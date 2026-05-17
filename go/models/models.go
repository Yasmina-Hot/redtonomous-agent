package models

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"
	"github.com/openai/openai-go"
	openaiopt "github.com/openai/openai-go/option"
	"github.com/yasmina-hot/redtonomous-agent/go/tools"
)

// ToolCall represents a single tool invocation from the model.
type ToolCall struct {
	ID   string
	Name string
	Args map[string]interface{}
}

// ModelResponse is the unified response from any provider.
type ModelResponse struct {
	Text         string
	StopReason   string // "end_turn" | "tool_use"
	ToolCalls    []ToolCall
	InputTokens  int
	OutputTokens int
}

// Message is a generic chat message.
type Message struct {
	Role    string
	Content interface{} // string or []interface{}
}

// Adapter is the interface every provider implements.
type Adapter interface {
	Chat(messages []Message, tools []tools.ToolDef, system string) (*ModelResponse, error)
	BuildToolResultMessages(toolCalls []ToolCall, results []ToolResult) []Message
}

// ToolResult holds the output of a tool execution.
type ToolResult struct {
	Content string
	IsError bool
}

// ─── Claude ────────────────────────────────────────────────────────────────

type ClaudeAdapter struct {
	client *anthropic.Client
	model  string
}

func NewClaudeAdapter(apiKey, model string) *ClaudeAdapter {
	client := anthropic.NewClient(option.WithAPIKey(apiKey))
	return &ClaudeAdapter{client: &client, model: model}
}

func (a *ClaudeAdapter) Chat(messages []Message, toolDefs []tools.ToolDef, system string) (*ModelResponse, error) {
	var anthropicMsgs []anthropic.MessageParam
	for _, m := range messages {
		switch v := m.Content.(type) {
		case string:
			if m.Role == "user" {
				anthropicMsgs = append(anthropicMsgs, anthropic.NewUserMessage(anthropic.NewTextBlock(v)))
			} else {
				anthropicMsgs = append(anthropicMsgs, anthropic.NewAssistantMessage(anthropic.NewTextBlock(v)))
			}
		case []interface{}:
			// tool result messages stored as raw blocks
			data, _ := json.Marshal(v)
			var blocks []anthropic.ContentBlockParamUnion
			_ = json.Unmarshal(data, &blocks)
			if m.Role == "user" {
				anthropicMsgs = append(anthropicMsgs, anthropic.MessageParam{Role: anthropic.MessageParamRoleUser, Content: blocks})
			} else {
				anthropicMsgs = append(anthropicMsgs, anthropic.MessageParam{Role: anthropic.MessageParamRoleAssistant, Content: blocks})
			}
		}
	}

	var anthropicTools []anthropic.ToolUnionParam
	for _, t := range toolDefs {
		data, _ := json.Marshal(t.Parameters)
		var schema anthropic.ToolInputSchemaParam
		_ = json.Unmarshal(data, &schema)
		anthropicTools = append(anthropicTools, anthropic.ToolParam{
			Name:        t.Name,
			Description: anthropic.String(t.Description),
			InputSchema: schema,
		})
	}

	resp, err := a.client.Messages.New(context.Background(), anthropic.MessageNewParams{
		Model:     anthropic.Model(a.model),
		MaxTokens: 8096,
		System:    []anthropic.TextBlockParam{{Type: "text", Text: system}},
		Messages:  anthropicMsgs,
		Tools:     anthropicTools,
	})
	if err != nil {
		return nil, err
	}

	var text string
	var toolCalls []ToolCall
	for _, block := range resp.Content {
		switch b := block.AsUnion().(type) {
		case anthropic.TextBlock:
			text += b.Text
		case anthropic.ToolUseBlock:
			var args map[string]interface{}
			_ = json.Unmarshal(b.Input, &args)
			toolCalls = append(toolCalls, ToolCall{ID: b.ID, Name: b.Name, Args: args})
		}
	}

	stopReason := "end_turn"
	if len(toolCalls) > 0 {
		stopReason = "tool_use"
	}
	return &ModelResponse{
		Text:        text,
		StopReason:  stopReason,
		ToolCalls:   toolCalls,
		InputTokens: int(resp.Usage.InputTokens),
		OutputTokens: int(resp.Usage.OutputTokens),
	}, nil
}

func (a *ClaudeAdapter) BuildToolResultMessages(toolCalls []ToolCall, results []ToolResult) []Message {
	var assistantBlocks []interface{}
	for _, tc := range toolCalls {
		argsJSON, _ := json.Marshal(tc.Args)
		var rawInput json.RawMessage = argsJSON
		assistantBlocks = append(assistantBlocks, map[string]interface{}{
			"type":  "tool_use",
			"id":    tc.ID,
			"name":  tc.Name,
			"input": rawInput,
		})
	}
	var userBlocks []interface{}
	for i, tc := range toolCalls {
		userBlocks = append(userBlocks, map[string]interface{}{
			"type":        "tool_result",
			"tool_use_id": tc.ID,
			"content":     results[i].Content,
			"is_error":    results[i].IsError,
		})
	}
	return []Message{
		{Role: "assistant", Content: assistantBlocks},
		{Role: "user", Content: userBlocks},
	}
}

// ─── OpenAI-compatible ─────────────────────────────────────────────────────

type OpenAICompatAdapter struct {
	client *openai.Client
	model  string
}

func NewOpenAICompatAdapter(apiKey, model, baseURL string) *OpenAICompatAdapter {
	opts := []openaiopt.RequestOption{openaiopt.WithAPIKey(apiKey)}
	if baseURL != "" {
		opts = append(opts, openaiopt.WithBaseURL(baseURL))
	}
	client := openai.NewClient(opts...)
	return &OpenAICompatAdapter{client: &client, model: model}
}

func (a *OpenAICompatAdapter) Chat(messages []Message, toolDefs []tools.ToolDef, system string) (*ModelResponse, error) {
	var chatMsgs []openai.ChatCompletionMessageParamUnion
	if system != "" {
		chatMsgs = append(chatMsgs, openai.SystemMessage(system))
	}
	for _, m := range messages {
		switch v := m.Content.(type) {
		case string:
			if m.Role == "user" {
				chatMsgs = append(chatMsgs, openai.UserMessage(v))
			} else if m.Role == "assistant" {
				chatMsgs = append(chatMsgs, openai.AssistantMessage(v))
			}
		case []interface{}:
			// For tool calls/results stored as raw maps
			data, _ := json.Marshal(v)
			var raw []map[string]interface{}
			_ = json.Unmarshal(data, &raw)
			for _, item := range raw {
				if item["role"] == "tool" {
					chatMsgs = append(chatMsgs, openai.ToolMessage(fmt.Sprint(item["content"]), fmt.Sprint(item["tool_call_id"])))
				}
			}
		}
	}

	var openaiTools []openai.ChatCompletionToolParam
	for _, t := range toolDefs {
		data, _ := json.Marshal(t.Parameters)
		var params openai.FunctionParameters
		_ = json.Unmarshal(data, &params)
		openaiTools = append(openaiTools, openai.ChatCompletionToolParam{
			Type: "function",
			Function: openai.FunctionDefinitionParam{
				Name:        t.Name,
				Description: openai.String(t.Description),
				Parameters:  params,
			},
		})
	}

	resp, err := a.client.Chat.Completions.New(context.Background(), openai.ChatCompletionNewParams{
		Model:      openai.ChatModel(a.model),
		Messages:   chatMsgs,
		Tools:      openaiTools,
		ToolChoice: openai.ChatCompletionToolChoiceOptionUnionParam{OfChatCompletionToolChoiceOption: openai.Ptr(openai.ChatCompletionToolChoiceOptionAuto)},
	})
	if err != nil {
		return nil, err
	}

	msg := resp.Choices[0].Message
	var toolCalls []ToolCall
	for _, tc := range msg.ToolCalls {
		var args map[string]interface{}
		_ = json.Unmarshal([]byte(tc.Function.Arguments), &args)
		toolCalls = append(toolCalls, ToolCall{ID: tc.ID, Name: tc.Function.Name, Args: args})
	}

	stopReason := "end_turn"
	if len(toolCalls) > 0 {
		stopReason = "tool_use"
	}
	return &ModelResponse{
		Text:         msg.Content,
		StopReason:   stopReason,
		ToolCalls:    toolCalls,
		InputTokens:  int(resp.Usage.PromptTokens),
		OutputTokens: int(resp.Usage.CompletionTokens),
	}, nil
}

func (a *OpenAICompatAdapter) BuildToolResultMessages(toolCalls []ToolCall, results []ToolResult) []Message {
	var tcList []interface{}
	for _, tc := range toolCalls {
		argsJSON, _ := json.Marshal(tc.Args)
		tcList = append(tcList, map[string]interface{}{
			"id":   tc.ID,
			"type": "function",
			"function": map[string]interface{}{
				"name":      tc.Name,
				"arguments": string(argsJSON),
			},
		})
	}
	assistantMsg := Message{Role: "assistant", Content: map[string]interface{}{
		"content":    nil,
		"tool_calls": tcList,
	}}
	msgs := []Message{assistantMsg}
	for i, tc := range toolCalls {
		msgs = append(msgs, Message{
			Role: "tool",
			Content: []interface{}{map[string]interface{}{
				"role":         "tool",
				"tool_call_id": tc.ID,
				"content":      results[i].Content,
			}},
		})
	}
	return msgs
}

// ─── Registry ──────────────────────────────────────────────────────────────

type ModelInfo struct {
	Provider string
	Model    string
	Type     string
}

var KnownModels = []ModelInfo{
	{"claude",     "claude-opus-4-7",              "claude"},
	{"claude",     "claude-sonnet-4-6",            "claude"},
	{"claude",     "claude-haiku-4-5",             "claude"},
	{"openai",     "gpt-4o",                       "openai-compat"},
	{"openai",     "gpt-4o-mini",                  "openai-compat"},
	{"gemini",     "gemini-2.5-pro",               "gemini (REST)"},
	{"gemini",     "gemini-2.0-flash",             "gemini (REST)"},
	{"groq",       "llama-3.3-70b-versatile",      "openai-compat"},
	{"groq",       "mixtral-8x7b-32768",           "openai-compat"},
	{"openrouter", "openai/gpt-4o",                "openai-compat"},
	{"deepseek",   "deepseek-chat",                "openai-compat"},
	{"xai",        "grok-3",                       "openai-compat"},
	{"ollama",     "llama3.2",                     "openai-compat (local)"},
	{"lmstudio",   "local-model",                  "openai-compat (local)"},
}
