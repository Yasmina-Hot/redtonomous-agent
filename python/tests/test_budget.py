import pytest

from redtonomous.modes import (
    Budget,
    BudgetExceeded,
    UNKNOWN_PRICE,
    price_for,
)


def test_price_lookup_known():
    assert price_for("claude-opus-4-7") == (15.0, 75.0)
    assert price_for("gpt-4o-mini") == (0.15, 0.6)


def test_price_lookup_prefixed():
    # OpenRouter-style "anthropic/claude-..." prefix should still resolve.
    assert price_for("anthropic/claude-sonnet-4-6") == (3.0, 15.0)


def test_price_lookup_unknown_falls_back_to_opus():
    assert price_for("totally-made-up-model") == UNKNOWN_PRICE


def test_budget_charges_accumulate():
    b = Budget(cap_usd=1.0, model="gpt-4o-mini")  # 0.15 in / 0.6 out per Mtok
    b.charge(1_000_000, 0)  # $0.15
    assert b.spent_usd == pytest.approx(0.15)
    b.charge(0, 1_000_000)  # $0.60
    assert b.spent_usd == pytest.approx(0.75)


def test_budget_cap_raises():
    b = Budget(cap_usd=0.1, model="gpt-4o-mini")
    with pytest.raises(BudgetExceeded):
        # 1M output tokens cost $0.60 > $0.10 cap.
        b.charge(0, 1_000_000)


def test_budget_zero_cap_disables_check():
    # cap_usd=0 means "no cap" — never raise.
    b = Budget(cap_usd=0.0, model="claude-opus-4-7")
    b.charge(10_000_000, 10_000_000)
    assert b.spent_usd > 0  # still tracks
