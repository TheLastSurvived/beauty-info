from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Salon(Base):
    __tablename__ = "salons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), index=True)
    category = Column(String(100))
    description = Column(Text)
    address = Column(String(300))
    district = Column(String(100))
    phone = Column(String(20))
    working_hours = Column(String(200))
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    image_url = Column(String(300), default="/static/img/default.png")  # Одно фото для салона
    created_at = Column(DateTime, server_default=func.now())
    
    # Связи (только услуги и отзывы)
    services = relationship("Service", back_populates="salon", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="salon", cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"))
    category = Column(String(100))
    name = Column(String(200))
    description = Column(Text)
    price = Column(Integer)
    
    salon = relationship("Salon", back_populates="services")


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"))
    author_name = Column(String(100))
    rating = Column(Integer)
    text = Column(Text)
    tags = Column(String(300))
    created_at = Column(DateTime, server_default=func.now())
    
    salon = relationship("Salon", back_populates="reviews")