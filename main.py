from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

# Модель объявления
class Advertisement(BaseModel):
    id: int
    title: str
    description: str
    price: float
    author: str
    created_at: datetime

# Хранилище объявлений в памяти
ads: List[Advertisement] = []

# Создание объявления
@app.post("/advertisement")
def create_ad(ad: Advertisement):
    for existing in ads:
        if existing.id == ad.id:
            raise HTTPException(status_code=400, detail="ID уже существует")
    ads.append(ad)
    return ad

# Получение объявления по id
@app.get("/advertisement/{ad_id}")
def get_ad(ad_id: int):
    for ad in ads:
        if ad.id == ad_id:
            return ad
    raise HTTPException(status_code=404, detail="Объявление не найдено")

# Обновление объявления
@app.patch("/advertisement/{ad_id}")
def update_ad(ad_id: int, title: Optional[str] = None, description: Optional[str] = None,
              price: Optional[float] = None, author: Optional[str] = None):
    for ad in ads:
        if ad.id == ad_id:
            if title: ad.title = title
            if description: ad.description = description
            if price: ad.price = price
            if author: ad.author = author
            return ad
    raise HTTPException(status_code=404, detail="Объявление не найдено")

# Удаление объявления
@app.delete("/advertisement/{ad_id}")
def delete_ad(ad_id: int):
    for ad in ads:
        if ad.id == ad_id:
            ads.remove(ad)
            return {"detail": "Объявление удалено"}
    raise HTTPException(status_code=404, detail="Объявление не найдено")

# Поиск объявлений по параметрам
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
