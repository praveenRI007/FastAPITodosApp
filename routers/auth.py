import sys
sys.path.append("..")

from starlette.responses import RedirectResponse

from fastapi import Depends, HTTPException, status, APIRouter, Request, Response, Form
from pydantic import BaseModel , root_validator , ValidationError
from typing import Optional
import models
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pytz

IST = pytz.timezone('Asia/Kolkata')
#IST = None

SECRET_KEY = "KlgH6AzYDeZeGwD288to79I3vTHT8wp7"
ALGORITHM = "HS256"

templates = Jinja2Templates(directory="templates")

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

models.Base.metadata.create_all(bind=engine)

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="token")


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={401: {"user": "Not authorized"}}
)


class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    async def create_oauth_form(self):
        form = await self.request.form()
        self.username = form.get("email")
        self.password = form.get("password")


class RegisterForm(BaseModel):
    email: str
    username: str
    firstname: str
    lastname: str
    password: str
    password2: str

    @root_validator()
    def verify_password_match(cls, values):
        password = values.get("password")
        password2 = values.get("password2")

        if password != password2:
            raise ValueError("The two passwords did not match.")
        return values



def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_password_hash(password):
    return bcrypt_context.hash(password)


def verify_password(plain_password, hashed_password):
    return bcrypt_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str, db):
    user = db.query(models.Users)\
        .filter(models.Users.username == username)\
        .first()

    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(username: str, user_id: int,
                        expires_delta: Optional[timedelta] = None):

    encode = {"sub": username, "id": user_id}
    if expires_delta:
        expire = datetime.now(IST) + expires_delta
    else:
        expire = datetime.now(IST) + timedelta(minutes=15)
    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(request: Request):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            logout(request)
        return {"username": username, "id": user_id}
    except ExpiredSignatureError:
        return None
        #raise HTTPException(status_code=404, detail="token expired , refresh token cannot be requested , time exceeded")
    except JWTError:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/token")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(),
                                 db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        return False
    token_expires = timedelta(minutes=10)
    token = create_access_token(user.username,
                                user.id,
                                expires_delta=token_expires)
    dt = datetime.now(IST) + timedelta(minutes=10)
    response.headers["Authorization"] = "Bearer "+ token
    response.set_cookie(key="access_token", value=token)
    response.set_cookie(key="access_token_expirationIn", value=str(dt))

    return True

@router.post("/refresh-token/")
async def login_for_refresh_access_token(request: Request, response: Response):
    token = request.cookies.get("access_token")
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        response = templates.TemplateResponse("login.html", {"request": request, "msg": "access token expired , cannot request for refresh token"})
        return response

    username: str = payload.get("sub")
    user_id: int = payload.get("id")

    token_expires = timedelta(minutes=10)

    token = create_access_token(username,
                                user_id,
                                expires_delta=token_expires)
    dt = datetime.now(IST) + timedelta(minutes=10)
    response.headers["Authorization"] = "Bearer " + token
    response.set_cookie(key="access_token", value=token)
    response.set_cookie(key="access_token_expirationIn", value=str(dt))

    return True


@router.get("/", response_class=HTMLResponse)
async def authentication_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    global IST
    try:
        form = LoginForm(request)
        await form.create_oauth_form()
        response = RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)

        validate_user_cookie = await login_for_access_token(response=response, form_data=form, db=db)

        if not validate_user_cookie:
            msg = "Incorrect Username or Password"
            return templates.TemplateResponse("login.html", {"request": request, "msg": msg})
        IST = pytz.timezone(request.cookies.get("ClientTimeZone"))
        return response
    except HTTPException:
        msg = "Unknown Error"
        return templates.TemplateResponse("login.html", {"request": request, "msg": msg})


@router.get("/logout")
async def logout(request: Request):
    msg = "Logout Successful"
    response = templates.TemplateResponse("login.html", {"request": request, "msg": msg})
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="access_token_expirationIn")
    return response


@router.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, email: str = Form(...), username: str = Form(...),
                        firstname: str = Form(...), lastname: str = Form(...),
                        password: str = Form(...), password2: str = Form(...),
                        db: Session = Depends(get_db)):
    try:
        RegisterForm(email=email,username=username,firstname=firstname,lastname=lastname,password=password,password2=password2)
    except ValidationError:
        msg = "password mismatch"
        return templates.TemplateResponse("register.html", {"request": request, "msg": msg})

    validation1 = db.query(models.Users).filter(models.Users.username == username).first()

    validation2 = db.query(models.Users).filter(models.Users.email == email).first()

    if password != password2 or validation1 is not None or validation2 is not None:
        msg = "Invalid registration request"
        return templates.TemplateResponse("register.html", {"request": request, "msg": msg})

    user_model = models.Users()
    user_model.username = username
    user_model.email = email
    user_model.first_name = firstname
    user_model.last_name = lastname

    hash_password = get_password_hash(password)
    user_model.hashed_password = hash_password
    user_model.is_active = True

    db.add(user_model)
    db.commit()

    msg = "User successfully created"
    return templates.TemplateResponse("login.html", {"request": request, "msg": msg})
