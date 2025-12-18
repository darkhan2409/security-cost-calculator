"""
Менеджер товарно-материальных ценностей с интерактивным интерфейсом
"""

from database import TMCDatabase, print_item, print_all_items, print_summary
from typing import List, Dict, Any


def add_item_interactive(db: TMCDatabase):
    """Интерактивное добавление товара."""
    print("\n" + "=" * 80)
    print("➕ ДОБАВЛЕНИЕ НОВОГО ТОВАРА")
    print("=" * 80)
    
    try:
        name = input("Название товара: ").strip()
        if not name:
            print("❌ Название не может быть пустым")
            return
        
        price = float(input("Цена за единицу (₸): ").strip().replace(',', '').replace(' ', ''))
        quantity = int(input("Количество (шт): ").strip())
        amortization = int(input("Срок амортизации (месяцев): ").strip())
        
        item_id = db.add_item(name, price, quantity, amortization)
        
        print(f"\n✅ Товар добавлен с ID: {item_id}")
        
        # Показываем добавленный товар
        item = db.get_item(item_id)
        if item:
            print_item(item)
            
    except ValueError as e:
        print(f"❌ Ошибка: {e}")


def update_item_interactive(db: TMCDatabase):
    """Интерактивное обновление товара."""
    print("\n" + "=" * 80)
    print("✏️ ОБНОВЛЕНИЕ ТОВАРА")
    print("=" * 80)
    
    try:
        item_id = int(input("ID товара для обновления: ").strip())
        
        item = db.get_item(item_id)
        if not item:
            print(f"❌ Товар с ID {item_id} не найден")
            return
        
        print("\nТекущие данные:")
        print_item(item)
        
        print("\nВведите новые значения (Enter = оставить без изменений):")
        
        name_input = input(f"Название [{item['name']}]: ").strip()
        name = name_input if name_input else None
        
        price_input = input(f"Цена [{item['price']:,.2f} ₸]: ").strip()
        price = float(price_input.replace(',', '').replace(' ', '')) if price_input else None
        
        quantity_input = input(f"Количество [{item['quantity']} шт]: ").strip()
        quantity = int(quantity_input) if quantity_input else None
        
        amortization_input = input(f"Срок амортизации [{item['amortization_months']} мес]: ").strip()
        amortization = int(amortization_input) if amortization_input else None
        
        if db.update_item(item_id, name, price, quantity, amortization):
            print("\n✅ Товар обновлен")
            updated_item = db.get_item(item_id)
            if updated_item:
                print_item(updated_item)
        else:
            print("❌ Не удалось обновить товар")
            
    except ValueError as e:
        print(f"❌ Ошибка: {e}")


def delete_item_interactive(db: TMCDatabase):
    """Интерактивное удаление товара."""
    print("\n" + "=" * 80)
    print("🗑️ УДАЛЕНИЕ ТОВАРА")
    print("=" * 80)
    
    try:
        item_id = int(input("ID товара для удаления: ").strip())
        
        item = db.get_item(item_id)
        if not item:
            print(f"❌ Товар с ID {item_id} не найден")
            return
        
        print("\nВы собираетесь удалить:")
        print_item(item)
        
        confirm = input("\nПодтвердите удаление (yes/y): ").strip().lower()
        if confirm in ['yes', 'y', 'да', 'д']:
            if db.delete_item(item_id):
                print("✅ Товар удален")
            else:
                print("❌ Не удалось удалить товар")
        else:
            print("❌ Удаление отменено")
            
    except ValueError as e:
        print(f"❌ Ошибка: {e}")


def select_items_for_calculation(db: TMCDatabase) -> List[Dict[str, Any]]:
    """
    Выбор товаров для расчета стоимости охраны.
    
    Returns:
        Список выбранных товаров
    """
    items = db.get_all_items()
    
    if not items:
        print("\n❌ База данных пуста. Сначала добавьте товары.")
        return []
    
    print("\n" + "=" * 80)
    print("📦 ВЫБОР ТМЦ ДЛЯ РАСЧЕТА")
    print("=" * 80)
    print("\nДоступные товары:")
    print_all_items(items)
    
    print("\nВведите ID товаров через запятую (например: 1,3,4)")
    print("Или нажмите Enter, чтобы использовать все товары")
    
    choice = input("\nВаш выбор: ").strip()
    
    if not choice:
        # Используем все товары
        print(f"\n✅ Выбраны все товары ({len(items)} шт.)")
        return items
    
    try:
        # Парсим ID
        selected_ids = [int(id.strip()) for id in choice.split(',')]
        
        # Получаем выбранные товары
        selected_items = []
        for item_id in selected_ids:
            item = db.get_item(item_id)
            if item:
                selected_items.append(item)
            else:
                print(f"⚠️ Товар с ID {item_id} не найден, пропускаем")
        
        if selected_items:
            print(f"\n✅ Выбрано товаров: {len(selected_items)}")
            print("\nВыбранные товары:")
            print_all_items(selected_items)
            
            # Показываем общую месячную стоимость
            total_monthly = sum(item['monthly_cost'] for item in selected_items)
            print(f"\n💰 Общая месячная стоимость ТМЦ: {total_monthly:,.2f} ₸")
        
        return selected_items
        
    except ValueError:
        print("❌ Неверный формат ввода")
        return []


def tmc_menu():
    """Главное меню управления ТМЦ."""
    with TMCDatabase() as db:
        while True:
            print("\n" + "=" * 80)
            print("УПРАВЛЕНИЕ ТОВАРНО-МАТЕРИАЛЬНЫМИ ЦЕННОСТЯМИ")
            print("=" * 80)
            print("\n1. Показать все товары")
            print("2. Добавить товар")
            print("3. Обновить товар")
            print("4. Удалить товар")
            print("5. Показать сводку")
            print("6. Выбрать товары для расчета")
            print("q. Выход")
            
            choice = input("\nВаш выбор: ").strip().lower()
            
            if choice == '1':
                items = db.get_all_items()
                print("\n" + "=" * 80)
                print("📦 ВСЕ ТОВАРЫ:")
                print_all_items(items)
                
            elif choice == '2':
                add_item_interactive(db)
                
            elif choice == '3':
                update_item_interactive(db)
                
            elif choice == '4':
                delete_item_interactive(db)
                
            elif choice == '5':
                summary = db.get_summary()
                print_summary(summary)
                
            elif choice == '6':
                selected = select_items_for_calculation(db)
                if selected:
                    input("\nНажмите Enter для продолжения...")
                
            elif choice == 'q':
                print("\n👋 До свидания!")
                break
                
            else:
                print("❌ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    tmc_menu()
