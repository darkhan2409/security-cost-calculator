"""
FastAPI Backend для калькулятора стоимости охранных услуг
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import math

from database import TMCDatabase
from salary_calculator import full_salary_breakdown

app = FastAPI(title="Security Cost Calculator API", version="2.0")

# Модели данных
class StaffGroup(BaseModel):
    position: str = Field(..., description="Должность")
    count: int = Field(..., gt=0, description="Количество человек")
    net_salary: float = Field(..., gt=0, description="ЗП на руки")

class Post(BaseModel):
    post_number: int = Field(..., gt=0, description="Номер поста")
    hours_per_day: int = Field(..., gt=0, le=24, description="Часов в день")
    days_per_week: int = Field(..., gt=0, le=7, description="Дней в неделю")
    staff: List[StaffGroup] = Field(..., description="Персонал")

class TMCItem(BaseModel):
    item_id: int = Field(..., description="ID товара из БД")
    quantity: int = Field(..., gt=0, description="Количество")

class CalculationRequest(BaseModel):
    posts: List[Post] = Field(..., description="Список постов")
    tmc_items: List[TMCItem] = Field(default=[], description="ТМЦ")
    markup_percent: float = Field(default=20.0, ge=0, description="Маржа в %")

class TMCCreateRequest(BaseModel):
    name: str = Field(..., description="Название")
    price: float = Field(..., gt=0, description="Цена")
    quantity: int = Field(..., gt=0, description="Количество")
    amortization_months: int = Field(..., gt=0, description="Срок амортизации")

class TMCUpdateRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    amortization_months: Optional[int] = None


# Вспомогательные функции
def calculate_monthly_hours(hours_per_day: int, days_per_week: int) -> int:
    """Расчет часов в месяц."""
    hours = (30.4 / 7) * hours_per_day * days_per_week
    return math.ceil(hours)


# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница."""
    return FileResponse("static/index.html")


@app.post("/api/calculate")
async def calculate_security_cost(request: CalculationRequest) -> Dict[str, Any]:
    """
    Расчет стоимости охранных услуг.
    """
    try:
        posts_data = []
        total_labor_cost = 0
        total_monthly_hours = 0
        
        # Расчет по постам
        for post in request.posts:
            monthly_hours = calculate_monthly_hours(post.hours_per_day, post.days_per_week)
            
            staff_details = []
            post_labor_cost = 0
            
            for staff_group in post.staff:
                # Расчет на одного сотрудника
                salary_breakdown = full_salary_breakdown(staff_group.net_salary, has_deduction=True)
                
                # Умножаем на количество
                group_cost = salary_breakdown['total_cost'] * staff_group.count
                post_labor_cost += group_cost
                
                staff_details.append({
                    'position': staff_group.position,
                    'count': staff_group.count,
                    'net_salary': staff_group.net_salary,
                    'gross_salary': salary_breakdown['gross_salary'],
                    'total_cost_per_person': salary_breakdown['total_cost'],
                    'total_cost_group': group_cost
                })
            
            posts_data.append({
                'post_number': post.post_number,
                'schedule': f"{post.hours_per_day}/{post.days_per_week}",
                'monthly_hours': monthly_hours,
                'staff_details': staff_details,
                'total_labor_cost': post_labor_cost
            })
            
            total_labor_cost += post_labor_cost
            total_monthly_hours += monthly_hours
        
        # Расчет ТМЦ
        tmc_data = []
        total_tmc_cost = 0
        
        with TMCDatabase() as db:
            for tmc_item in request.tmc_items:
                item = db.get_item(tmc_item.item_id)
                if not item:
                    raise HTTPException(status_code=404, detail=f"ТМЦ с ID {tmc_item.item_id} не найден")
                
                item_monthly_cost = item['monthly_cost'] * tmc_item.quantity
                total_tmc_cost += item_monthly_cost
                
                tmc_data.append({
                    'id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': tmc_item.quantity,
                    'total_cost': item['price'] * tmc_item.quantity,
                    'amortization_months': item['amortization_months'],
                    'monthly_cost': item_monthly_cost
                })
        
        # Итоговая стоимость
        total_cost = total_labor_cost + total_tmc_cost
        markup_amount = total_cost * (request.markup_percent / 100)
        final_price = total_cost + markup_amount
        
        # Тариф за час
        hourly_rate = final_price / total_monthly_hours if total_monthly_hours > 0 else 0
        
        return {
            'posts': posts_data,
            'tmc': tmc_data,
            'summary': {
                'total_posts': len(request.posts),
                'total_monthly_hours': total_monthly_hours,
                'total_labor_cost': round(total_labor_cost, 2),
                'total_tmc_cost': round(total_tmc_cost, 2),
                'subtotal': round(total_cost, 2),
                'markup_percent': request.markup_percent,
                'markup_amount': round(markup_amount, 2),
                'final_price': round(final_price, 2),
                'hourly_rate': round(hourly_rate, 2)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tmc")
async def get_all_tmc() -> List[Dict[str, Any]]:
    """Получить все ТМЦ."""
    with TMCDatabase() as db:
        return db.get_all_items()


@app.get("/api/tmc/{item_id}")
async def get_tmc(item_id: int) -> Dict[str, Any]:
    """Получить ТМЦ по ID."""
    with TMCDatabase() as db:
        item = db.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="ТМЦ не найден")
        return item


@app.post("/api/tmc")
async def create_tmc(request: TMCCreateRequest) -> Dict[str, Any]:
    """Создать новый ТМЦ."""
    try:
        with TMCDatabase() as db:
            item_id = db.add_item(
                request.name,
                request.price,
                request.quantity,
                request.amortization_months
            )
            return db.get_item(item_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/tmc/{item_id}")
async def update_tmc(item_id: int, request: TMCUpdateRequest) -> Dict[str, Any]:
    """Обновить ТМЦ."""
    try:
        with TMCDatabase() as db:
            success = db.update_item(
                item_id,
                request.name,
                request.price,
                request.quantity,
                request.amortization_months
            )
            if not success:
                raise HTTPException(status_code=404, detail="ТМЦ не найден")
            return db.get_item(item_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/tmc/{item_id}")
async def delete_tmc(item_id: int) -> Dict[str, str]:
    """Удалить ТМЦ."""
    with TMCDatabase() as db:
        success = db.delete_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail="ТМЦ не найден")
        return {"message": "ТМЦ удален"}


@app.get("/api/tmc/summary")
async def get_tmc_summary() -> Dict[str, Any]:
    """Получить сводку по ТМЦ."""
    with TMCDatabase() as db:
        return db.get_summary()


# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
