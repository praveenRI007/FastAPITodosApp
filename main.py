import uvicorn
from fastapi import FastAPI, Depends, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import time
from middlewares import MyMiddleware, AdvancedMiddleware
import random
import string
from collections import defaultdict
from typing import Dict

import models
from database import engine, check_db_connected, check_db_disconnected
from routers import auth, todos, users
from starlette.staticfiles import StaticFiles

from settings import Settings
from jose import jwt, JWTError, ExpiredSignatureError

app = FastAPI()

app.mount('/static', StaticFiles(directory='static', html=True), name='static')

app.add_middleware(MyMiddleware, some_attribute="some_attribute_here_if_needed")
# app.add_middleware(AdvancedMiddleware)

settings = Settings()

origins = [
    "http://localhost",
    "http://localhost:8080",
]

# app.add_middleware(HTTPSRedirectMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# middleware for appending request response time in request
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


models.Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(users.router)


@app.get("/testdata")
async def read_main():
    return {"msg": "Hello World"}


@app.on_event("startup")
async def app_startup():
    await check_db_connected()


@app.on_event("shutdown")
async def app_shutdown():
    await check_db_disconnected()


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/register")


# depreciated : below @app.middleware("http")

# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     start_time = time.time()
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     response.headers["X-Process-Time"] = str(process_time)
#     return response


# @app.middleware("http")
# async def check_jwt(request: Request, call_next):
#     header = request.headers.get('Authorization')
#     if header is None:
#         return {"msg": "access token expired , cannot request for refresh token"}
#     bearer, token = header.split()
#
#
#     try:
#         if token is None:
#             return {"msg": "access token expired , cannot request for refresh token"}
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#         username: str = payload.get("sub")
#         user_id: int = payload.get("id")
#         if username is None or user_id is None:
#             return {"msg": "access token expired , cannot request for refresh token"}
#     except ExpiredSignatureError:
#         return {"msg": "access token expired , cannot request for refresh token"}
#         #raise HTTPException(status_code=404, detail="token expired , refresh token cannot be requested , time exceeded")
#     except JWTError:
#         return {"msg": "access token expired , cannot request for refresh token"}
#
#     response = await call_next(request)
#     return response


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
