from typing import Union
from pydantic import BaseModel
from db import *
from utils.models import *
from utils.auth import *

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

SECRET_KEY = "7547b88b5922e3a3a99776b895d73f76b1a9fb1e57a500ae40160094953bf815"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
Session = setup()
s = Session()
#print(s.query(User).first().username)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    exception = HTTPException(status_code=401,detail="Could not validate credetials",headers={"WWW-Authenticate":"Bearer"})
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise exception
        token_data = TokenData(username=username)
    except JWTError:
        raise exception
    user = get_user(username=token_data.username,session=s)
    if user is None:
        raise exception
    if not user.active:
        raise HTTPException(status_code=400,detail="Inactive user")
    return user

@app.post("/register")
def user_registration(user: UserRegister):
    user_info = user.dict()
    user_info['password'] = get_hashed_password(user_info['password'])
    if not get_user(user_info["username"],s):       
        create_user(user_info["username"],user_info["password"],s)
        return {"status":"ok","data":f"{user_info['username']} created"}
    else:
        raise HTTPException(status_code=400,detail="Username Taken")

@app.post("/login")
def  login_for_acces_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(session = s, password = form_data.password, username = form_data.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                      detail="Incorrect username or password",
                      headers={"WWW-Authenticate":"Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub":user.username},expires_delta=access_token_expires,secret_key=SECRET_KEY,algo=ALGORITHM)
    return {"access_token":access_token,"token_type":"bearer"}

@app.get("/users/me/")
def read_me(current_user: User = Depends(get_current_user)):
    return current_user.username

@app.get("/")
def index():
    return {"Hello":"World"}

