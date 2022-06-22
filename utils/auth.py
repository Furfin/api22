from base64 import encode
from datetime import datetime, timedelta
from typing import Union
from passlib.context import CryptContext
from db import *
from jose import jwt, JWTError


pwd_context = CryptContext(schemes = ['bcrypt'], deprecated = 'auto')

def get_hashed_password(password):
    return pwd_context.hash(password)

def verify_password(password,hashed_password):
    return pwd_context.verify(password,hashed_password)
    
def authenticate_user(session,username,password):
    user = get_user(username,session)
    if not user:
        return False
    if user.active == False:
        return False
    if not verify_password(password,user.hashed_password):
        return False
    return user

def create_access_token(secret_key: str, algo: str,data: dict,expires_delta: Union[timedelta,None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode,secret_key,algorithm=algo)
    return encoded_jwt


