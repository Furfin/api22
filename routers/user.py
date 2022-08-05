from fastapi import APIRouter

import requests as requests
from db import *
from ..utils.models import *
from ..utils.auth import *
from ..main import *

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

SECRET_KEY = "7547b88b5922e3a3a99776b895d73f76b1a9fb1e57a500ae40160094953bf815"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

Session = setup()
s = Session()

user_router = APIRouter()

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

@user_router.get("/")
async def index():
    return {"Hello":"World"}

@user_router.post("/login")
async def login_for_acces_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(session = s, password = form_data.password, username = form_data.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect username or password",headers={"WWW-Authenticate":"Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub":user.username},expires_delta=access_token_expires,secret_key=SECRET_KEY,algo=ALGORITHM)
    return {"access_token":access_token,"token_type":"bearer"}

@user_router.post("/register")
async def user_registration(user: UserRegister):
    user_info = user.dict()
    user_info['password'] = get_hashed_password(user_info['password'])
    if not get_user(user_info["username"],s):       
        create_user(user_info["username"],user_info["password"],s)
        return {"status":"ok","data":f"{user_info['username']} created"}
    else:
        raise HTTPException(status_code=400,detail="Username Taken")

@user_router.get("/yauth")
async def auth_with_yandex():
    url='https://oauth.yandex.ru/authorize?response_type=token&client_id=3525df3335254c57a6df4e48c670809b'
    
    return {"authurl":url}

@user_router.get("/yoauth")
def proceed_url_token(request: Request,acces_token: str  = ""):
    if acces_token != '':
        url = 'https://login.yandex.ru/info?'
        header = {'Authorization': f'OAuth {acces_token}'}
        data = requests.get(url,headers = header).json()
        username = data["login"]
        user = s.query(User).filter(User.username == username).first()
        if not user:
            data = requests.post("https://apapers.herokuapp.com" + user_router.url_path_for('user_registration'),
                                 json = {"username":username,"password":str(data["id"])}).json()
            return data
        else:
            data = requests.post("https://apapers.herokuapp.com" + user_router.url_path_for('login_for_acces_token'),
                                 data = {"username":username,"password":str(data["id"])}).json()
            return data

@user_router.get("/users/me/")
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@user_router.get("/users/papers/")
async def read_my_papers(current_user: User = Depends(get_current_user)):
    if current_user.adm or current_user.read:
        data = []
        for paper in s.query(Paper):
            if current_user.id in paper.users:
                data.append(paper)
        return data  
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")

@user_router.get("/users/papers/{paper_id}/validate")
async def to_mod_paper(paper_id:int,current_user: User = Depends(get_current_user)):
    if current_user.adm or current_user.write:
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="paper not found")
        if current_user.id not in paper.users:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")
        if paper and paper.status == 0:
            paper.status = 1
            s.commit()
            return {"status":"waiting validation"}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="paper still in draft")

@user_router.get("/users/papers/{paper_id}/to_draft")
async def to_draft_paper(paper_id:int,current_user: User = Depends(get_current_user)):
    if current_user.adm or current_user.write:
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="paper not found")
        if current_user.id not in paper.users:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")
        if paper and paper.status != 0:
            paper.status = 0
            paper.modComment = ""
            s.commit()
            return {"status":"drafting"}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="paper still in draft")


@user_router.get("/users/papers/{paper_id}")
async def read_my_paper(paper_id:int,current_user: User = Depends(get_current_user)):
    if current_user.read or current_user.adm:
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return paper
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to read that")

@user_router.patch("/users/papers/{paper_id}")
async def update_paper_draft(paper_id: int,paper_update: PaperUpdate,current_user: User = Depends(get_current_user)):
    if current_user.write or current_user.adm:
        data = paper_update
        paper = s.get(Paper,paper_id)
        if current_user.id not in paper.users:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if paper and paper.status == 0 and (current_user.id in paper.users or current_user.adm):
            if paper_update.title:
                paper.title =  paper_update.title
            if paper_update.content:
                paper.content = paper_update.content
            if paper_update.theme:
                paper.theme = paper_update.theme
            if paper_update.added_users:
                paper.users = paper.users + paper_update.added_users
            s.commit()
            return {"status":"updated","detail":paper}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")

