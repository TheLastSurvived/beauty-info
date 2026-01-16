from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
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

# Блог посты
def get_blog_posts(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    only_published: bool = True
):
    query = db.query(models.BlogPost)
    
    if only_published:
        query = query.filter(models.BlogPost.is_published == True)
    
    if category:
        query = query.filter(models.BlogPost.category == category)
    
    if tag:
        query = query.join(models.BlogPost.tags).filter(models.BlogTag.name == tag)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            models.BlogPost.title.ilike(search_term) |
            models.BlogPost.content.ilike(search_term) |
            models.BlogPost.excerpt.ilike(search_term)
        )
    
    return query.order_by(desc(models.BlogPost.created_at)).offset(skip).limit(limit).all()

def get_blog_post(db: Session, post_id: int):
    return db.query(models.BlogPost).filter(models.BlogPost.id == post_id).first()

def get_blog_post_by_slug(db: Session, slug: str):
    return db.query(models.BlogPost).filter(models.BlogPost.slug == slug).first()

def increment_post_views(db: Session, post_id: int):
    post = get_blog_post(db, post_id)
    if post:
        post.views_count += 1
        db.commit()
        db.refresh(post)
    return post

def get_popular_posts(db: Session, limit: int = 5):
    return db.query(models.BlogPost).filter(
        models.BlogPost.is_published == True
    ).order_by(
        desc(models.BlogPost.views_count)
    ).limit(limit).all()

def get_recent_posts(db: Session, limit: int = 5):
    return db.query(models.BlogPost).filter(
        models.BlogPost.is_published == True
    ).order_by(
        desc(models.BlogPost.created_at)
    ).limit(limit).all()

# Категории блога
def get_blog_categories(db: Session):
    return db.query(models.BlogCategory).all()

def get_blog_categories_with_counts(db: Session):
    result = db.query(
        models.BlogPost.category,
        func.count(models.BlogPost.id).label('count')
    ).filter(
        models.BlogPost.is_published == True
    ).group_by(
        models.BlogPost.category
    ).all()
    
    return [{"name": cat[0], "count": cat[1]} for cat in result if cat[0]]

# Теги блога
def get_blog_tags(db: Session):
    return db.query(models.BlogTag).all()

def get_popular_tags(db: Session, limit: int = 10):
    result = db.query(
        models.BlogTag,
        func.count(models.post_tags.c.post_id).label('count')
    ).join(
        models.post_tags
    ).group_by(
        models.BlogTag.id
    ).order_by(
        desc('count')
    ).limit(limit).all()
    
    return result

# Комментарии
def get_post_comments(db: Session, post_id: int, only_approved: bool = True):
    query = db.query(models.BlogComment).filter(
        models.BlogComment.post_id == post_id
    )
    
    if only_approved:
        query = query.filter(models.BlogComment.is_approved == True)
    
    return query.order_by(desc(models.BlogComment.created_at)).all()

def create_comment(db: Session, post_id: int, author_name: str, content: str, author_email: Optional[str] = None):
    comment = models.BlogComment(
        post_id=post_id,
        author_name=author_name,
        author_email=author_email,
        content=content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

def create_blog_category(db: Session, name: str, description: Optional[str] = None):
    from slugify import slugify
    category = models.BlogCategory(
        name=name,
        slug=slugify(name),
        description=description
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

def create_blog_tag(db: Session, name: str):
    from slugify import slugify
    tag = models.BlogTag(
        name=name,
        slug=slugify(name)
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

def create_blog_post(
    db: Session,
    title: str,
    content: str,
    category: str,
    excerpt: Optional[str] = None,
    author: str = "Администратор",
    image_url: Optional[str] = None,
    tags: Optional[List[str]] = None,
    is_published: bool = True
):
    from slugify import slugify
    post = models.BlogPost(
        title=title,
        slug=slugify(title),
        excerpt=excerpt,
        content=content,
        author=author,
        image_url=image_url,
        category=category,
        is_published=is_published
    )
    
    db.add(post)
    db.flush()  # Получаем ID без коммита
    
    # Добавляем теги
    if tags:
        for tag_name in tags:
            tag = db.query(models.BlogTag).filter(models.BlogTag.name == tag_name).first()
            if not tag:
                tag = create_blog_tag(db, tag_name)
            post.tags.append(tag)
    
    db.commit()
    db.refresh(post)
    return post