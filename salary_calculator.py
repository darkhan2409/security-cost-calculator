"""
Калькулятор стоимости охранных услуг для Казахстана 2026
Расчет стоимости постов охраны 24/7 с полной разбивкой затрат
"""

import sys
from typing import Dict, Any, Optional, List
from database import TMCDatabase
from tmc_manager import select_items_for_calculation

# ==================== КОНСТАНТЫ 2026 ====================
MRP = 4325  # Месячный расчетный показатель
MZP = 85000  # Минимальная заработная плата
BASE_DEDUCTION = 30 * MRP  # 129 750 тг/мес

# Ставки работника (удерживаются из зарплаты)
OPV_RATE = 0.10  # 10% - Обязательные пенсионные взносы
VOSMS_RATE = 0.02  # 2% - Взносы на ОСМС (от GROSS)

# Ставки работодателя (сверх зарплаты)
OPVR_RATE = 0.035  # 3.5% - Обязательные профессиональные пенсионные взносы
SO_RATE = 0.05  # 5% - Социальные отчисления
SN_RATE = 0.06  # 6% - Социальный налог
OOSMS_RATE = 0.03  # 3% - Отчисления на ОСМС работодателя (от GROSS)

# Прогрессивная шкала ИПН
IPN_THRESHOLD_ANNUAL_MRP = 8500  # МРП в год
IPN_RATE_LOW = 0.10  # 10% до порога
IPN_RATE_HIGH = 0.15  # 15% свыше порога

# Настройки бинарного поиска
BINARY_SEARCH_TOLERANCE = 1.0  # Точность 1 тенге
BINARY_SEARCH_MULTIPLIER = 2.0  # Множитель для верхней границы

# Константы для охраны
HOURS_PER_MONTH_AVG = 730  # Среднее количество часов в месяце (365*24/12)
HOURS_PER_POST_24_7 = 720  # Часов работы поста в месяц (30*24, среднее)
DEFAULT_STAFF_PER_POST = 3  # Стандартное количество охранников на пост 24/7
DEFAULT_MARKUP_PERCENT = 20.0  # Стандартная наценка


# ==================== РАСЧЕТ ЗАРПЛАТЫ ====================

def ipn_progressive(taxable_income_monthly: float) -> float:
    """
    Расчет ИПН по прогрессивной шкале 2026:
    - До 8500 МРП/год (708 333 тг/мес) → 10%
    - Свыше → 15%
    
    Args:
        taxable_income_monthly: Налогооблагаемый доход в месяц
        
    Returns:
        Сумма ИПН
    """
    if taxable_income_monthly <= 0:
        return 0.0
    
    threshold_monthly = (IPN_THRESHOLD_ANNUAL_MRP * MRP) / 12  # 708 333 тг/мес
    
    if taxable_income_monthly <= threshold_monthly:
        return taxable_income_monthly * IPN_RATE_LOW
    else:
        return (threshold_monthly * IPN_RATE_LOW + 
                (taxable_income_monthly - threshold_monthly) * IPN_RATE_HIGH)


def calculate_gross_from_net(net_salary: float, has_deduction: bool = True) -> float:
    """
    Расчет gross salary от net salary методом бинарного поиска.
    
    Логика:
    1. gross = начисленная зарплата (искомая)
    2. OPV = gross * 10%
    3. VOSMS = gross * 2%
    4. taxable = gross - OPV - VOSMS - BASE_DEDUCTION (если есть вычет)
    5. IPN = ipn_progressive(taxable)
    6. net = gross - OPV - VOSMS - IPN
    
    Args:
        net_salary: Желаемая зарплата на руки
        has_deduction: Применять ли базовый вычет 30 МРП
        
    Returns:
        Начисленная зарплата (gross)
        
    Raises:
        ValueError: Если net_salary <= 0
    """
    if net_salary <= 0:
        raise ValueError("Зарплата на руки должна быть больше нуля")
    
    # Бинарный поиск
    lower = net_salary
    upper = net_salary * BINARY_SEARCH_MULTIPLIER
    
    while upper - lower > BINARY_SEARCH_TOLERANCE:
        gross_estimate = (lower + upper) / 2
        
        # Расчет удержаний
        opv = gross_estimate * OPV_RATE
        vosms = gross_estimate * VOSMS_RATE
        
        if has_deduction:
            taxable = max(0, gross_estimate - opv - vosms - BASE_DEDUCTION)
        else:
            taxable = max(0, gross_estimate - opv - vosms)
        
        ipn = ipn_progressive(taxable)
        calculated_net = gross_estimate - opv - vosms - ipn
        
        if calculated_net < net_salary:
            lower = gross_estimate
        else:
            upper = gross_estimate
    
    return gross_estimate


def full_salary_breakdown(net_salary: float, has_deduction: bool = True) -> Dict[str, Any]:
    """
    Полный расчет с разбивкой всех платежей.
    
    Args:
        net_salary: Желаемая зарплата на руки
        has_deduction: Применять ли базовый вычет 30 МРП
        
    Returns:
        Словарь с полной разбивкой зарплаты и платежей
    """
    gross = calculate_gross_from_net(net_salary, has_deduction)
    
    # Удержания работника
    opv = gross * OPV_RATE
    vosms = gross * VOSMS_RATE
    
    if has_deduction:
        taxable = max(0, gross - opv - vosms - BASE_DEDUCTION)
    else:
        taxable = max(0, gross - opv - vosms)
    
    ipn = ipn_progressive(taxable)
    net_calculated = gross - opv - vosms - ipn
    
    # Платежи работодателя
    so = (gross - opv) * SO_RATE  # СО = 5% от (ЗП - ОПВ)
    oosms = gross * OOSMS_RATE  # ООСМС = 3% от ЗП
    sn = (gross - opv - vosms) * SN_RATE  # СН = 6% от (ЗП - ОПВ - ВОСМС)
    opvr = gross * OPVR_RATE  # ОПВР = 3.5% от ЗП
    
    # Полная стоимость работника для компании
    total_cost = gross + opvr + so + sn + oosms
    
    return {
        'gross_salary': round(gross, 2),
        'employee_deductions': {
            'opv': round(opv, 2),
            'vosms': round(vosms, 2),
            'ipn': round(ipn, 2),
            'total': round(opv + vosms + ipn, 2)
        },
        'net_salary': round(net_calculated, 2),
        'employer_payments': {
            'opvr': round(opvr, 2),
            'so': round(so, 2),
            'sn': round(sn, 2),
            'oosms': round(oosms, 2),
            'total': round(opvr + so + sn + oosms, 2)
        },
        'total_cost': round(total_cost, 2),
        'deduction_applied': has_deduction
    }


# ==================== РАСЧЕТ ОХРАННЫХ УСЛУГ ====================

def calculate_security_post_cost(
    num_posts: int,
    staff_per_post: int,
    net_salary_per_person: float,
    markup_percent: float = DEFAULT_MARKUP_PERCENT,
    additional_costs_per_month: float = 0.0
) -> Dict[str, Any]:
    """
    Расчет стоимости охранных услуг.
    
    Args:
        num_posts: Количество постов
        staff_per_post: Количество человек на 1 пост (обычно 3 для 24/7)
        net_salary_per_person: ЗП на руки на 1 человека
        markup_percent: Наценка (маржа) в %
        additional_costs_per_month: Доп. расходы (форма, оборудование и т.д.)
    
    Returns:
        Словарь с полным расчетом стоимости охраны
        
    Raises:
        ValueError: Если num_posts <= 0 или staff_per_post <= 0
    """
    if num_posts <= 0:
        raise ValueError("Количество постов должно быть больше нуля")
    if staff_per_post <= 0:
        raise ValueError("Количество сотрудников на пост должно быть больше нуля")
    
    # Общее количество сотрудников
    total_staff = num_posts * staff_per_post
    
    # Расчет на 1 сотрудника
    salary_breakdown = full_salary_breakdown(net_salary_per_person, has_deduction=True)
    
    # Умножаем на количество сотрудников
    total_gross = salary_breakdown['gross_salary'] * total_staff
    total_employee_deductions = salary_breakdown['employee_deductions']['total'] * total_staff
    total_net = salary_breakdown['net_salary'] * total_staff
    total_employer_payments = salary_breakdown['employer_payments']['total'] * total_staff
    
    # Итоговые затраты
    total_labor_cost = salary_breakdown['total_cost'] * total_staff
    total_cost_with_additional = total_labor_cost + additional_costs_per_month
    
    # Стоимость с наценкой
    markup_amount = total_cost_with_additional * (markup_percent / 100)
    final_price = total_cost_with_additional + markup_amount
    
    # Стоимость за 1 пост
    price_per_post = final_price / num_posts
    
    # Стоимость за час работы поста
    price_per_hour = price_per_post / HOURS_PER_POST_24_7
    
    return {
        'configuration': {
            'posts': num_posts,
            'staff_per_post': staff_per_post,
            'total_staff': total_staff,
            'net_salary': net_salary_per_person,
            'markup_percent': markup_percent
        },
        'per_employee': {
            'gross_salary': salary_breakdown['gross_salary'],
            'total_cost': salary_breakdown['total_cost'],
            'opv': salary_breakdown['employee_deductions']['opv'],
            'vosms': salary_breakdown['employee_deductions']['vosms'],
            'ipn': salary_breakdown['employee_deductions']['ipn'],
            'so': salary_breakdown['employer_payments']['so'],
            'sn': salary_breakdown['employer_payments']['sn'],
            'oosms': salary_breakdown['employer_payments']['oosms'],
            'opvr': salary_breakdown['employer_payments']['opvr']
        },
        'total_monthly': {
            'gross_salaries': total_gross,
            'employee_deductions': total_employee_deductions,
            'net_salaries': total_net,
            'employer_payments': total_employer_payments,
            'labor_cost': total_labor_cost,
            'additional_costs': additional_costs_per_month,
            'total_cost': total_cost_with_additional,
            'markup': markup_amount,
            'final_price': final_price
        },
        'per_post': {
            'price': price_per_post,
            'price_per_hour': price_per_hour
        }
    }


# ==================== ФОРМАТИРОВАНИЕ ВЫВОДА ====================

def format_security_quote(result: Dict[str, Any]) -> str:
    """Форматирование коммерческого предложения по охране."""
    cfg = result['configuration']
    per = result['per_employee']
    total = result['total_monthly']
    post = result['per_post']
    
    lines = []
    lines.append("=" * 80)
    lines.append("КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ")
    lines.append("Услуги охраны - расчет стоимости")
    lines.append("=" * 80)
    
    lines.append(f"\n📋 КОНФИГУРАЦИЯ:")
    lines.append(f"   Количество постов:              {cfg['posts']}")
    lines.append(f"   График работы:                  24/7")
    lines.append(f"   Сотрудников на пост:            {cfg['staff_per_post']} чел.")
    lines.append(f"   Всего сотрудников:              {cfg['total_staff']} чел.")
    lines.append(f"   ЗП на руки (1 чел.):            {cfg['net_salary']:>12,.0f} ₸")
    
    lines.append(f"\n💼 РАСЧЕТ НА 1 СОТРУДНИКА:")
    lines.append(f"   Начисленная ЗП:                 {per['gross_salary']:>12,.0f} ₸")
    lines.append(f"   │")
    lines.append(f"   ├─ Удержания:")
    lines.append(f"   │  ├─ ОПВ (10%):                {per['opv']:>12,.0f} ₸")
    lines.append(f"   │  ├─ ВОСМС (2%):               {per['vosms']:>12,.0f} ₸")
    lines.append(f"   │  └─ ИПН:                      {per['ipn']:>12,.0f} ₸")
    lines.append(f"   │")
    lines.append(f"   └─ Платежи работодателя:")
    lines.append(f"      ├─ СО (5%):                  {per['so']:>12,.0f} ₸")
    lines.append(f"      ├─ СН (6%):                  {per['sn']:>12,.0f} ₸")
    lines.append(f"      ├─ ООСМС (3%):               {per['oosms']:>12,.0f} ₸")
    lines.append(f"      └─ ОПВР (3.5%):              {per['opvr']:>12,.0f} ₸")
    lines.append(f"   {'-' * 60}")
    lines.append(f"   ПОЛНАЯ СТОИМОСТЬ (1 чел.):      {per['total_cost']:>12,.0f} ₸")
    
    lines.append(f"\n💰 ИТОГО ЗА МЕСЯЦ ({cfg['total_staff']} чел.):")
    lines.append(f"   Фонд оплаты труда:              {total['labor_cost']:>12,.0f} ₸")
    if total['additional_costs'] > 0:
        lines.append(f"   Дополнительные расходы:         {total['additional_costs']:>12,.0f} ₸")
        lines.append(f"   {'-' * 60}")
        lines.append(f"   Себестоимость:                  {total['total_cost']:>12,.0f} ₸")
    lines.append(f"   Наценка ({cfg['markup_percent']:.1f}%):                  {total['markup']:>12,.0f} ₸")
    lines.append(f"   {'=' * 60}")
    lines.append(f"   СТОИМОСТЬ УСЛУГИ:               {total['final_price']:>12,.0f} ₸/мес")
    
    if cfg['posts'] > 1:
        lines.append(f"\n📍 СТОИМОСТЬ 1 ПОСТА:")
        lines.append(f"   За месяц:                       {post['price']:>12,.0f} ₸")
        lines.append(f"   За час работы:                  {post['price_per_hour']:>12,.2f} ₸")
    
    lines.append("\n" + "=" * 80)
    
    return "\n".join(lines)


# ==================== ИНТЕРАКТИВНЫЙ РЕЖИМ ====================

def security_calculator_interactive():
    """Интерактивный режим расчета стоимости охраны."""
    print("=" * 80)
    print("КАЛЬКУЛЯТОР СТОИМОСТИ ОХРАННЫХ УСЛУГ - 2026")
    print("=" * 80)
    print()
    
    try:
        # Ввод данных
        num_posts = int(input("Количество постов: ").strip())
        staff_input = input(f"Сотрудников на 1 пост (default={DEFAULT_STAFF_PER_POST}): ").strip()
        staff_per_post = int(staff_input) if staff_input else DEFAULT_STAFF_PER_POST
        
        net_salary = float(input("ЗП на руки на 1 человека (₸): ").strip().replace(',', '').replace(' ', ''))
        
        markup_input = input(f"Наценка/маржа (%, default={DEFAULT_MARKUP_PERCENT}): ").strip()
        markup = float(markup_input) if markup_input else DEFAULT_MARKUP_PERCENT
        
        # Выбор ТМЦ из базы данных
        additional = 0.0
        
        use_tmc = input("\nИспользовать ТМЦ из базы данных? (y/n, default=n): ").strip().lower()
        if use_tmc in ['y', 'yes', 'да', 'д']:
            with TMCDatabase() as db:
                selected_items = select_items_for_calculation(db)
                if selected_items:
                    tmc_monthly_cost = sum(item['monthly_cost'] for item in selected_items)
                    additional = tmc_monthly_cost
                    print(f"\n✅ Добавлена стоимость ТМЦ: {tmc_monthly_cost:,.2f} ₸/мес")
        else:
            # Дополнительные расходы (если не используем ТМЦ)
            additional_input = input("Доп. расходы в месяц (форма, оборудование, ₸, default=0): ").strip()
            additional = float(additional_input.replace(',', '').replace(' ', '')) if additional_input else 0
        
        print("\n🔄 Расчет...")
        
        # Расчет
        result = calculate_security_post_cost(
            num_posts=num_posts,
            staff_per_post=staff_per_post,
            net_salary_per_person=net_salary,
            markup_percent=markup,
            additional_costs_per_month=additional
        )
        
        # Вывод
        output = format_security_quote(result)
        print("\n" + output)
        
        # Сохранить?
        save = input("\nСохранить расчет в файл? (y/n): ").strip().lower()
        if save == 'y':
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


def main_menu():
    """Главное меню программы."""
    while True:
        print("\n" + "=" * 80)
        print("КАЛЬКУЛЯТОР СТОИМОСТИ ОХРАННЫХ УСЛУГ - КАЗАХСТАН 2026")
        print("=" * 80)
        print("\n1. Расчет стоимости охраны")
        print("2. Управление ТМЦ (товарно-материальные ценности)")
        print("q. Выход")
        
        choice = input("\nВаш выбор: ").strip().lower()
        
        if choice == '1':
            security_calculator_interactive()
        elif choice == '2':
            from tmc_manager import tmc_menu
            tmc_menu()
        elif choice == 'q':
            print("\n👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    main_menu()
