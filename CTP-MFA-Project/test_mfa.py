import asyncio, time
import pytest
import mfa
from mfa import DB, FACTORS, TRANSITIONS, ACTIVE, InvalidTransition, Policy, Service, State, hotp, totp

mfa.ITER = 1000  # fast hashing in tests
PW = "Pass#1234"


def run(coro):
    return asyncio.run(coro)


def make(**kw):
    t = [1_800_000_000.0]
    svc = Service(clock=lambda: t[0], **kw)
    svc.add_user("alice", PW, "+910000")
    return svc, t


def test_hotp_rfc4226_vectors():
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # ASCII "12345678901234567890"
    assert [hotp(secret, i) for i in (0, 1, 9)] == ["755224", "287082", "520489"]


def test_happy_path_two_factors():
    async def go():
        svc, t = make()
        s = await svc.open("alice")
        assert s.state is State.CHALLENGED
        await s.submit(PW)
        assert s.state is State.CHALLENGED and s.idx == 1
        await s.submit(totp(svc.user("alice")["secret"], t[0]))
        assert s.state is State.AUTHENTICATED and s.token
        assert [h["to"] for h in s.history] == ["CHALLENGED", "VERIFYING", "CHALLENGED", "VERIFYING", "AUTHENTICATED"]
    run(go())


def test_retry_then_success():
    async def go():
        svc, _ = make()
        s = await svc.open("alice")
        await s.submit("wrong")
        assert s.state is State.RETRY and (await s.view())["attemptsLeft"] == 2
        await s.submit(PW)
        assert s.state is State.CHALLENGED and s.idx == 1
    run(go())


def test_lockout_then_unlock_restarts_flow():
    async def go():
        svc, t = make()
        s = await svc.open("alice")
        for _ in range(3):
            await s.submit("bad")
        assert s.state is State.LOCKED and (await s.view())["lockedFor"] == 30
        with pytest.raises(InvalidTransition):
            await s.submit(PW)
        t[0] += 31
        await s.view()
        assert s.state is State.CHALLENGED and s.idx == 0
    run(go())


def test_backoff_then_block_and_admin_unlock():
    async def go():
        svc, t = make(policy=Policy(max_lockouts=2))
        s = await svc.open("alice")
        for _ in range(3): await s.submit("bad")
        t[0] += 31; await s.view()
        for _ in range(3): await s.submit("bad")
        assert s.state is State.BLOCKED
        assert (await svc.open("alice")).state is State.BLOCKED
        svc.unlock("alice")
        assert (await svc.open("alice")).state is State.CHALLENGED
    run(go())


def test_lock_is_account_wide():
    async def go():
        svc, _ = make()
        s1 = await svc.open("alice")
        for _ in range(3): await s1.submit("bad")
        assert (await svc.open("alice")).state is State.LOCKED
    run(go())


def test_lock_persists_across_restart(tmp_path):
    async def go():
        path = str(tmp_path / "m.db")
        svc, t = make(db=DB(path))
        s = await svc.open("alice")
        for _ in range(3): await s.submit("x")
        again = Service(DB(path), clock=lambda: t[0])
        assert (await again.open("alice")).state is State.LOCKED
    run(go())


def test_invalid_transitions_raise():
    async def go():
        svc, _ = make()
        s = await svc.open("alice")
        with pytest.raises(InvalidTransition):
            await s.resend()          # password cannot be resent
        s.cancel()
        with pytest.raises(InvalidTransition):
            await s.submit(PW)
        with pytest.raises(InvalidTransition):
            s.cancel()
    run(go())


def test_sms_otp_accept_and_expire():
    async def go():
        svc, t = make(policy=Policy(factors=["sms"], otp_ttl=60))
        s = await svc.open("alice")
        code = svc.devices("alice")["messages"][0]["body"].split()[-1]
        await s.submit(code)
        assert s.state is State.AUTHENTICATED
        s2 = await svc.open("alice")
        code2 = svc.devices("alice")["messages"][0]["body"].split()[-1]
        t[0] += 61
        await s2.submit(code2)
        assert s2.state is State.RETRY
    run(go())


def test_concurrent_challenges_do_not_block_each_other():
    async def go():
        svc = Service(policy=Policy(factors=["sms"]), latency=0.1)
        for i in range(5): svc.add_user(f"user{i}", PW)
        t0 = time.perf_counter()
        await asyncio.gather(*(svc.open(f"user{i}") for i in range(5)))
        assert time.perf_counter() - t0 < 0.35  # sequential would take 0.5s
    run(go())


@pytest.mark.parametrize("bad", [{"factors": []}, {"factors": ["password", "password"]}, {"factors": ["nope"]},
                                 {"max_attempts": 0}, {"backoff": 0.5}, {"unknown": 1}])
def test_policy_rejects_invalid(bad):
    with pytest.raises(ValueError):
        Policy.parse(bad)


def test_transition_table_is_consistent():
    assert all((s, "cancel") in TRANSITIONS for s in ACTIVE)
    terminal = {State.AUTHENTICATED, State.BLOCKED, State.CANCELLED}
    assert not any(src in terminal for src, _ in TRANSITIONS)
    assert set(FACTORS) == {"password", "totp", "sms"}
