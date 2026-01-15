from sqlalchemy.orm import Session
from sqlalchemy import or_
import models
from typing import List, Optional

# Салоны
def get_salons(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    category: Optional[str] = None,
    district: Optional[str] = None,
    min_rating: Optional[float] = None
):
    query = db.query(models.Salon)
    
    if category:
        query = query.filter(models.Salon.category == category)
    if district:
        query = query.filter(models.Salon.district == district)
    if min_rating:
        query = query.filter(models.Salon.rating >= min_rating)
    
    return query.order_by(models.Salon.rating.desc()).offset(skip).limit(limit).all()

def get_salon(db: Session, salon_id: int):
    return db.query(models.Salon).filter(models.Salon.id == salon_id).first()

def search_salons(db: Session, query: str, limit: int = 20):
    return db.query(models.Salon).filter(
        or_(
            models.Salon.name.ilike(f"%{query}%"),
            models.Salon.description.ilike(f"%{query}%"),
            models.Salon.address.ilike(f"%{query}%")
        )
    ).limit(limit).all()

# Услуги
def get_services_by_salon(db: Session, salon_id: int):
    return db.query(models.Service).filter(models.Service.salon_id == salon_id).all()

def get_services_by_category(db: Session, salon_id: int, category: str):
    return db.query(models.Service).filter(
        models.Service.salon_id == salon_id,
        models.Service.category == category
    ).all()

# Отзывы
def get_reviews_by_salon(db: Session, salon_id: int, limit: int = 10):
    return db.query(models.Review).filter(
        models.Review.salon_id == salon_id
    ).order_by(models.Review.created_at.desc()).limit(limit).all()

# Изображения
def get_salon_images(db: Session, salon_id: int):
    return db.query(models.SalonImage).filter(
        models.SalonImage.salon_id == salon_id
    ).all()

# Статистика
def get_categories(db: Session):
    result = db.query(models.Salon.category).distinct().all()
    return [cat[0] for cat in result if cat[0]]

def get_districts(db: Session):
    result = db.query(models.Salon.district).distinct().all()
    return [dist[0] for dist in result if dist[0]]