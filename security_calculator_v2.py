"""
Калькулятор стоимости охранных услуг для Казахстана 2026 - Версия 2
Поддержка множественных постов с разными графиками и должностями
"""

import sys
import math
from typing import Dict, Any, List, Tuple
from database import TMCDatabase, print_all_items

# Импортируем функции расчета зарплаты
from salary_calculator import full_salary_breakdown

# Константы
DEFAULT_MARKUP_PERCENT = 20.0


def calculate_monthly_hours(hours_per_day: int, days_per_week: int) -> int:
    """
    Расчет количества часов в месяц по формуле:
    ОКРУГЛВВЕРХ(((30.4/7) * часы_в_день * рабочих_дней_в_неделю); 0)
    
    Args:
        hours_per_day: Часов в день (8, 12, 24 и т.д.)
        days_per_week: Рабочих дней в неделю (5, 7 и т.д.)
        
    Returns:
        Количество часов в месяц
    """
    hours = (30.4 / 7) * hours_per_day * days_per_week
    return math.ceil(hours)


class SecurityPost:
    """Класс для представления одного поста охраны."""
    
    def __init__(self, post_number: int, hours_per_day: int, days_per_week: int):
        """
        Инициализация поста.
        
        Args:
            post_number: Номер поста
            hours_per_day: Часов работы в день
            days_per_week: Рабочих дней в неделю
        """
        self.post_number = post_number
        self.hours_per_day = hours_per_day
        self.days_per_week = days_per_week
        self.monthly_hours = calculate_monthly_hours(hours_per_day, days_per_week)
        self.staff: List[Dict[str, Any]] = []
    
    def add_staff(self, position: str, count: int, net_salary: float):
        """
        Добавление сотрудников на пост.
        
        Args:
            position: Должность
            count: Количество человек
            net_salary: ЗП на руки
        """
        self.staff.append({
            'position': position,
            'count': count,
            'net_salary': net_salary
        })
    
    def calculate_cost(self) -> Dict[str, Any]:
        """Расчет стоимости поста."""
        total_labor_cost = 0
        staff_details = []
        
        for staff_group in self.staff:
            # Расчет на одного сотрудника
            salary_breakdown = full_salary_breakdown(staff_group['net_salary'], has_deduction=True)
            
            # Умножаем на количество
            group_cost = salary_breakdown['total_cost'] * staff_group['count']
            total_labor_cost += group_cost
            
            staff_details.append({
                'position': staff_group['position'],
                'count': staff_group['count'],
                'net_salary': staff_group['net_salary'],
                'gross_salary': salary_breakdown['gross_salary'],
                'total_cost_per_person': salary_breakdown['total_cost'],
                'total_cost_group': group_cost
            })
        
        return {
            'post_number': self.post_number,
            'schedule': f"{self.hours_per_day}/{self.days_per_week}",
            'monthly_hours': self.monthly_hours,
            'staff_details': staff_details,
            'total_labor_cost': total_labor_cost
        }


class SecurityCalculator:
    """Главный калькулятор стоимости охраны."""
    
    def __init__(self):
        self.posts: List[SecurityPost] = []
        self.tmc_items: List[Tuple[Dict[str, Any], int]] = []  # (item, quantity)
        self.markup_percent = DEFAULT_MARKUP_PERCENT
    
    def add_post(self, post: SecurityPost):
        """Добавление поста."""
        self.posts.append(post)
    
    def add_tmc_item(self, item: Dict[str, Any], quantity: int):
        """Добавление ТМЦ с количеством."""
        self.tmc_items.append((item, quantity))
    
    def calculate_total(self) -> Dict[str, Any]:
        """Полный расчет стоимости охраны."""
        # Расчет по постам
        posts_data = []
        total_labor_cost = 0
        total_monthly_hours = 0
        
        for post in self.posts:
            post_data = post.calculate_cost()
            posts_data.append(post_data)
            total_labor_cost += post_data['total_labor_cost']
            total_monthly_hours += post_data['monthly_hours']
        
        # Расчет ТМЦ
        tmc_data = []
        total_tmc_cost = 0
        
        for item, quantity in self.tmc_items:
            item_monthly_cost = item['monthly_cost'] * quantity
            total_tmc_cost += item_monthly_cost
            
            tmc_data.append({
                'name': item['name'],
                'price': item['price'],
                'quantity': quantity,
                'total_cost': item['price'] * quantity,
                'amortization_months': item['amortization_months'],
                'monthly_cost': item_monthly_cost
            })
        
        # Итоговая стоимость
        total_cost = total_labor_cost + total_tmc_cost
        markup_amount = total_cost * (self.markup_percent / 100)
        final_price = total_cost + markup_amount
        
        # Тариф за час
        hourly_rate = final_price / total_monthly_hours if total_monthly_hours > 0 else 0
        
        return {
            'posts': posts_data,
            'tmc': tmc_data,
            'summary': {
                'total_posts': len(self.posts),
                'total_monthly_hours': total_monthly_hours,
                'total_labor_cost': total_labor_cost,
                'total_tmc_cost': total_tmc_cost,
                'subtotal': total_cost,
                'markup_percent': self.markup_percent,
                'markup_amount': markup_amount,
                'final_price': final_price,
                'hourly_rate': hourly_rate
            }
        }


def format_calculation_output(result: Dict[str, Any]) -> str:
    """Форматирование вывода расчета."""
    lines = []
    lines.append("=" * 100)
    lines.append("КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ - УСЛУГИ ОХРАНЫ")
    lines.append("=" * 100)
    
    # Посты
    lines.append("\n📍 КОНФИГУРАЦИЯ ПОСТОВ:")
    for post_data in result['posts']:
        lines.append(f"\n   Пост №{post_data['post_number']} - График {post_data['schedule']}")
        lines.append(f"   Часов в месяц: {post_data['monthly_hours']} ч")
        lines.append(f"   Персонал:")
        
        for staff in post_data['staff_details']:
            lines.append(f"      • {staff['position']}: {staff['count']} чел. × {staff['net_salary']:,.0f} ₸ = {staff['total_cost_group']:,.0f} ₸/мес")
        
        lines.append(f"   Стоимость поста: {post_data['total_labor_cost']:,.0f} ₸/мес")
    
    # ТМЦ
    if result['tmc']:
        lines.append(f"\n📦 ТОВАРНО-МАТЕРИАЛЬНЫЕ ЦЕННОСТИ:")
        for tmc in result['tmc']:
            lines.append(f"   • {tmc['name']}: {tmc['quantity']} шт × {tmc['price']:,.0f} ₸ = {tmc['total_cost']:,.0f} ₸")
            lines.append(f"     Амортизация {tmc['amortization_months']} мес → {tmc['monthly_cost']:,.0f} ₸/мес")
    
    # Итого
    summary = result['summary']
    lines.append(f"\n{'=' * 100}")
    lines.append("💰 ИТОГОВЫЙ РАСЧЕТ:")
    lines.append(f"{'=' * 100}")
    lines.append(f"   Фонд оплаты труда (ФОТ):                    {summary['total_labor_cost']:>20,.0f} ₸/мес")
    lines.append(f"   ТМЦ (амортизация):                          {summary['total_tmc_cost']:>20,.0f} ₸/мес")
    lines.append(f"   {'-' * 100}")
    lines.append(f"   Себестоимость:                              {summary['subtotal']:>20,.0f} ₸/мес")
    lines.append(f"   Маржа ({summary['markup_percent']:.1f}%):                                  {summary['markup_amount']:>20,.0f} ₸/мес")
    lines.append(f"   {'=' * 100}")
    lines.append(f"   СТОИМОСТЬ УСЛУГИ:                           {summary['final_price']:>20,.0f} ₸/мес")
    lines.append(f"   {'=' * 100}")
    lines.append(f"\n   📊 Всего постов: {summary['total_posts']}")
    lines.append(f"   ⏱️  Всего часов в месяц: {summary['total_monthly_hours']} ч")
    lines.append(f"   💵 Тариф за час: {summary['hourly_rate']:,.2f} ₸/ч")
    lines.append(f"\n{'=' * 100}")
    
    return "\n".join(lines)


def interactive_calculator():
    """Интерактивный режим калькулятора."""
    print("=" * 100)
    print("КАЛЬКУЛЯТОР СТОИМОСТИ ОХРАННЫХ УСЛУГ - КАЗАХСТАН 2026")
    print("=" * 100)
    
    calculator = SecurityCalculator()
    
    try:
        # Количество постов
        num_posts = int(input("\nКоличество постов: ").strip())
        if num_posts <= 0:
            print("❌ Количество постов должно быть больше нуля")
            return
        
        # Настройка каждого поста
        for i in range(1, num_posts + 1):
            print(f"\n{'=' * 100}")
            print(f"НАСТРОЙКА ПОСТА №{i}")
            print(f"{'=' * 100}")
            
            # График работы
            print("\nГрафик работы (например: 12/7, 24/7, 8/5):")
            schedule = input("Введите часы/дни (например 12/7): ").strip()
            hours_per_day, days_per_week = map(int, schedule.split('/'))
            
            post = SecurityPost(i, hours_per_day, days_per_week)
            print(f"✅ График {schedule} = {post.monthly_hours} часов в месяц")
            
            # Персонал
            print(f"\nСколько групп персонала на посту №{i}? (например: дневные и ночные)")
            num_staff_groups = int(input("Количество групп: ").strip())
            
            for j in range(num_staff_groups):
                print(f"\n   Группа {j+1}:")
                position = input("   Должность: ").strip()
                count = int(input("   Количество человек: ").strip())
                net_salary = float(input("   ЗП на руки (₸): ").strip().replace(',', '').replace(' ', ''))
                
                post.add_staff(position, count, net_salary)
                print(f"   ✅ Добавлено: {position} - {count} чел. × {net_salary:,.0f} ₸")
            
            calculator.add_post(post)
        
        # ТМЦ
        print(f"\n{'=' * 100}")
        use_tmc = input("\nИспользовать ТМЦ из базы данных? (y/n): ").strip().lower()
        
        if use_tmc in ['y', 'yes', 'да', 'д']:
            with TMCDatabase() as db:
                items = db.get_all_items()
                
                if not items:
                    print("❌ База данных ТМЦ пуста")
                else:
                    print("\n📦 Доступные ТМЦ:")
                    print_all_items(items)
                    
                    print("\nВыберите ТМЦ (введите ID и количество через запятую, например: 1:2,3:5)")
                    print("Или нажмите Enter для пропуска")
                    tmc_input = input("Ваш выбор: ").strip()
                    
                    if tmc_input:
                        selections = tmc_input.split(',')
                        for selection in selections:
                            try:
                                item_id, quantity = map(int, selection.split(':'))
                                item = db.get_item(item_id)
                                if item:
                                    calculator.add_tmc_item(item, quantity)
                                    print(f"✅ Добавлено: {item['name']} × {quantity} шт")
                                else:
                                    print(f"⚠️ Товар ID {item_id} не найден")
                            except ValueError:
                                print(f"⚠️ Неверный формат: {selection}")
        
        # Маржа
        markup_input = input(f"\nМаржа (%, default={DEFAULT_MARKUP_PERCENT}): ").strip()
        if markup_input:
            calculator.markup_percent = float(markup_input)
        
        # Расчет
        print("\n🔄 Выполняется расчет...")
        result = calculator.calculate_total()
        
        # Вывод
        output = format_calculation_output(result)
        print("\n" + output)
        
        # Сохранение
        save = input("\nСохранить расчет в файл? (y/n): ").strip().lower()
        if save in ['y', 'yes', 'да', 'д']:
            filename = input("Имя файла (без расширения): ").strip() or "security_quote"
            filepath = f"{filename}.txt"
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"✅ Сохранено: {filepath}")
            except IOError as e:
                print(f"❌ Ошибка сохранения: {e}")
    
    except ValueError as e:
        print(f"❌ Ошибка ввода: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


def main_menu():
    """Главное меню."""
    while True:
        print("\n" + "=" * 100)
        print("КАЛЬКУЛЯТОР СТОИМОСТИ ОХРАННЫХ УСЛУГ - КАЗАХСТАН 2026")
        print("=" * 100)
        print("\n1. Расчет стоимости охраны")
        print("2. Управление ТМЦ")
        print("q. Выход")
        
        choice = input("\nВаш выбор: ").strip().lower()
        
        if choice == '1':
            interactive_calculator()
        elif choice == '2':
            from tmc_manager import tmc_menu
            tmc_menu()
        elif choice == 'q':
            print("\n👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")


if __name__ == "__main__":
    main_menu()
