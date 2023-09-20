from fastapi import FastAPI, Depends
from starlette.responses import RedirectResponse

import models
from database import engine
from routers import auth, todos , users
from starlette.staticfiles import StaticFiles

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/register")
