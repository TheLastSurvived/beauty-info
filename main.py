from fastapi import FastAPI, Request, Form, Depends, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
import crud, models
from database import engine, get_db
import os
import uvicorn
from typing import Optional, List
import math
from datetime import datetime


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BeautyCity")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    # Статистика
    total_salons = db.query(models.Salon).count()
    total_reviews = db.query(models.Review).count()
    total_categories = db.query(models.Salon.category).distinct().count()
    
    # Средний рейтинг
    avg_rating = db.query(func.avg(models.Salon.rating)).scalar() or 0
    average_rating = round(avg_rating, 1)
    
    # Топ салоны по рейтингу (3 лучших)
    top_salons = db.query(models.Salon).order_by(
        models.Salon.rating.desc(),
        models.Salon.reviews_count.desc()
    ).limit(3).all()
    
    # Категории с количеством салонов
    categories = db.query(
        models.Salon.category,
        func.count(models.Salon.id).label('count')
    ).group_by(models.Salon.category).all()
    
    # Преобразуем в удобный формат
    categories_data = []
    for cat in categories:
        if cat[0]:  # Проверяем что категория не пустая
            categories_data.append({
                "name": cat[0],
                "count": cat[1]
            })
    
    # Последние отзывы
    recent_reviews = db.query(models.Review).join(
        models.Salon
    ).order_by(
        models.Review.created_at.desc()
    ).limit(4).all()
    
    # Популярные статьи блога
    blog_posts = db.query(models.BlogPost).filter(
        models.BlogPost.is_published == True
    ).order_by(
        models.BlogPost.views_count.desc()
    ).limit(3).all()
    
    # Районы с количеством салонов
    districts = db.query(
        models.Salon.district,
        func.count(models.Salon.id).label('count')
    ).group_by(models.Salon.district).all()
    
    # Преобразуем в удобный формат
    districts_data = []
    for dist in districts:
        if dist[0]:  # Проверяем что район не пустой
            districts_data.append({
                "name": dist[0],
                "count": dist[1]
            })
    
    # Максимальное количество салонов в районе (для прогресс-бара)
    max_district_count = max([d["count"] for d in districts_data]) if districts_data else 1
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Красота в Гродно - Информационный ресурс о салонах красоты",
        "stats": {
            "total_salons": total_salons,
            "total_reviews": total_reviews,
            "average_rating": average_rating,
            "total_categories": total_categories
        },
        "top_salons": top_salons,
        "categories": categories_data,
        "recent_reviews": recent_reviews,
        "blog_posts": blog_posts,
        "districts": districts_data,
        "max_district_count": max_district_count,
        "now": datetime.now()  # Для вычисления времени отзыва
    })


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "contact.html",
        {
            "request": request,
            "title": "Контакты и информация - Красота в Гродно",
        },
    )


@app.get("/blog", response_class=HTMLResponse)
async def blog(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    # Пагинация
    items_per_page = 6
    skip = (page - 1) * items_per_page

    # Получаем посты
    posts = crud.get_blog_posts(
        db,
        skip=skip,
        limit=items_per_page,
        category=category,
        tag=tag,
        search=search,
        only_published=True,
    )

    # Общее количество постов
    total_items = (
        db.query(models.BlogPost).filter(models.BlogPost.is_published == True).count()
    )

    if category:
        total_items = (
            db.query(models.BlogPost)
            .filter(
                models.BlogPost.is_published == True,
                models.BlogPost.category == category,
            )
            .count()
        )
    elif tag:
        total_items = (
            db.query(func.count(models.BlogPost.id))
            .join(models.BlogPost.tags)
            .filter(models.BlogPost.is_published == True, models.BlogTag.name == tag)
            .scalar()
        )

    total_pages = max(1, math.ceil(total_items / items_per_page))

    # Получаем данные для сайдбара
    categories = crud.get_blog_categories_with_counts(db)
    popular_posts = crud.get_popular_posts(db, limit=2)
    recent_posts = crud.get_recent_posts(db, limit=2)
    popular_tags_result = crud.get_popular_tags(db, limit=10)

    return templates.TemplateResponse(
        "blog.html",
        {
            "request": request,
            "title": "Блог о красоте - Красота в Гродно",
            "posts": posts,
            "categories": categories,
            "popular_posts": popular_posts,
            "recent_posts": recent_posts,
            "popular_tags": [tag[0] for tag in popular_tags_result],
            "current_category": category,
            "current_tag": tag,
            "search_query": search,
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_items,
        },
    )


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str, db: Session = Depends(get_db)):
    post = crud.get_blog_post_by_slug(db, slug)

    if not post:
        return templates.TemplateResponse(
            "404.html", {"request": request, "title": "Пост не найден"}, status_code=404
        )

    # Увеличиваем счетчик просмотров
    crud.increment_post_views(db, post.id)

    # Получаем комментарии
    comments = crud.get_post_comments(db, post.id)

    # Получаем предыдущий и следующий пост
    prev_post = (
        db.query(models.BlogPost)
        .filter(
            models.BlogPost.is_published == True,
            models.BlogPost.created_at > post.created_at,
        )
        .order_by(models.BlogPost.created_at.asc())
        .first()
    )

    next_post = (
        db.query(models.BlogPost)
        .filter(
            models.BlogPost.is_published == True,
            models.BlogPost.created_at < post.created_at,
        )
        .order_by(models.BlogPost.created_at.desc())
        .first()
    )

    # Похожие посты (по категории и тегам)
    similar_posts = []

    # По категории
    category_posts = (
        db.query(models.BlogPost)
        .filter(
            models.BlogPost.is_published == True,
            models.BlogPost.category == post.category,
            models.BlogPost.id != post.id,
        )
        .order_by(models.BlogPost.created_at.desc())
        .limit(3)
        .all()
    )

    similar_posts.extend(category_posts)

    # По тегам (если есть)
    if hasattr(post, "tags") and post.tags:
        tag_ids = [tag.id for tag in post.tags]
        tag_posts = (
            db.query(models.BlogPost)
            .join(models.post_tags)
            .filter(
                models.BlogPost.is_published == True,
                models.BlogPost.id != post.id,
                models.post_tags.c.tag_id.in_(tag_ids),
            )
            .distinct()
            .limit(3)
            .all()
        )

        # Добавляем только новые посты
        existing_ids = [p.id for p in similar_posts]
        for tag_post in tag_posts:
            if tag_post.id not in existing_ids and len(similar_posts) < 6:
                similar_posts.append(tag_post)

    # Если мало постов, добавляем последние
    if len(similar_posts) < 4:
        recent_posts = (
            db.query(models.BlogPost)
            .filter(models.BlogPost.is_published == True, models.BlogPost.id != post.id)
            .order_by(models.BlogPost.created_at.desc())
            .limit(3)
            .all()
        )

        existing_ids = [p.id for p in similar_posts]
        for recent_post in recent_posts:
            if recent_post.id not in existing_ids and len(similar_posts) < 6:
                similar_posts.append(recent_post)

    # Получаем теги поста
    tags = post.tags if hasattr(post, "tags") else []

    return templates.TemplateResponse(
        "blog-post.html",
        {
            "request": request,
            "title": post.title + " - Красота в Гродно",
            "post": post,
            "comments": comments,
            "similar_posts": similar_posts[:4],  # Ограничиваем 3 постами
            "prev_post": prev_post,
            "next_post": next_post,
            "tags": tags,
        },
    )


@app.post("/blog/{slug}/comment")
async def add_comment(
    request: Request,
    slug: str,
    author_name: str = Form(...),
    content: str = Form(...),
    author_email: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    post = crud.get_blog_post_by_slug(db, slug)

    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")

    comment = crud.create_comment(
        db,
        post_id=post.id,
        author_name=author_name,
        content=content,
        author_email=author_email,
    )

    return RedirectResponse(f"/blog/{slug}#comments", status_code=303)


@app.get("/api/blog/search")
async def blog_search(q: str = Query("", min_length=1), db: Session = Depends(get_db)):
    posts = crud.get_blog_posts(db, search=q, limit=5, only_published=True)

    results = []
    for post in posts:
        results.append(
            {
                "id": post.id,
                "title": post.title,
                "excerpt": post.excerpt[:100] if post.excerpt else "",
                "slug": post.slug,
                "category": post.category,
                "image_url": post.image_url,
            }
        )

    return JSONResponse(content={"results": results})


@app.get("/catalog", response_class=HTMLResponse)
async def catalog(
    request: Request,
    category: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    min_rating: Optional[str] = Query(None),
    sort_by: str = Query("popular"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    # Базовый запрос
    query = db.query(models.Salon)

    # Применяем фильтры
    if category:
        query = query.filter(func.lower(models.Salon.category) == func.lower(category))
    if district:
        query = query.filter(func.lower(models.Salon.district) == func.lower(district))

    if min_rating and min_rating != "":
        try:
            rating_value = float(min_rating)
            query = query.filter(models.Salon.rating >= rating_value)
        except ValueError:
            pass

    # Применяем сортировку
    if sort_by == "rating":
        query = query.order_by(models.Salon.rating.desc())
    elif sort_by == "reviews":
        query = query.order_by(models.Salon.reviews_count.desc())
    elif sort_by == "name":
        query = query.order_by(models.Salon.name.asc())
    else:
        query = query.order_by(
            models.Salon.rating.desc(), models.Salon.reviews_count.desc()
        )

    # Пагинация
    items_per_page = 6
    total_items = query.count()
    total_pages = max(1, math.ceil(total_items / items_per_page))

    # Корректируем номер страницы
    page = min(page, total_pages)

    # Получаем элементы для текущей страницы
    offset = (page - 1) * items_per_page
    salons = query.offset(offset).limit(items_per_page).all()

    # Получаем уникальные категории и районы для фильтров
    categories = db.query(models.Salon.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]

    districts = db.query(models.Salon.district).distinct().all()
    districts = [dist[0] for dist in districts if dist[0]]

    # Подсчет салонов
    category_counts = {}
    for cat in categories:
        count = (
            db.query(models.Salon)
            .filter(func.lower(models.Salon.category) == func.lower(cat))
            .count()
        )
        category_counts[cat] = count

    district_counts = {}
    for dist in districts:
        count = (
            db.query(models.Salon)
            .filter(func.lower(models.Salon.district) == func.lower(dist))
            .count()
        )
        district_counts[dist] = count

    current_min_rating = min_rating if min_rating else ""

    # В функции catalog(), после получения categories и districts:
    category_counts = {}
    district_counts = {}

    # Подсчет салонов в каждой категории (с учетом всех фильтров кроме текущей категории)
    for cat in categories:
        query = db.query(models.Salon).filter(
            func.lower(models.Salon.category) == func.lower(cat)
        )

        # Применяем фильтр по району, если выбран
        if district:
            query = query.filter(
                func.lower(models.Salon.district) == func.lower(district)
            )

        # Применяем фильтр по рейтингу, если выбран
        if min_rating and min_rating != "":
            try:
                rating_value = float(min_rating)
                query = query.filter(models.Salon.rating >= rating_value)
            except ValueError:
                pass

        category_counts[cat] = query.count()

    # Подсчет салонов в каждом районе (с учетом всех фильтров кроме текущего района)
    for dist in districts:
        query = db.query(models.Salon).filter(
            func.lower(models.Salon.district) == func.lower(dist)
        )

        # Применяем фильтр по категории, если выбран
        if category:
            query = query.filter(
                func.lower(models.Salon.category) == func.lower(category)
            )

        # Применяем фильтр по рейтингу, если выбран
        if min_rating and min_rating != "":
            try:
                rating_value = float(min_rating)
                query = query.filter(models.Salon.rating >= rating_value)
            except ValueError:
                pass

        district_counts[dist] = query.count()

    # Подсчет для "Все категории" (с учетом района и рейтинга)
    all_categories_query = db.query(models.Salon)
    if district:
        all_categories_query = all_categories_query.filter(
            func.lower(models.Salon.district) == func.lower(district)
        )
    if min_rating and min_rating != "":
        try:
            rating_value = float(min_rating)
            all_categories_query = all_categories_query.filter(
                models.Salon.rating >= rating_value
            )
        except ValueError:
            pass
    all_categories_count = all_categories_query.count()

    # Подсчет для "Все районы" (с учетом категории и рейтинга)
    all_districts_query = db.query(models.Salon)
    if category:
        all_districts_query = all_districts_query.filter(
            func.lower(models.Salon.category) == func.lower(category)
        )
    if min_rating and min_rating != "":
        try:
            rating_value = float(min_rating)
            all_districts_query = all_districts_query.filter(
                models.Salon.rating >= rating_value
            )
        except ValueError:
            pass
    all_districts_count = all_districts_query.count()

    return templates.TemplateResponse(
        "catalog.html",
        {
            "request": request,
            "title": "Каталог салонов",
            "salons": salons,
            "categories": categories,
            "districts": districts,
            "all_categories_count": all_categories_count,  # Добавить
            "all_districts_count": all_districts_count,  # Добавить
            "category_counts": category_counts,
            "district_counts": district_counts,
            "current_category": category,
            "current_district": district,
            "current_rating": current_min_rating,
            "current_sort": sort_by,
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_items,
            "items_per_page": items_per_page,
        },
    )


@app.get("/catalog/{salon_id}", response_class=HTMLResponse)
async def salon_detail(
    request: Request,
    salon_id: int,
    db: Session = Depends(get_db)
):
    salon = db.query(models.Salon).filter(models.Salon.id == salon_id).first()
    
    if not salon:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "title": "Салон не найден"
        }, status_code=404)
    
    # Получаем услуги
    services = db.query(models.Service).filter(models.Service.salon_id == salon_id).all()
    
    # Группируем услуги по категориям
    services_by_category = {}
    for service in services:
        if service.category not in services_by_category:
            services_by_category[service.category] = []
        services_by_category[service.category].append(service)
    
    # Получаем отзывы
    reviews = db.query(models.Review).filter(models.Review.salon_id == salon_id).all()
    
    return templates.TemplateResponse("salon-detail.html", {
        "request": request,
        "title": salon.name,
        "salon": salon,
        "services": services,  # Оставляем для обратной совместимости
        "services_by_category": services_by_category,  # Группированные услуги
        "reviews": reviews
    })


@app.post("/catalog/search")
async def catalog_search(
    request: Request,
    search_query: str = Form(""),
    page: int = Form(1),
    db: Session = Depends(get_db),
):
    if search_query:
        # Поиск без учета регистра
        search_term = f"%{search_query}%"
        base_query = db.query(models.Salon).filter(
            or_(
                func.lower(models.Salon.name).like(func.lower(search_term)),
                func.lower(models.Salon.description).like(func.lower(search_term)),
                func.lower(models.Salon.address).like(func.lower(search_term)),
                func.lower(models.Salon.district).like(func.lower(search_term)),
                func.lower(models.Salon.category).like(func.lower(search_term)),
            )
        )

        # Пагинация
        items_per_page = 6
        total_items = base_query.count()
        total_pages = max(1, math.ceil(total_items / items_per_page))

        # Корректируем номер страницы
        page = min(page, total_pages)

        # Получаем элементы для текущей страницы
        offset = (page - 1) * items_per_page
        salons = base_query.offset(offset).limit(items_per_page).all()

        categories = db.query(models.Salon.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]

        districts = db.query(models.Salon.district).distinct().all()
        districts = [dist[0] for dist in districts if dist[0]]

        category_counts = {}
        for cat in categories:
            count = (
                db.query(models.Salon)
                .filter(func.lower(models.Salon.category) == func.lower(cat))
                .count()
            )
            category_counts[cat] = count

        district_counts = {}
        for dist in districts:
            count = (
                db.query(models.Salon)
                .filter(func.lower(models.Salon.district) == func.lower(dist))
                .count()
            )
            district_counts[dist] = count

        return templates.TemplateResponse(
            "catalog.html",
            {
                "request": request,
                "title": f"Результаты поиска: {search_query}",
                "salons": salons,
                "categories": categories,
                "districts": districts,
                "category_counts": category_counts,
                "district_counts": district_counts,
                "search_query": search_query,
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_items,
                "items_per_page": items_per_page,
            },
        )

    return RedirectResponse("/catalog", status_code=303)


# Новый эндпоинт для автодополнения поиска
@app.get("/api/search/autocomplete")
async def search_autocomplete(
    q: str = Query("", min_length=1), db: Session = Depends(get_db)
):
    # Поиск без учета регистра
    search_term = f"%{q}%"

    # Ищем салоны по названию
    salons = (
        db.query(models.Salon)
        .filter(func.lower(models.Salon.name).like(func.lower(search_term)))
        .limit(10)
        .all()
    )

    # Ищем по категориям
    categories = (
        db.query(models.Salon.category)
        .filter(func.lower(models.Salon.category).like(func.lower(search_term)))
        .distinct()
        .limit(5)
        .all()
    )

    # Ищем по районам
    districts = (
        db.query(models.Salon.district)
        .filter(func.lower(models.Salon.district).like(func.lower(search_term)))
        .distinct()
        .limit(5)
        .all()
    )

    # Формируем результаты
    results = []

    # Добавляем салоны
    for salon in salons:
        results.append(
            {
                "type": "salon",
                "id": salon.id,
                "name": salon.name,
                "rating": salon.rating,
                "category": salon.category,
                "icon": "bi-shop",
            }
        )

    # Добавляем категории
    for category in categories:
        if category[0]:
            results.append({"type": "category", "name": category[0], "icon": "bi-tag"})

    # Добавляем районы
    for district in districts:
        if district[0]:
            results.append(
                {"type": "district", "name": district[0], "icon": "bi-geo-alt"}
            )

    return JSONResponse(content={"results": results})


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "title": "Вход - Красота в Гродно",
        },
    )


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "title": "Регистрация - Красота в Гродно",
        },
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
