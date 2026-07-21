import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.database import connection, now_iso

bearer = HTTPBearer(auto_error=False)


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise HTTPException(422, "Enter a valid email address.")
    return value


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}:{derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, expected = stored.split(":", 1)
        actual = hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    with connection() as db:
        db.execute(
            "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
            (token_hash, user_id, now_iso(), expires.isoformat()),
        )
    return token


def delete_session(token: str) -> None:
    with connection() as db:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (hashlib.sha256(token.encode()).hexdigest(),))


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else request.cookies.get("contender_session")
    if not token:
        raise HTTPException(401, "Please log in to continue.", headers={"WWW-Authenticate": "Bearer"})
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        row = db.execute(
            """SELECT users.id, users.name, users.email, sessions.expires_at
               FROM sessions JOIN users ON users.id = sessions.user_id
               WHERE sessions.token_hash = ?""",
            (token_hash,),
        ).fetchone()
        if row and datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            row = None
    if not row:
        raise HTTPException(401, "Your session is invalid or expired.", headers={"WWW-Authenticate": "Bearer"})
    return {"id": row["id"], "name": row["name"], "email": row["email"], "token": token}
