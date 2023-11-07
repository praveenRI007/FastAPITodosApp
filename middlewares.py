import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from functools import wraps
from settings import Settings
from jose import jwt, JWTError, ExpiredSignatureError

settings = Settings()


class MyMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            some_attribute: str,
    ):
        super().__init__(app)
        self.some_attribute = some_attribute

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time) + " seconds"
        return response


def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        header = Request.headers.get('Authorization')
        if header is None:
            return {"msg": "access token expired , cannot request for refresh token"}
        bearer, token = header.split()


        try:
            if token is None:
                return {"msg": "access token expired , cannot request for refresh token"}
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            user_id: int = payload.get("id")
            if username is None or user_id is None:
                return {"msg": "access token expired , cannot request for refresh token"}
        except ExpiredSignatureError:
            return {"msg": "access token expired , cannot request for refresh token"}
            #raise HTTPException(status_code=404, detail="token expired , refresh token cannot be requested , time exceeded")
        except JWTError:
            return {"msg": "access token expired , cannot request for refresh token"}

        return func(*args, **kwargs)

    return decorated
