# 17 · Auth: password hashing, JWT, roles

## Concept
Authentication answers **"who are you?"** and authorization answers **"what may you do?"**. TriageDesk uses
the standard stateless API approach:

1. **Register**: store the user with a **hashed** password (never the plain one). We use **Argon2**
   via `pwdlib`. Argon2 is the modern recommendation and is stronger than bcrypt against GPU attacks.
2. **Login**: verify the password, then issue a signed **JWT access token** (via `PyJWT`) containing the
   user id (`sub`), their role and an expiry (`exp`).
3. **Authenticated requests**: the client sends `Authorization: Bearer <token>`. A dependency
   decodes and verifies the token, loads the user, and injects it into the handler.
4. **Authorization**: a role check (customer / agent / admin) plus ownership rules (a customer
   may only see their own tickets).

FastAPI ships `OAuth2PasswordBearer`, a small dependency that extracts the bearer token from the header
**and** makes the 🔒 "Authorize" button in `/docs` work. Login uses `OAuth2PasswordRequestForm`
(form fields `username` + `password`), which is the shape that button expects.

## In Node you'd…
```js
// Express + bcrypt + jsonwebtoken
const hash = await bcrypt.hash(password, 12);
const ok = await bcrypt.compare(password, user.passwordHash);
const token = jwt.sign({ sub: user.id, role: user.role }, SECRET, { expiresIn: "30m" });

function auth(req, res, next) {                       // middleware mutates req
  const token = req.headers.authorization?.split(" ")[1];
  try { req.user = jwt.verify(token, SECRET); next(); }
  catch { res.status(401).json({ error: "Unauthorized" }); }
}
const requireRole = (...roles) => (req, res, next) =>
  roles.includes(req.user.role) ? next() : res.status(403).end();

app.get("/tickets", auth, requireRole("agent", "admin"), handler);
```
```python
# FastAPI: dependencies return the user instead of mutating req
@router.get("/tickets")
async def list_tickets(user: Annotated[User, Depends(require_role(Role.AGENT, Role.ADMIN))]) -> ...:
    ...
```

| Node | Python |
|---|---|
| `bcrypt` / `argon2` | `pwdlib` (`PasswordHash.recommended()` → Argon2) |
| `jsonwebtoken` `sign` / `verify` | `jwt.encode` / `jwt.decode` (PyJWT) |
| `passport-jwt` strategy | `OAuth2PasswordBearer` + a `get_current_user` dependency |
| `req.user` | a `current_user: CurrentUser` parameter |
| `requireRole("admin")` middleware | `Depends(require_role(Role.ADMIN))` dependency factory |
| `TokenExpiredError` | `jwt.ExpiredSignatureError` (subclass of `jwt.InvalidTokenError`) |

## Examples

### 1. Install
```bash
uv add pyjwt "pwdlib[argon2]"
```
(`python-multipart`, needed for the login form, already comes with `fastapi[standard]`.)

### 2. Password hashing
```python
# app/core/security.py
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()        # Argon2id with sensible parameters

def hash_password(plain: str) -> str:
    return password_hash.hash(plain)               # '$argon2id$v=19$m=65536,t=3,p=4$...'

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)
```
The salt and parameters are stored **inside** the hash string, so you need only one DB column.

### 3. Creating and decoding JWTs
```python
# app/core/security.py (continued)
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(minutes=30)


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {"sub": user_id, "role": role, "iat": now, "exp": now + ACCESS_TOKEN_TTL}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    # Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on bad tokens
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
```
PyJWT converts `datetime` values for `exp`/`iat` to Unix timestamps and **checks `exp` automatically**
on decode. Always pass `algorithms=[...]` (a list) when decoding.

### 4. User model with a role
```python
# app/models/user.py
import uuid
from enum import StrEnum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=20), default=Role.CUSTOMER)
    is_active: Mapped[bool] = mapped_column(default=True)
```
And schemas. Note that `UserOut` **has no password field**:
```python
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str
    role: Role

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

### 5. The current-user dependency
```python
# app/api/deps.py
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token
from app.models.user import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")   # path of the login endpoint

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise CREDENTIALS_ERROR from None
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
```
`OAuth2PasswordBearer` returns 401 by itself if the header is missing. We re-load the user from the
DB, so a deactivated user is locked out immediately even with an unexpired token.

### 6. Role checks: a dependency factory
```python
def require_role(*roles: Role):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return checker          # a closure (chapter 03) that FastAPI uses as a dependency

AgentUser = Annotated[User, Depends(require_role(Role.AGENT, Role.ADMIN))]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]

@router.get("/admin/users")
async def list_users(admin: AdminUser) -> list[UserOut]: ...
```
**401 vs 403:** 401 means "I don't know who you are" (missing or bad token). 403 means "I know who you are, and you're not allowed".

### 7. Register, login, me
```python
# app/api/routes/auth.py
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201, response_model=UserOut)
async def register(payload: UserCreate, service: AuthServiceDep) -> User:
    return await service.register(payload)          # raises ConflictError if email taken

@router.post("/login")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()],
                service: AuthServiceDep) -> Token:
    user = await service.authenticate(form.username, form.password)  # username = email
    return Token(access_token=create_access_token(str(user.id), user.role))

@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
```
Login is a **form post** (`application/x-www-form-urlencoded`), not JSON. That's the OAuth2 password-flow spec, and
it's what the `/docs` Authorize button sends.

### 8. Ownership (row-level) authorization
```python
# app/services/ticket_service.py
async def get_for_user(self, ticket_id: UUID, user: User) -> Ticket:
    ticket = await self.get(ticket_id)
    if user.role == Role.CUSTOMER and ticket.customer_id != user.id:
        raise NotFoundError("Ticket", ticket_id)   # 404, not 403: don't reveal that it exists
    return ticket

async def list_for_user(self, user: User, ...) -> list[Ticket]:
    stmt = select(Ticket)
    if user.role == Role.CUSTOMER:
        stmt = stmt.where(Ticket.customer_id == user.id)   # filter in SQL
    ...
```

### 9. Testing authenticated endpoints
```python
def auth_headers(client: TestClient, email: str, password: str = "password123") -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "full_name": "T", "password": password})
    resp = client.post("/auth/login", data={"username": email, "password": password})  # data= → form
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

def test_me(client: TestClient) -> None:
    headers = auth_headers(client, "a@example.com")
    assert client.get("/auth/me", headers=headers).json()["email"] == "a@example.com"
```
For speed, you can also override `get_current_user` with a fake user in tests that aren't about auth.

## Gotchas
- **Never store or log plain passwords.** Also never return `password_hash`. That's why `UserOut` exists.
- **Weak or default `JWT_SECRET`.** PyJWT warns (`InsecureKeyLengthWarning`) when an HS256 key is under 32
  bytes, and the default `change-me` triggers it. Generate a real one:
  `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"` and put it in `.env`.
- **Always pass `algorithms=["HS256"]` to `jwt.decode`.** Never let the token pick its own algorithm.
- **JWTs are signed, not encrypted.** Anyone can base64-decode the payload. Don't put secrets or PII in it.
- **Stateless means no instant logout.** A stolen token is valid until `exp`. Keep access tokens
  short (15–30 min). Refresh tokens and revocation lists are a later topic.
- **Same error for "no such user" and "wrong password"** (`401 Incorrect email or password`), so the
  API doesn't reveal which emails are registered.
- **Role must not come from the client.** `UserCreate` has no `role` field. Everyone registers as a customer, and
  an admin promotes agents. Trust the role from the **DB** (loaded in `get_current_user`). The JWT `role`
  claim is a convenience, not the source of truth.
- **Login is form data.** `client.post("/auth/login", json=...)` gives 422. Use `data=...`.
- **Hashing is deliberately slow** (tens of ms). That's fine for login. Don't hash in hot loops in tests.
  Create a fixture user once per test instead.

## Exercises
1. Hash the same password twice. Are the hashes equal? Does `verify` work for both? Why?
2. Create a token with `exp` 1 second in the future, wait 2 seconds and decode it. Which exception do you get?
   Is it a subclass of `jwt.InvalidTokenError`?
3. Decode a token's payload **without** the secret using only `base64` and `json`. What does this
   teach you about JWT contents?
4. Write `require_role` without looking, then a test proving a customer gets 403 on an agent-only route.
5. Why does `get_ticket` return 404 instead of 403 when a customer requests someone else's ticket?

<details><summary>Answers</summary>

1. No. Each hash has a random salt. `verify` works for both because the salt is stored inside the hash string.
2. `jwt.ExpiredSignatureError`. Yes, it subclasses `InvalidTokenError`, so catching the base class covers both.
3. ```python
   import base64, json
   part = token.split(".")[1]
   part += "=" * (-len(part) % 4)            # restore base64 padding
   print(json.loads(base64.urlsafe_b64decode(part)))
   ```
   The payload is public. The signature only proves it wasn't modified.
4. See Example 6. Test: register (customer), log in, call an `AgentUser` route, and assert 403.
5. A 403 confirms that the ticket ID exists, which leaks information. A 404 treats "not yours" the same as "doesn't exist".
</details>

## Apply to TriageDesk: M4
**Goal:** Users can register and log in. Every ticket endpoint requires auth. Customers create and
see only their own tickets, while agents and admins see and triage all of them.

**Packages**
```bash
uv add pyjwt "pwdlib[argon2]"
```

**Files**
| File | Purpose |
|---|---|
| `app/core/security.py` | `hash_password`, `verify_password`, `create_access_token`, `decode_access_token` |
| `app/models/user.py` | `Role` enum + `User` model. Remember to import it in `app/models/__init__.py`. |
| `app/models/ticket.py` (edit) | add `customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)` |
| `app/schemas/user.py` | `UserCreate`, `UserOut`, `Token` |
| `app/services/auth_service.py` | `AuthService.register()`, `.authenticate()` |
| `app/services/ticket_service.py` (edit) | `list_for_user`, `get_for_user`; `create` takes the user |
| `app/api/deps.py` (edit) | `oauth2_scheme`, `get_current_user`, `CurrentUser`, `require_role`, `AgentUser`, `AdminUser` |
| `app/api/routes/auth.py` | `/auth/register`, `/auth/login`, `/auth/me` |
| `app/api/routes/users.py` | `PATCH /users/{id}/role` (admin) |
| `alembic/versions/*_add_users.py` | autogenerated. Read it! |
| `scripts/create_admin.py` | CLI to bootstrap the first admin (`uv run python scripts/create_admin.py email password`) |
| `tests/test_auth.py`, `tests/test_ticket_permissions.py` | tests |

**Endpoint spec**
| Method | Path | Who | Request | Response | Codes |
|---|---|---|---|---|---|
| POST | `/auth/register` | anyone | `UserCreate` JSON | `UserOut` (role = customer) | 201, 409 email taken, 422 |
| POST | `/auth/login` | anyone | form: `username` (email), `password` | `Token` | 200, 401 |
| GET | `/auth/me` | any logged-in user | — | `UserOut` | 200, 401 |
| PATCH | `/users/{user_id}/role` | admin | `{"role": "agent"}` | `UserOut` | 200, 401, 403, 404 |
| POST | `/tickets` | customer (agents too) | `TicketCreate` (now **without** `customer_email`; it comes from the user) | `TicketOut` | 201, 401 |
| GET | `/tickets` | customer → own only; agent/admin → all | filters as before | `list[TicketOut]` | 200, 401 |
| GET | `/tickets/{id}` | owner, agent, admin | — | `TicketOut` | 200, 401, 404 (also for "not yours") |
| PATCH | `/tickets/{id}` | agent, admin (status/priority/category) | `TicketUpdate` | `TicketOut` | 200, 401, 403, 404 |
| DELETE | `/tickets/{id}` | admin | — | — | 204, 401, 403, 404 |

**Acceptance criteria**
- [ ] Passwords are stored as Argon2 hashes, and no response ever includes `password_hash`
- [ ] Duplicate email → 409 with `code: "conflict"` (from your M3 `ConflictError`)
- [ ] Wrong password and unknown email both → 401 with the same message
- [ ] Expired or tampered token → 401
- [ ] The `/docs` 🔒 Authorize button works: log in there and call `/auth/me`
- [ ] Customer A can't see customer B's ticket (404) and doesn't see it in the list
- [ ] Customer → PATCH ticket gives 403. Agent → PATCH gives 200.
- [ ] `JWT_SECRET` comes from settings, and `.env.example` documents how to generate one
- [ ] Tests cover all the rules above. Use a fixture that returns auth headers for a given role.
- [ ] Migration applied, earlier tests updated (they now need auth), `ruff` + `pytest` green

**Hints**
- In `TicketOut`, keep `customer_email` by loading it from the user, or switch to `customer_id`.
  Pick one and update the M1 tests. Simplest: keep a `customer_email` column copied from the user at create time.
- To make a test agent, register normally, then update `role` directly through the test session
  (or through the admin endpoint with a fixture admin).
- `OAuth2PasswordBearer(tokenUrl="/auth/login")`: the `tokenUrl` must match your login route path.
- Existing tickets in your dev DB have no `customer_id`. Easiest: delete `triagedesk.db` and re-run migrations.
  (Making the column nullable, or adding a data migration, is the "real world" alternative.)

<details><summary>Reference sketch (peek only after trying)</summary>

```python
# app/services/auth_service.py (partial)
class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, data: UserCreate) -> User:
        existing = await self.session.scalar(select(User).where(User.email == data.email.lower()))
        if existing is not None:
            raise ConflictError("Email already registered")
        user = User(
            email=data.email.lower(),
            full_name=data.full_name,
            password_hash=hash_password(data.password),
        )
        self.session.add(user)
        await self.session.commit()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.session.scalar(select(User).where(User.email == email.lower()))
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Incorrect email or password")   # AppError, status 401
        return user
```
```python
# tests/conftest.py: headers for any role (partial)
@pytest.fixture
def make_user_headers(client, session_factory):
    def _make(role: Role = Role.CUSTOMER, email: str | None = None) -> dict[str, str]:
        email = email or f"{role}-{uuid4().hex[:6]}@example.com"
        client.post("/auth/register", json={"email": email, "full_name": "T", "password": "password123"})
        if role != Role.CUSTOMER:
            ...  # promote via the session (asyncio.run) or the admin endpoint
        token = client.post("/auth/login", data={"username": email, "password": "password123"})
        return {"Authorization": f"Bearer {token.json()['access_token']}"}
    return _make
```
</details>
