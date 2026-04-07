import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


def require_admin_token(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    if not (settings.admin_token and settings.admin_token.strip()):
        raise HTTPException(
            status_code=503,
            detail="Admin writes are disabled (set JOINTED_ADMIN_TOKEN on the server).",
        )
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authorization: Bearer <token> required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    a, b = creds.credentials, settings.admin_token
    if len(a) != len(b) or not secrets.compare_digest(a, b):
        raise HTTPException(status_code=403, detail="Invalid token.")
