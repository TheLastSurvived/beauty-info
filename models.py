from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime


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

post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('blog_posts.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('blog_tags.id', ondelete='CASCADE'), primary_key=True)
)

class BlogPost(Base):
    __tablename__ = "blog_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True)
    excerpt = Column(String(500))
    content = Column(Text, nullable=False)
    author = Column(String(100), default="Администратор")
    image_url = Column(String(300), default="/static/img/default.png")
    category = Column(String(50))
    is_published = Column(Boolean, default=True)
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    comments = relationship("BlogComment", back_populates="post", cascade="all, delete-orphan")
    tags = relationship("BlogTag", secondary=post_tags, back_populates="posts")

class BlogCategory(Base):
    __tablename__ = "blog_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, index=True)
    description = Column(String(200))
    
    # Убрали связь posts, т.к. у нас category хранится в BlogPost как строковое поле

class BlogTag(Base):
    __tablename__ = "blog_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(30), unique=True, nullable=False)
    slug = Column(String(30), unique=True, index=True)
    
    posts = relationship("BlogPost", secondary=post_tags, back_populates="tags")

class BlogComment(Base):
    __tablename__ = "blog_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("blog_posts.id", ondelete='CASCADE'))
    author_name = Column(String(100), nullable=False)
    author_email = Column(String(100))
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    post = relationship("BlogPost", back_populates="comments")