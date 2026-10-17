"""MFA Simulation System core: OOP state machine, asyncio factors, lockout policy, SQLite storage."""
import asyncio, base64, hashlib, hmac, json, re, secrets, sqlite3, struct, time
from dataclasses import dataclass, field, asdict
from enum import Enum

ITER = 50_000  # PBKDF2 iterations (tests lower this)


class State(str, Enum):
    CREATED = "CREATED"; CHALLENGED = "CHALLENGED"; VERIFYING = "VERIFYING"; RETRY = "RETRY"
    LOCKED = "LOCKED"; AUTHENTICATED = "AUTHENTICATED"; BLOCKED = "BLOCKED"; CANCELLED = "CANCELLED"

S = State
ACTIVE = {S.CREATED, S.CHALLENGED, S.VERIFYING, S.RETRY, S.LOCKED}
TRANSITIONS = {  # (state, event) -> next state; anything else raises InvalidTransition
    (S.CREATED, "start"): S.CHALLENGED,
    (S.CHALLENGED, "submit"): S.VERIFYING, (S.RETRY, "submit"): S.VERIFYING,
    (S.CHALLENGED, "resend"): S.CHALLENGED, (S.RETRY, "resend"): S.CHALLENGED,
    (S.VERIFYING, "next"): S.CHALLENGED, (S.VERIFYING, "done"): S.AUTHENTICATED,
    (S.VERIFYING, "fail"): S.RETRY, (S.VERIFYING, "lock"): S.LOCKED, (S.VERIFYING, "block"): S.BLOCKED,
    (S.LOCKED, "unlock"): S.CHALLENGED,
}
for _s in (S.CREATED, S.CHALLENGED, S.RETRY):  # account locked/blocked by another session
    TRANSITIONS[(_s, "lock")] = S.LOCKED
    TRANSITIONS[(_s, "block")] = S.BLOCKED
for _s in ACTIVE:
    TRANSITIONS[(_s, "cancel")] = S.CANCELLED


class InvalidTransition(Exception):
    pass


# ---------- crypto helpers ----------
def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(8)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), ITER).hex()

def check_pw(pw, stored):
    return hmac.compare_digest(hash_pw(pw, stored.split("$")[0]), stored)

def hotp(secret, counter, digits=6):  # RFC 4226
    mac = hmac.new(base64.b32decode(secret), struct.pack(">Q", counter), "sha1").digest()
    o = mac[-1] & 15
    return str((struct.unpack(">I", mac[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** digits).zfill(digits)

def totp(secret, t, period=30):  # RFC 6238
    return hotp(secret, int(t // period))


# ---------- policy ----------
@dataclass
class Policy:
    factors: list = field(default_factory=lambda: ["password", "totp"])
    max_attempts: int = 3        # failed verifications per account before a lockout
    lockout_seconds: float = 30  # first lockout length
    backoff: float = 2.0         # each further lockout is this many times longer
    max_lockouts: int = 3        # the Nth lockout blocks the account until an admin unlocks it
    otp_ttl: float = 60          # SMS code lifetime

    def lock_for(self, n):
        return self.lockout_seconds * self.backoff ** (n - 1)

    @classmethod
    def parse(cls, d):
        base, kw = cls(), {}
        for k, v in d.items():
            if k not in asdict(base):
                raise ValueError(f"unknown setting {k}")
            kw[k] = list(v) if k == "factors" else type(getattr(base, k))(v)
        p = cls(**kw)
        if not p.factors or len(set(p.factors)) != len(p.factors) or any(f not in FACTORS for f in p.factors):
            raise ValueError("factors must be unique and from: " + ", ".join(FACTORS))
        if min(p.max_attempts, p.max_lockouts) < 1 or p.lockout_seconds <= 0 or p.backoff < 1 or p.otp_ttl <= 0:
            raise ValueError("invalid retry/lockout settings")
        return p


# ---------- factors (async challenge-response) ----------
class Factor:
    name = prompt = ""
    resendable = False
    async def issue(self, svc, sess): return {}
    async def verify(self, svc, sess, answer): raise NotImplementedError

class PasswordFactor(Factor):
    name, prompt = "password", "Enter your password"
    async def verify(self, svc, sess, answer):
        return await asyncio.to_thread(check_pw, answer, svc.user(sess.user)["pw"])  # CPU work off the loop

class TotpFactor(Factor):
    name, prompt = "totp", "Enter the 6-digit code from your authenticator app"
    async def verify(self, svc, sess, answer):
        secret, c = svc.user(sess.user)["secret"], int(svc.clock() // 30)
        return any(hmac.compare_digest(hotp(secret, k), answer.strip()) for k in (c - 1, c, c + 1))

class SmsFactor(Factor):
    name, prompt, resendable = "sms", "Enter the code we texted you", True
    async def issue(self, svc, sess):
        code = f"{secrets.randbelow(10 ** 6):06d}"
        await asyncio.sleep(svc.latency)  # simulated network delivery
        svc.db.x("insert into outbox(ts,user,body) values(?,?,?)", svc.clock(), sess.user, f"Your code is {code}")
        return {"code": code, "exp": svc.clock() + svc.policy.otp_ttl}
    async def verify(self, svc, sess, answer):
        return svc.clock() < sess.ch["exp"] and hmac.compare_digest(sess.ch["code"], answer.strip())

FACTORS = {f.name: f for f in (PasswordFactor(), TotpFactor(), SmsFactor())}


# ---------- storage ----------
class DB:
    def __init__(self, path=":memory:"):
        self.c = sqlite3.connect(path, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.executescript("""
        create table if not exists users(name text primary key, pw text, secret text, phone text);
        create table if not exists accounts(name text primary key, fails int default 0, locks int default 0, until real default 0, blocked int default 0);
        create table if not exists audit(id integer primary key autoincrement, ts real, sid text, user text, event text, src text, dst text, detail text);
        create table if not exists outbox(id integer primary key autoincrement, ts real, user text, body text);
        create table if not exists settings(k text primary key, v text);""")
    def x(self, sql, *a):
        self.c.execute(sql, a); self.c.commit()
    def q(self, sql, *a):
        return [dict(r) for r in self.c.execute(sql, a)]


# ---------- session = state machine context ----------
class Session:
    def __init__(self, svc, user):
        self.svc, self.user, self.id = svc, user, secrets.token_hex(4)
        self.state, self.idx, self.ch, self.msg, self.history, self.token = S.CREATED, 0, {}, "", [], None
        self.lock = asyncio.Lock()

    @property
    def factor(self):
        return FACTORS[self.svc.policy.factors[self.idx]]

    def fire(self, event, detail=""):
        dst = TRANSITIONS.get((self.state, event))
        if dst is None:
            raise InvalidTransition(f"'{event}' is not allowed in state {self.state.value}")
        row = {"ts": self.svc.clock(), "event": event, "from": self.state.value, "to": dst.value, "detail": detail}
        self.svc.db.x("insert into audit(ts,sid,user,event,src,dst,detail) values(?,?,?,?,?,?,?)",
                      row["ts"], self.id, self.user, event, row["from"], row["to"], detail)
        self.history.append(row)
        self.state, self.msg = dst, detail

    async def _issue(self, event):
        self.ch = await self.factor.issue(self.svc, self)
        self.fire(event, self.factor.prompt)

    async def _guard(self):  # account-level lock applies to every session of the user
        a, now = self.svc.acct(self.user), self.svc.clock()
        if self.state in (S.CREATED, S.CHALLENGED, S.RETRY):
            if a["blocked"]:
                self.fire("block", "Account blocked after too many lockouts. An administrator must unlock it.")
            elif a["until"] > now:
                self.fire("lock", "Account is locked")
        elif self.state is S.LOCKED and not a["blocked"] and a["until"] <= now:
            self.idx = 0  # unlocking restarts the flow from the first factor
            await self._issue("unlock")

    async def start(self):
        async with self.lock:
            await self._guard()
            if self.state is S.CREATED:
                await self._issue("start")

    async def submit(self, answer):
        async with self.lock:
            await self._guard()
            self.fire("submit")
            try:
                ok = await asyncio.wait_for(self.factor.verify(self.svc, self, str(answer)), 10)
            except Exception:
                ok = False
            if not ok:
                return self._fail()
            if self.idx + 1 < len(self.svc.policy.factors):
                self.idx += 1
                await self._issue("next")
            else:
                self.svc.db.x("update accounts set fails=0, locks=0, until=0 where name=?", self.user)
                self.token = secrets.token_urlsafe(16)
                self.fire("done", "All factors verified")

    def _fail(self):
        p, db, n = self.svc.policy, self.svc.db, self.user
        fails = self.svc.acct(n)["fails"] + 1
        if fails < p.max_attempts:
            db.x("update accounts set fails=? where name=?", fails, n)
            return self.fire("fail", f"Incorrect. {p.max_attempts - fails} attempt(s) left")
        locks = self.svc.acct(n)["locks"] + 1
        if locks >= p.max_lockouts:
            db.x("update accounts set fails=0, locks=?, blocked=1 where name=?", locks, n)
            return self.fire("block", "Too many lockouts: account blocked until an administrator unlocks it")
        db.x("update accounts set fails=0, locks=?, until=? where name=?", locks, self.svc.clock() + p.lock_for(locks), n)
        self.fire("lock", f"Too many failures: locked for {p.lock_for(locks):.0f}s")

    async def resend(self):
        async with self.lock:
            await self._guard()
            if not self.factor.resendable or (self.state, "resend") not in TRANSITIONS:
                raise InvalidTransition("Nothing to resend for this step")
            await self._issue("resend")

    def cancel(self):
        self.fire("cancel", "Sign-in cancelled")

    async def view(self):
        async with self.lock:
            await self._guard()
        a, p, now = self.svc.acct(self.user), self.svc.policy, self.svc.clock()
        live = self.state in (S.CHALLENGED, S.RETRY, S.VERIFYING)
        return {"id": self.id, "user": self.user, "state": self.state.value, "message": self.msg,
                "factors": p.factors, "idx": self.idx, "prompt": self.factor.prompt if live else "",
                "resendable": live and self.factor.resendable, "attemptsLeft": p.max_attempts - a["fails"],
                "lockedFor": max(0, round(a["until"] - now)) if self.state is S.LOCKED else 0,
                "token": self.token, "history": self.history}


# ---------- service ----------
class Service:
    def __init__(self, db=None, policy=None, clock=time.time, latency=0.0):
        self.db, self.clock, self.latency, self.sessions = db or DB(), clock, latency, {}
        saved = self.db.q("select v from settings where k='policy'")
        self.policy = policy or (Policy.parse(json.loads(saved[0]["v"])) if saved else Policy())

    def set_policy(self, d):
        self.policy = Policy.parse(d)
        self.db.x("insert or replace into settings values('policy',?)", json.dumps(asdict(self.policy)))

    def add_user(self, name, password, phone=""):
        if not re.fullmatch(r"\w{3,20}", name) or len(password) < 8:
            raise ValueError("name: 3-20 letters/digits/_, password: at least 8 characters")
        secret = base64.b32encode(secrets.token_bytes(10)).decode()
        self.db.x("insert into users values(?,?,?,?)", name, hash_pw(password), secret, phone)
        self.db.x("insert into accounts(name) values(?)", name)

    def user(self, name):
        r = self.db.q("select * from users where name=?", name)
        if not r:
            raise KeyError(f"unknown user {name}")
        return r[0]

    def acct(self, name):
        return self.db.q("select * from accounts where name=?", name)[0]

    def unlock(self, name):
        self.db.x("update accounts set fails=0, locks=0, until=0, blocked=0 where name=?", name)

    async def open(self, name):
        self.user(name)
        s = Session(self, name)
        self.sessions[s.id] = s
        await s.start()
        return s

    def devices(self, name):  # what the simulated phone shows
        u, t = self.user(name), self.clock()
        return {"totp": totp(u["secret"], t), "left": 30 - t % 30,
                "messages": self.db.q("select * from outbox where user=? order by id desc limit 5", name)}
