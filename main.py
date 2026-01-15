from fastapi import FastAPI, Request, Form, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
import crud, models
from database import engine, get_db
import os
import uvicorn
from typing import Optional


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BeautyCity")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "BeautyCity - Информационный ресурс о салонах красоты",
    })


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "title": "Контакты и информация - BeautyCity",
})


@app.get("/blog", response_class=HTMLResponse)
async def blog(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("blog.html", {
        "request": request,
        "title": "Блог о красоте - BeautyCity",
})


@app.get("/blog/{post_id}", response_class=HTMLResponse)
async def blog_post(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("blog-post.html", {
        "request": request,
        "title": "Название поста - BeautyCity",
})


@app.get("/catalog", response_class=HTMLResponse)
async def catalog(
    request: Request,
    category: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    min_rating: Optional[str] = Query(None),
    sort_by: str = Query("popular"),
    db: Session = Depends(get_db)
):
    # Базовый запрос
    query = db.query(models.Salon)
    
    # Применяем фильтры
    if category:
        query = query.filter(models.Salon.category == category)
    if district:
        query = query.filter(models.Salon.district == district)
    
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
        query = query.order_by(models.Salon.rating.desc(), models.Salon.reviews_count.desc())
    
    salons = query.all()
    
    # Получаем уникальные категории и районы для фильтров
    categories = db.query(models.Salon.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    districts = db.query(models.Salon.district).distinct().all()
    districts = [dist[0] for dist in districts if dist[0]]
    
    # Подсчет салонов
    category_counts = {}
    for cat in categories:
        count = db.query(models.Salon).filter(models.Salon.category == cat).count()
        category_counts[cat] = count
    
    district_counts = {}
    for dist in districts:
        count = db.query(models.Salon).filter(models.Salon.district == dist).count()
        district_counts[dist] = count
    
    current_min_rating = min_rating if min_rating else ""
    
    return templates.TemplateResponse("catalog.html", {
        "request": request,
        "title": "Каталог салонов",
        "salons": salons,
        "categories": categories,
        "districts": districts,
        "category_counts": category_counts,
        "district_counts": district_counts,
        "current_category": category,
        "current_district": district,
        "current_rating": current_min_rating,
        "current_sort": sort_by
    })


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
        "services_by_category": services_by_category,
        "reviews": reviews
    })


@app.post("/catalog/search")
async def catalog_search(
    request: Request,
    search_query: str = Form(""),
    db: Session = Depends(get_db)
):
    if search_query:
        salons = db.query(models.Salon).filter(
            or_(
                models.Salon.name.ilike(f"%{search_query}%"),
                models.Salon.description.ilike(f"%{search_query}%"),
                models.Salon.address.ilike(f"%{search_query}%")
            )
        ).all()
        
        categories = db.query(models.Salon.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]
        
        districts = db.query(models.Salon.district).distinct().all()
        districts = [dist[0] for dist in districts if dist[0]]
        
        category_counts = {}
        for cat in categories:
            count = db.query(models.Salon).filter(models.Salon.category == cat).count()
            category_counts[cat] = count
        
        district_counts = {}
        for dist in districts:
            count = db.query(models.Salon).filter(models.Salon.district == dist).count()
            district_counts[dist] = count
        
        return templates.TemplateResponse("catalog.html", {
            "request": request,
            "title": f"Результаты поиска: {search_query}",
            "salons": salons,
            "categories": categories,
            "districts": districts,
            "category_counts": category_counts,
            "district_counts": district_counts,
            "search_query": search_query
        })
    
    return RedirectResponse("/catalog?search={search_query}", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "title": "Вход - BeautyCity",
})


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("register.html", {
        "request": request,
        "title": "Регистрация - BeautyCity",
})


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)