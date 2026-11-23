from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import School, User
from .settings import settings

hasher = PasswordHasher()
bearer = HTTPBearer()

def hash_password(raw: str) -> str:
    return hasher.hash(raw)

def verify_password(raw: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, raw)
    except (VerifyMismatchError, VerificationError):
        return False

def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': user.id, 'school_id': user.school_id, 'iat': now,
               'exp': now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm='HS256')

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=['HS256'])
        uid, school_id = payload['sub'], payload['school_id']
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPException(401, 'Token inválido')
    user = db.get(User, uid)
    school = db.get(School, school_id)
    if not user or not user.active or user.school_id != school_id or not school or not school.active:
        raise HTTPException(401, 'Usuário ou escola indisponível')
    return user

def admin_only(user: User = Depends(current_user)) -> User:
    if user.role != 'admin':
        raise HTTPException(403, 'Acesso restrito ao administrador')
    return user
