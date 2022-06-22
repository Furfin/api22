from email.policy import default
from turtle import end_fill
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column,Integer,String,Date,create_engine,ARRAY
from sqlalchemy.orm import sessionmaker

DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/postgres"

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
    users = Column(ARRAY(Integer))


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
