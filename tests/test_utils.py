import time

from backend.utils import TTLCache


def test_ttl_cache_reuses_value_until_ttl_expires():
    cache = TTLCache[int](ttl_seconds=0.02)
    calls = 0

    def factory() -> int:
        nonlocal calls
        calls += 1
        return calls

    assert cache.get_or_set(factory) == 1
    assert cache.get_or_set(factory) == 1
    assert calls == 1

    time.sleep(0.03)

    assert cache.get_or_set(factory) == 2
    assert calls == 2


def test_ttl_cache_clear_forces_refresh():
    cache = TTLCache[str](ttl_seconds=60)
    calls = 0

    def factory() -> str:
        nonlocal calls
        calls += 1
        return f"value-{calls}"

    assert cache.get_or_set(factory) == "value-1"
    cache.clear()
    assert cache.get_or_set(factory) == "value-2"
