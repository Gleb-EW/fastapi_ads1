from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

app = FastAPI()

# --- Конфигурация для JWT ---
SECRET_KEY = "mysecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 48
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Модели ---
class Advertisement(BaseModel):
    id: int
    title: str
    description: str
    price: float
    author: str
    created_at: datetime

class User(BaseModel):
    id: int
    username: str
    password: str
    group: str  # user или admin

class LoginRequest(BaseModel):
    username: str
    password: str

# --- Хранилища ---
ads: List[Advertisement] = []
users: List[User] = []

# --- Вспомогательные функции ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user(authorization: str = Header(None)):
    if not authorization:
        return None
    try:
        token_type, token = authorization.split()
        if token_type.lower() != "bearer":
            return None
    except:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    for user in users:
        if user.username == payload.get("sub"):
            return user
    return None

# --- Роуты для объявлений ---
@app.post("/advertisement")
def create_ad(ad: Advertisement, current_user: User = Depends(get_current_user)):
    if current_user is None or (current_user.group != "admin" and current_user.id != ad.id):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    for existing in ads:
        if existing.id == ad.id:
            raise HTTPException(status_code=400, detail="ID уже существует")
    ads.append(ad)
    return ad

@app.get("/advertisement/{ad_id}")
def get_ad(ad_id: int):
    for ad in ads:
        if ad.id == ad_id:
            return ad
    raise HTTPException(status_code=404, detail="Объявление не найдено")

@app.patch("/advertisement/{ad_id}")
def update_ad(ad_id: int, title: Optional[str] = None, description: Optional[str] = None,
              price: Optional[float] = None, author: Optional[str] = None, current_user: User = Depends(get_current_user)):
    for ad in ads:
        if ad.id == ad_id:
            if current_user is None:
                raise HTTPException(status_code=403, detail="Требуется авторизация")
            if current_user.group != "admin" and current_user.username != ad.author:
                raise HTTPException(status_code=403, detail="Недостаточно прав")
            if title: ad.title = title
            if description: ad.description = description
            if price: ad.price = price
            if author: ad.author = author
            return ad
    raise HTTPException(status_code=404, detail="Объявление не найдено")

@app.delete("/advertisement/{ad_id}")
def delete_ad(ad_id: int, current_user: User = Depends(get_current_user)):
    for ad in ads:
        if ad.id == ad_id:
            if current_user is None:
                raise HTTPException(status_code=403, detail="Требуется авторизация")
            if current_user.group != "admin" and current_user.username != ad.author:
                raise HTTPException(status_code=403, detail="Недостаточно прав")
            ads.remove(ad)
            return {"detail": "Объявление удалено"}
    raise HTTPException(status_code=404, detail="Объявление не найдено")

@app.get("/advertisement")
def search_ads(title: Optional[str] = None, author: Optional[str] = None, min_price: Optional[float] = None,
               max_price: Optional[float] = None):
    results = ads
    if title:
        results = [ad for ad in results if title.lower() in ad.title.lower()]
    if author:
        results = [ad for ad in results if author.lower() in ad.author.lower()]
    if min_price:
        results = [ad for ad in results if ad.price >= min_price]
    if max_price:
        results = [ad for ad in results if ad.price <= max_price]
    return results

# --- Роут для логина ---
@app.post("/login")
def login(req: LoginRequest):
    for user in users:
        if user.username == req.username and verify_password(req.password, user.password):
            token = create_access_token({"sub": user.username, "group": user.group, "user_id": user.id})
            return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Неверный логин или пароль")

# --- Роуты пользователей ---
@app.post("/user")
def create_user(user: User):
    user.password = hash_password(user.password)
    users.append(user)
    return user

@app.get("/user/{user_id}")
def get_user(user_id: int):
    for user in users:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="Пользователь не найден")

@app.patch("/user/{user_id}")
def update_user(user_id: int, username: Optional[str] = None, password: Optional[str] = None,
                group: Optional[str] = None, current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=403, detail="Требуется авторизация")
    for user in users:
        if user.id == user_id:
            if current_user.group != "admin" and current_user.id != user.id:
                raise HTTPException(status_code=403, detail="Недостаточно прав")
            if username: user.username = username
            if password: user.password = hash_password(password)
            if group and current_user.group == "admin":
                user.group = group
            return user
    raise HTTPException(status_code=404, detail="Пользователь не найден")

@app.delete("/user/{user_id}")
def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    for user in users:
        if user.id == user_id:
            if current_user is None or (current_user.group != "admin" and current_user.id != user.id):
                raise HTTPException(status_code=403, detail="Недостаточно прав")
            users.remove(user)
            return {"detail": "Пользователь удалён"}
    raise HTTPException(status_code=404, detail="Пользователь не найден")
