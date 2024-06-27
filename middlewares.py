import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from functools import wraps
from settings import Settings
from jose import jwt, JWTError, ExpiredSignatureError
import random
import string
from collections import defaultdict
from typing import Dict
import time

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


# rate limiting middleware (DDOS prevention)

class AdvancedMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_records: Dict[str, float] = defaultdict(float)

    async def log_message(self, message: str):
        print(message)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        if current_time - self.rate_limit_records[client_ip] < 100:  # 1 request per second limit
            return Response(content="Rate limit exceeded", status_code=429)

        self.rate_limit_records[client_ip] = current_time

        # Asynchronous logging
        path = request.url.path
        await self.log_message(f"Request to {path}")

        # Process the request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add custom headers without modifying the original headers object
        custom_headers = {"X-Process-Time": str(process_time)}
        for header, value in custom_headers.items():
            response.headers.append(header, value)

        # Asynchronous logging for processing time
        await self.log_message(f"Response for {path} took {process_time} seconds")

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
            # raise HTTPException(status_code=404, detail="token expired , refresh token cannot be requested , time exceeded")
        except JWTError:
            return {"msg": "access token expired , cannot request for refresh token"}

        return func(*args, **kwargs)

    return decorated
