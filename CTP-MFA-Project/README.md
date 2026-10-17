# Multi-Factor Authentication Simulation System

Simulates a configurable multi-factor sign-in flow with retry and lockout policies.
Pure Python 3.10+ standard library at runtime; `pytest` for tests.

## Run
```
python server.py            # http://127.0.0.1:8000  (data in mfa.db; --port, --db, --latency)
pip install -r requirements.txt && pytest
```
Demo accounts: `alice / Wonder#2026`, `bob / Builder#2026`. The "Simulated phone" panel shows the live
authenticator code and texted OTPs. Try wrong codes to watch RETRY → LOCKED → BLOCKED in the diagram.

## Design
| Focus area | Where |
|---|---|
| OOP state machine | `Session` is the context; `State`/`TRANSITIONS` is the single source of truth. Every change goes through `Session.fire()`, so illegal moves raise `InvalidTransition` and every move is written to the audit log. |
| asyncio challenge-response | `Factor` subclasses (`PasswordFactor`, `TotpFactor`, `SmsFactor`) implement async `issue()` / `verify()`. SMS delivery is simulated with `asyncio.sleep`, verification runs under `wait_for`, password hashing is offloaded with `to_thread`, and a per-session `asyncio.Lock` serialises actions. |
| Retry / lockout | `Policy` (stored in SQLite): attempts before lockout, lockout length, backoff multiplier, lockouts before block, OTP lifetime, ordered factor list. |
| Storage | SQLite: users (PBKDF2 hashes, TOTP secrets), per-account lock counters, audit log, SMS outbox, saved policy. |
| Tests | `tests/test_mfa.py`: RFC 4226 vectors, happy path, retry, lockout/unlock, backoff and block, restart persistence, OTP expiry, concurrency, policy validation. |

States: `CREATED → CHALLENGED → VERIFYING → (CHALLENGED | AUTHENTICATED | RETRY | LOCKED | BLOCKED)`, `CANCELLED` from any active state.

Decisions worth explaining in a viva:
- Failure counters and locks belong to the **account**, not the session, so opening new sessions cannot reset them.
- Unlocking restarts the flow at the first factor.
- The Nth lockout (`max_lockouts`) blocks the account until an administrator unlocks it.
- Session tokens, SMS and authenticator devices are simulated; nothing is sent anywhere.
