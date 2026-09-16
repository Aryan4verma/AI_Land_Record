"""Auth endpoints per 10_API_SPECIFICATION section 2.

POST /api/v1/auth/login    — email + password -> Bearer token
POST /api/v1/auth/register — self-registration -> created account (no token;
    the client proceeds to login per the required register-then-login flow).
    Always creates the read-only `user` role; operator accounts are
    provisioned out-of-band.
POST /api/v1/auth/logout   — stateless; client discards the token
GET  /api/v1/auth/me       — current user, refetched from the user store
"""
from fastapi import APIRouter, Depends, Request

from ..config import get_settings
from ..errors import AppError
from ..logging_config import get_logger
from .dependencies import ROLE_HIERARCHY, get_current_user, normalize_role
from .rate_limit import get_login_limiter, login_key
from .schemas import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse, UserOut
from .security import create_access_token, hash_password, verify_password
from .store import UserStore, get_user_store

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request,
          store: UserStore = Depends(get_user_store)) -> TokenResponse:
    limiter = get_login_limiter()
    key = login_key(request.client.host if request.client else None, body.email)
    if limiter.is_blocked(key):
        # Same opaque wording as a bad password: never reveal whether the
        # account exists, only that further attempts are refused for now.
        log.warning("login throttled")
        raise AppError(429, "TOO_MANY_ATTEMPTS",
                       "Too many failed sign-in attempts. Try again later.")
    user = store.get_by_email(body.email.strip().lower())
    if (
        not user
        or user.get("status") != "active"
        or not user.get("password_hash")
        or not verify_password(body.password, user["password_hash"])
    ):
        # Identical response for every failure: no account enumeration.
        limiter.record_failure(key)
        log.warning("login failed")
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    settings = get_settings()
    role = normalize_role(user.get("role"))
    if role not in ROLE_HIERARCHY:
        # A stored role we no longer honour (e.g. a legacy `verifier` row)
        # must fail closed rather than be guessed at.
        limiter.record_failure(key)
        log.warning("login rejected: unsupported stored role")
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    token = create_access_token(
        user_id=user["id"],
        role=role,
        secret=settings.auth_secret,
        expires_minutes=settings.auth_token_expire_minutes,
    )
    limiter.reset(key)  # a real sign-in clears the counter
    return TokenResponse(access_token=token)


_MAX_REGISTER_FIELD = 200  # shared ceiling; per-field maxima live on the schema

# Self-registration is capped at the read-only role. Raising this would let
# anyone grant themselves the review/approval workflow — never change it
# without also adding a controlled provisioning path.
DEFAULT_REGISTRATION_ROLE = "user"


@router.post("/register", status_code=201, response_model=RegisterResponse)
def register(body: RegisterRequest, store: UserStore = Depends(get_user_store)) -> RegisterResponse:
    name = body.name.strip()
    id_number = body.id_number.strip()
    email = body.email.strip().lower()
    if not name:
        raise AppError(422, "NAME_REQUIRED", "Name is required.")
    if not id_number:
        raise AppError(422, "ID_NUMBER_REQUIRED", "ID number is required.")
    if "@" not in email:
        raise AppError(422, "INVALID_EMAIL", "Enter a valid email address.")
    if store.get_by_email(email) is not None:
        # Friendly duplicate message (no enumeration concern: registration
        # legitimately tells the user the email is taken). The UNIQUE(email)
        # constraint backstops the check-then-insert race in the store.
        log.warning("registration rejected: email taken")
        raise AppError(409, "USER_EXISTS", "An account with this email already exists.")
    created = store.create_user(
        {
            "name": name[:_MAX_REGISTER_FIELD],
            "id_number": id_number[:64],
            "email": email,
            "password_hash": hash_password(body.password),
            # Fixed least-privilege role: never accepted from the client.
            # Self-registration can ONLY create `user` (read-only). Operator
            # accounts are provisioned out-of-band (13_DEPLOYMENT_RUNBOOK).
            "role": DEFAULT_REGISTRATION_ROLE,
            "status": "active",
        }
    )
    log.info("account registered")
    return RegisterResponse(
        id=str(created["id"]),
        name=created.get("name") or name,
        id_number=created.get("id_number"),
        email=created.get("email") or email,
        role=created.get("role") or DEFAULT_REGISTRATION_ROLE,
        status=created.get("status") or "active",
        created_at=str(created.get("created_at") or ""),
    )


@router.post("/logout")
def logout() -> dict:
    return {"status": "ok", "message": "Discard the access token on the client; no server session exists."}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user), store: UserStore = Depends(get_user_store)) -> dict:
    full = store.get_by_id(user["id"])
    if not full or full.get("status") != "active":
        raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.")
    return full
