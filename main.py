import requests as requests
from db import *
from utils.models import *
from utils.auth import *
from routers.user import *

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()
Session = setup()
s = Session()
#print(s.query(User).first().username)
app.include_router(user_router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def check_if_less_than_seven_days(x):
    d = datetime.strptime(str(x), "%Y-%m-%d")
    now = datetime.now()                 
    return (d - now).days < 7

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
            data = sorted(data,key = lambda paper: paper.content)
        if sortby in ["date"]:
            data = sorted(data,key = lambda paper: paper.datePublushed)
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
        if paper:
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
