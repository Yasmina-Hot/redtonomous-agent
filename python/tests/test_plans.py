from redtonomous.plans import PLANS, plan_by_id, public_catalog


def test_plan_ids_unique_and_complete():
    ids = [p.id for p in PLANS]
    assert ids == ["free", "min", "starter", "pro", "dev", "max", "red"]
    assert len(set(ids)) == len(ids)


def test_prices_are_in_ascending_order():
    prices = [p.price_usd for p in PLANS]
    assert prices == sorted(prices)


def test_red_plan_is_the_only_one_with_red_mode():
    red = plan_by_id("red")
    assert red is not None
    assert "red" in red.cli_modes
    for p in PLANS:
        if p.id != "red":
            assert "red" not in p.cli_modes


def test_free_plan_is_zero_dollars():
    free = plan_by_id("free")
    assert free is not None
    assert free.price_usd == 0.0


def test_unlimited_sessions_starts_at_pro():
    for tier in ("pro", "dev", "max", "red"):
        plan = plan_by_id(tier)
        assert plan is not None
        assert plan.sessions_per_month is None  # unlimited


def test_public_catalog_is_json_serialisable():
    import json
    catalog = public_catalog()
    json.dumps(catalog)  # must not raise
    assert all("features" in entry and isinstance(entry["features"], list) for entry in catalog)


def test_plan_by_id_returns_none_for_missing():
    assert plan_by_id("enterprise-deluxe") is None
