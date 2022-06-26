from curses.ascii import US
from os import access
import requests as requests
from sqlalchemy import null
from db import *
from utils.models import *
from utils.auth import *

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.responses import RedirectResponse

SECRET_KEY = "7547b88b5922e3a3a99776b895d73f76b1a9fb1e57a500ae40160094953bf815"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
Session = setup()
s = Session()
#print(s.query(User).first().username)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def check_if_less_than_seven_days(x):
    d = datetime.strptime(str(x), "%Y-%m-%d")
    now = datetime.now()                 
    return (d - now).days < 7

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

@app.get("/")
async def index():
    return {"Hello":"World"}

@app.get("/yauth")
async def auth_with_yandex():
    url='https://oauth.yandex.ru/authorize?response_type=token&client_id=3525df3335254c57a6df4e48c670809b'
    
    return {"authurl":url}

@app.get("/yoauth")
def proceed_url_token(request: Request,acces_token: str  = ""):
    if acces_token != '':
        url = 'https://login.yandex.ru/info?'
        header = {'Authorization': f'OAuth {acces_token}'}
        data = requests.get(url,headers = header).json()
        username = data["login"]
        user = s.query(User).filter(User.username == username).first()
        if not user:
            data = requests.post("https://apapers.herokuapp.com" + app.url_path_for('user_registration'),json = {"username":username,"password":str(data["id"])}).json()
            return data
        else:
            data = requests.post("https://apapers.herokuapp.com" + app.url_path_for('login_for_acces_token'),data = {"username":username,"password":str(data["id"])}).json()
            return data

            
            
        
        
        

@app.get("/papers/")
async def read_papers(current_user: User = Depends(get_current_user),sortby: str = '',author: str = '',words: str = '',theme: str = '',digestit:bool = True):
    if current_user.read or current_user.adm:
        data = []
        for paper in s.query(Paper):
            line = [paper]
            if sortby == "rate":
                line = [paper,get_rating(s,paper.id)]
            if sortby == "views":
                line = [paper,paper.views]
            if sortby == "title":
                line = [paper,paper.title]
            if sortby == "content":
                line = paper
            if sortby == "words":
                if words == '':
                    raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY,detail="Specify the words to sort by it")
                elif words in paper.content:
                    line = [paper]
                else:
                    line = []
            if sortby == "author":
                user = s.query(User).filter(User.username == author).first()
                if not user:
                    raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY,detail="Specify the author that exist to sort by it")
                elif user.id in paper.users:
                    line = [paper]
                else:
                    line = []
            if sortby == "date":
                if paper.datePublushed != None:
                    line = paper
                else:
                    line = []
            if sortby == "theme":
                if theme == '' or theme != paper.theme:
                    line = []
                else:
                    line = [paper] 
            if line != []: 
                data.append(line)
        if sortby in ["rate","views"]:
            data = sorted(data,key = lambda data: data[1])[::-1]
        if sortby in ["title"]:
            data = sorted(data,key = lambda data: data[1])
        if sortby in ["content"]:
            data = sorted(data,key = lambda paper: paper[0].content)
        if sortby in ["date"]:
            data = sorted(data,key = lambda paper: paper[0].datePublushed)
        digest = []
        if digestit:
            for paper in data:
                if paper[0].status == 3 and check_if_less_than_seven_days(paper[0].datePublushed):
                    digest.append(paper)
            data = digest
        return data
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to read that")
            
@app.get("/papers/{paper_id}")
async def read_paper(paper_id:int,current_user: User = Depends(get_current_user)):
    if current_user.read or current_user.adm:
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        paper.views += 1
        s.commit()
        line = [paper]
        for comment in s.query(Comment).filter(Comment.paper_id == paper.id):
                line.append(comment)
        for rating in s.query(Rating).filter(Rating.paper_id == paper.id):
                line.append(rating)
        return line
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to read that")

@app.post("/papers/write")
async def create_paper(paper_draft: PaperCreate,current_user: User = Depends(get_current_user)):
    if current_user.write or current_user.adm:
        paper = Paper(title=paper_draft.title,content = paper_draft.content,status = 0,users = [current_user.id])
        if paper_draft.theme:
            paper.theme = paper_draft.theme
        s.add(paper)
        s.commit()
        return {"status":"ok"}
    else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")

@app.post("/papers/{paper_id}/rate")
async def rate_paper(paper_id:int,paper_rate:RatePaper,current_user: User = Depends(get_current_user)):
    if current_user.read or current_user.adm:
        paper = s.get(Paper,paper_id)
        paper_rate = paper_rate.value
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if paper_rate > 5 or paper_rate < 0:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Invalid rating score")
        for rate in s.query(Rating).filter(Rating.paper_id == paper_id):
            if rate.user_id == current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Paper already rated")
        rate = Rating(value = paper_rate,user_id = current_user.id,paper_id = paper.id)
        s.add(rate)
        s.commit()
        return {"status":"ok"}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to read that")

@app.post("/papers/{paper_id}/comment")
async def rate_paper(paper_id:int,cmt_str:CommentPaper,current_user: User = Depends(get_current_user)):
    if current_user.read or current_user.adm:
        cmt_str = cmt_str.comment
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        comment = Comment(content = cmt_str,user_id = current_user.id,paper_id = paper.id)
        s.add(comment)
        s.commit()
        return {"status":"ok"}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to read that")


     
@app.post("/register")
async def user_registration(user: UserRegister):
    user_info = user.dict()
    user_info['password'] = get_hashed_password(user_info['password'])
    if not get_user(user_info["username"],s):       
        create_user(user_info["username"],user_info["password"],s)
        return {"status":"ok","data":f"{user_info['username']} created"}
    else:
        raise HTTPException(status_code=400,detail="Username Taken")

@app.post("/login")
async def login_for_acces_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(session = s, password = form_data.password, username = form_data.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect username or password",headers={"WWW-Authenticate":"Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub":user.username},expires_delta=access_token_expires,secret_key=SECRET_KEY,algo=ALGORITHM)
    return {"access_token":access_token,"token_type":"bearer"}

@app.get("/make.me.admin/")
async def make_me_admin(current_user: User = Depends(get_current_user)):
    s.get(User,current_user.id).adm = True
    s.commit()
    return {"status":"ok"}
#-----------------------------------------------------------------------------------------------------------------------------
@app.patch("/adm/paper/{paper_id}")
async def update_papers(paper_id: int,paper_update: PaperUpdate,current_user: User = Depends(get_current_user)):
    if current_user.adm:
        data = paper_update
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="paper not found")
        if paper and paper.status == 0 and (current_user.id in paper.users or current_user.adm):
            if paper_update.title:
                paper.title =  paper_update.title
            if paper_update.content:
                paper.content = paper_update.content
            if paper_update.status:
                paper.status = paper_update.status
            if paper_update.added_users:
                paper.users = paper.users + paper_update.added_users
            s.commit()
        return {"status":"updated"}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")
        
@app.patch("/adm/user/{user_id}")
async def update_users(user_id: int,user_update: UserUpdate,current_user: User = Depends(get_current_user)):
    if current_user.adm:
        data = user_update
        user = s.get(User,user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="user not found")
        
        if data.active != None:
            user.active = data.active
        if data.read != None:
            user.read = data.read
        if data.write != None:
            user.write = data.write
        if data.mod != None:
            user.mod = data.mod
        if data.adm != None:
            user.adm = data.adm
        s.commit()
        return {"status":"updated"}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")

@app.get("/adm/users/")
async def read_users(current_user: User = Depends(get_current_user)):
    if current_user.adm:
        data = []
        for user in s.query(User):
            data.append(user)
        return data  
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")
#-----------------------------------------------------------------------------------------------------------------------------
@app.get("/mod/papers/")
async def read_not_accepted_papers(current_user: User = Depends(get_current_user)):
    if current_user.adm or current_user.mod:
        data = []
        for paper in s.query(Paper).filter(Paper.status == 1):
            data.append(paper)
        return data  
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")

@app.get("/mod/papers/{paper_id}")
async def accept_paper(paper_id:int,accepted:bool = True,comment:str = "",current_user: User = Depends(get_current_user)):
    if current_user.adm or current_user.mod:
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="paper not found")
        if paper and paper.status == 1 and accepted:
            paper.status = 3
            paper.datePublushed = datetime.now()
            s.commit()
            return {"status":"accepted"}
        elif not accepted and paper and paper.status == 1:
            if not comment:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="denial comment req")
            paper.status = 2
            paper.modComment = comment
            s.commit()
            return {"status":"denied"}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="paper still in draft")

#-----------------------------------------------------------------------------------------------------------------------------
@app.get("/users/me/")
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/users/papers/")
async def read_my_papers(current_user: User = Depends(get_current_user)):
    if current_user.adm or current_user.read:
        data = []
        for paper in s.query(Paper):
            if current_user.id in paper.users:
                data.append(paper)
        return data  
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")

@app.get("/users/papers/{paper_id}/validate")
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

@app.get("/users/papers/{paper_id}/to_draft")
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


@app.get("/users/papers/{paper_id}")
async def read_my_paper(paper_id:int,current_user: User = Depends(get_current_user)):
    if current_user.read or current_user.adm:
        paper = s.get(Paper,paper_id)
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return paper

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to read that")

@app.patch("/users/papers/{paper_id}")
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
            s.commit()
        return {"status":"updated","detail":paper}

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not allowed to do that")
  





