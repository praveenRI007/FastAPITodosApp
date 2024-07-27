import json
import pickle
import sys
from datetime import timedelta
sys.path.append("..")

from starlette import status
from starlette.responses import RedirectResponse

from fastapi import Depends, APIRouter, Request, Form
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from .auth import get_current_user

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import redis

from models import MtoDos
# from database import collection_name
from schemas.schema import list_serial, individual_serial
from bson import ObjectId
from settings import Settings

Settings = Settings()

router = APIRouter(
    prefix="/todos",
    tags=["todos"],
    responses={404: {"description": "Not found"}}
)

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
async def read_all_by_user(request: Request, db: Session = Depends(get_db)):

    # r = redis.Redis(host='redis-10708.c264.ap-south-1-1.ec2.cloud.redislabs.com',port=10708,password='IxJp9N3b3IiIoVusSXcLYirS0bNOCyjC')
    r = {}
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    # cache = r.get(str(models.Todos.owner_id) + "-todos")
    cache = False
    if cache:
        # r.delete(str(models.Todos.owner_id) + "-todos")
        print('cache hit')
        todos = pickle.loads(cache)
    else:
        print('cache miss')
        if not Settings.isMongoTrue:
            todos = db.query(models.Todos).filter(models.Todos.owner_id == user.get("id")).all()
        else:
            # mongo
            todos = list_serial(collection_name.find())

        # r.set(str(models.Todos.owner_id) + "-todos",pickle.dumps(todos),ex=timedelta(minutes=1))

    return templates.TemplateResponse("home.html", {"request": request, "todos": todos, "user": user})


@router.get("/add-todo", response_class=HTMLResponse)
async def add_new_todo(request: Request):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("add-todo.html", {"request": request, "user": user})


@router.post("/add-todo", response_class=HTMLResponse)
async def create_todo(request: Request, title: str = Form(...), description: str = Form(...),
                      priority: int = Form(...), db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    if not Settings.isMongoTrue:
        todo_model = models.Todos()
        todo_model.title = title
        todo_model.description = description
        todo_model.priority = priority
        todo_model.complete = False
        todo_model.owner_id = user.get("id")
        db.add(todo_model)
        db.commit()
    else:
        # mongo
        tmptodos = MtoDos(title=title, description=description, priority=priority, complete=False,
                          owner_id=int(user.get("id")))
        collection_name.insert_one(dict(tmptodos))

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


@router.get("/edit-todo/{todo_id}", response_class=HTMLResponse)
async def edit_todo(request: Request, todo_id: str, db: Session = Depends(get_db)):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    if not Settings.isMongoTrue:
        todo = db.query(models.Todos).filter(models.Todos.id == int(todo_id)).first()
    else:
        # mongo
        todo = individual_serial(collection_name.find_one({"_id": ObjectId(str(todo_id))}))

    return templates.TemplateResponse("edit-todo.html", {"request": request, "todo": todo, "user": user})


@router.post("/edit-todo/{todo_id}", response_class=HTMLResponse)
async def edit_todo_commit(request: Request, todo_id: str, title: str = Form(...),
                           description: str = Form(...), priority: int = Form(...),
                           db: Session = Depends(get_db)):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    if not Settings.isMongoTrue:
        todo_model = db.query(models.Todos).filter(models.Todos.id == int(todo_id)).first()

        todo_model.title = title
        todo_model.description = description
        todo_model.priority = priority

        db.add(todo_model)
        db.commit()
    else:
        # mongo
        mtodos = individual_serial(collection_name.find_one({"_id": ObjectId(str(todo_id))}))
        mtodos["title"] = title
        mtodos["description"] = description
        mtodos["priority"] = priority
        collection_name.find_one_and_update({"_id": ObjectId(str(todo_id))},{"$set":dict(mtodos)})

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


@router.get("/delete/{todo_id}")
async def delete_todo(request: Request, todo_id: str, db: Session = Depends(get_db)):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    if not Settings.isMongoTrue:
        todo_model = db.query(models.Todos).filter(models.Todos.id == int(todo_id)).filter(models.Todos.owner_id == user.get("id")).first()

        if todo_model is None:
            return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)

        db.query(models.Todos).filter(models.Todos.id == int(todo_id)).delete()

        db.commit()
    else:
        # mongo
        collection_name.find_one_and_delete({"_id": ObjectId(str(todo_id))})

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


@router.get("/complete/{todo_id}", response_class=HTMLResponse)
async def complete_todo(request: Request, todo_id: str, db: Session = Depends(get_db)):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    if not Settings.isMongoTrue:
        todo = db.query(models.Todos).filter(models.Todos.id == int(todo_id)).first()

        todo.complete = not todo.complete

        db.add(todo)
        db.commit()
    else:
        # mongo
        mtodos = individual_serial(collection_name.find_one({"_id": ObjectId(str(todo_id))}))
        mtodos["complete"] = not mtodos["complete"]
        collection_name.find_one_and_update({"_id": ObjectId(str(todo_id))}, {"$set": dict(mtodos)})

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)
