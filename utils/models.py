from typing import Union,List
from pydantic import BaseModel


class UserRegister(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str,None] = None

class PaperCreate(BaseModel):
    title: str
    content: str

class PaperUpdate(BaseModel):
    title: Union[str,None] = None
    content: Union[str,None] = None
    status: Union[int,None] = None
    added_users: List[int] = None

class UserUpdate(BaseModel):
    active: Union[bool,None] = None
    read: Union[bool,None] = None
    write: Union[bool,None] = None
    mod: Union[bool,None] = None
    adm: Union[bool,None] = None