from core.spawn import _max_tokens_for_task


def test_compact_mode_uses_lower_token_budget():
    assert _max_tokens_for_task({"type": "plan"}, compact_mode=True) == 1800
    assert _max_tokens_for_task({"type": "code"}, compact_mode=True) == 900


def test_default_mode_keeps_full_budget():
    assert _max_tokens_for_task({"type": "plan"}, compact_mode=False) == 8192
