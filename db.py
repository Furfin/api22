from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column, Date, ForeignKey,Integer,String,create_engine,ARRAY
from sqlalchemy.orm import sessionmaker
import os

print(os.environ['DATABASE_URL'])
DATABASE_URI = os.environ['DATABASE_URL']
DATABASE_URI = DATABASE_URI.replace("postgres://", "postgresql://", 1)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer,primary_key=True)
    username = Column(String)
    hashed_password = Column(String)
    active = Column(Boolean,default = True)
    read = Column(Boolean,default = True)
    write = Column(Boolean,default = False)
    mod = Column(Boolean,default = False)
    adm = Column(Boolean,default = False)
    __repr__ = f"USER:{username}-{id} Status:{active} Read/Write/Mod/Adm:{read}-{write}-{mod}-{adm}"
class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer,primary_key=True)
    title = Column(String)
    content = Column(String)
    status = Column(Integer)#0-draft 1-validate 2-denied 3-accepted
    users = Column(ARRAY(Integer), default = [])
    modComment = Column(String,default = "")
    rates = Column(ARRAY(Integer), default = [])
    views = Column(Integer,default = 0)
    datePublushed = Column(Date,nullable = True)
    theme = Column(String, default = "general")    

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer,primary_key=True)
    content = Column(String)
    paper_id = Column(Integer,ForeignKey(Paper.id))
    user_id = Column(Integer,ForeignKey(User.id))
    
class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer,primary_key=True)
    value = Column(Integer)
    user_id = Column(Integer,ForeignKey(User.id))
    paper_id = Column(Integer,ForeignKey(Paper.id))

def setup():
    engine = create_engine(DATABASE_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind = engine)
    return Session

def drop_all():
    engine = create_engine(DATABASE_URI)
    Base.metadata.drop_all(engine)

def create_user(username,hashed_password,session):
    user = User(username=username,hashed_password=hashed_password)
    session.add(user)
    session.commit()
    
def get_user(username: str,session):
    return session.query(User).filter(User.username == username).first()

def get_rating(session,id):
        rate = 0
        num = 0
        for note in session.query(Rating).filter(Rating.paper_id == id):
            rate += note.value
            num += 1
        if num != 0:
            return rate / num
        else:
            return 0