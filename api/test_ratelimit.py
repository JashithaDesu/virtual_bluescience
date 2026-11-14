try:
    from api.ratelimit import RateLimiter
except ImportError:
    from ratelimit import RateLimiter


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make(limit=10, window=60):
    clock = FakeClock()
    return RateLimiter(limit=limit, window=window, clock=clock), clock


def test_allows_up_to_limit():
    rl, _ = make()
    assert all(rl.check("u1")[0] for _ in range(10))


def test_blocks_eleventh_with_retry_after():
    rl, _ = make()
    for _ in range(10):
        rl.check("u1")
    allowed, retry = rl.check("u1")
    assert not allowed
    assert 1 <= retry <= 61


def test_allows_again_after_window():
    rl, clock = make()
    for _ in range(10):
        rl.check("u1")
    clock.t += 60
    assert rl.check("u1")[0]


def test_limit_is_per_user():
    rl, _ = make()
    for _ in range(10):
        rl.check("u1")
    assert not rl.check("u1")[0]
    assert rl.check("u2")[0]


def test_blocked_calls_do_not_extend_the_wait():
    rl, clock = make()
    for _ in range(10):
        rl.check("u1")
    for _ in range(5):
        rl.check("u1")
    clock.t += 60
    assert rl.check("u1")[0]
