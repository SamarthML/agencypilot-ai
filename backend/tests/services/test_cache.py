from app.services.cache import TtlCache


def test_entries_expire_after_ttl() -> None:
    now = [0.0]
    cache: TtlCache[str] = TtlCache(10, clock=lambda: now[0])

    cache.set("k", "v")
    now[0] = 9.9
    assert cache.get("k") == "v"
    now[0] = 10.0
    assert cache.get("k") is None


def test_oldest_entry_evicted_when_full() -> None:
    cache: TtlCache[int] = TtlCache(60, max_entries=2)

    for i in range(3):
        cache.set(str(i), i)

    assert (cache.get("0"), cache.get("1"), cache.get("2")) == (None, 1, 2)


def test_overwriting_a_key_does_not_evict_others() -> None:
    cache: TtlCache[int] = TtlCache(60, max_entries=2)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("b", 3)

    assert (cache.get("a"), cache.get("b")) == (1, 3)
