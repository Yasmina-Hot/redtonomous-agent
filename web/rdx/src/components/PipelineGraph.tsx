"use client";
import { useCallback, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type NodeTypes,
} from "@xyflow/react";
import { Cpu, Terminal, GitBranch, LogIn, LogOut } from "lucide-react";
import type { PipelineNode } from "@/lib/types";

const NODE_ICONS: Record<PipelineNode["type"], React.ReactNode> = {
  input:  <LogIn size={11} />,
  agent:  <Cpu size={11} />,
  tool:   <Terminal size={11} />,
  router: <GitBranch size={11} />,
  output: <LogOut size={11} />,
};

const NODE_COLORS: Record<PipelineNode["type"], string> = {
  input:  "border-[var(--success)]",
  agent:  "border-[var(--accent)]",
  tool:   "border-blue-500",
  router: "border-yellow-500",
  output: "border-purple-500",
};

function AgentNode({ data }: { data: { label: string; type: PipelineNode["type"]; model?: string } }) {
  return (
    <div className={`rounded border-2 ${NODE_COLORS[data.type] ?? "border-[var(--border)]"} bg-[var(--surface)] px-3 py-2 min-w-[120px] shadow-lg`}>
      <div className="flex items-center gap-1.5">
        <span className="text-[var(--accent)]">{NODE_ICONS[data.type]}</span>
        <span className="text-xs font-semibold text-[var(--text)]">{data.label}</span>
      </div>
      {data.model && (
        <p className="text-[9px] font-mono text-[var(--text-muted)] mt-1">{data.model}</p>
      )}
    </div>
  );
}

const nodeTypes: NodeTypes = { agentNode: AgentNode };

type NodeData = { label: string; type: PipelineNode["type"]; model?: string };
type GraphNode = { id: string; type: string; position: { x: number; y: number }; data: NodeData };

const INITIAL_NODES: GraphNode[] = [
  { id: "1", type: "agentNode", position: { x: 80, y: 150 },  data: { label: "Input",  type: "input" } },
  { id: "2", type: "agentNode", position: { x: 320, y: 150 }, data: { label: "Agent",  type: "agent", model: "claude-sonnet-4-6" } },
  { id: "3", type: "agentNode", position: { x: 560, y: 150 }, data: { label: "Output", type: "output" } },
];
const INITIAL_EDGES = [
  { id: "e1-2", source: "1", target: "2", animated: true },
  { id: "e2-3", source: "2", target: "3", animated: true },
];

interface PipelineGraphProps {
  onChange?: (nodes: unknown[], edges: unknown[]) => void;
}

export function PipelineGraph({ onChange }: PipelineGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNode>(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
  const [nodeType, setNodeType] = useState<PipelineNode["type"]>("agent");

  const onConnect = useCallback((conn: Connection) => {
    setEdges((eds) => addEdge({ ...conn, animated: true }, eds));
  }, [setEdges]);

  const addNode = () => {
    const id = String(Date.now());
    const newNode = {
      id,
      type: "agentNode",
      position: { x: 200 + Math.random() * 200, y: 100 + Math.random() * 200 },
      data: { label: nodeType.charAt(0).toUpperCase() + nodeType.slice(1), type: nodeType, model: nodeType === "agent" ? "claude-sonnet-4-6" : undefined },
    };
    setNodes((ns) => [...ns, newNode]);
    onChange?.([...nodes, newNode], edges);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border)] bg-[var(--surface-2)]">
        <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">Add node:</span>
        {(["input", "agent", "tool", "router", "output"] as PipelineNode["type"][]).map((t) => (
          <button
            key={t}
            onClick={() => { setNodeType(t); addNode(); }}
            className="flex items-center gap-1 rounded border border-[var(--border)] px-2 py-1 text-[10px] text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-[var(--accent)] hover:bg-[var(--accent-muted)] transition-colors"
          >
            {NODE_ICONS[t]} {t}
          </button>
        ))}
      </div>
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background color="var(--border)" />
          <Controls className="!bg-[var(--surface)] !border-[var(--border)]" />
          <MiniMap className="!bg-[var(--surface-2)]" maskColor="rgba(0,0,0,0.5)" />
        </ReactFlow>
      </div>
    </div>
  );
}
