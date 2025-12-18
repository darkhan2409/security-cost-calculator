"""
База данных для учета товарно-материальных ценностей (ТМЦ)
SQLite3 база для хранения оборудования и расчета амортизации
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime


class TMCDatabase:
    """Класс для работы с базой данных ТМЦ."""
    
    def __init__(self, db_path: str = "tmc.db"):
        """
        Инициализация базы данных.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.connection = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Подключение к базе данных."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    
    def _create_tables(self):
        """Создание таблиц в базе данных."""
        cursor = self.connection.cursor()
        
        # Таблица товарно-материальных ценностей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tmc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                total_cost REAL GENERATED ALWAYS AS (price * quantity) STORED,
                amortization_months INTEGER NOT NULL,
                monthly_cost REAL GENERATED ALWAYS AS (price * quantity / amortization_months) STORED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.connection.commit()
    
    def add_item(
        self,
        name: str,
        price: float,
        quantity: int,
        amortization_months: int
    ) -> int:
        """
        Добавление нового товара в базу.
        
        Args:
            name: Название товара
            price: Цена за единицу
            quantity: Количество
            amortization_months: Срок амортизации в месяцах
            
        Returns:
            ID добавленного товара
            
        Raises:
            ValueError: Если параметры некорректны
        """
        if price <= 0:
            raise ValueError("Цена должна быть больше нуля")
        if quantity <= 0:
            raise ValueError("Количество должно быть больше нуля")
        if amortization_months <= 0:
            raise ValueError("Срок амортизации должен быть больше нуля")
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO tmc (name, price, quantity, amortization_months)
            VALUES (?, ?, ?, ?)
        """, (name, price, quantity, amortization_months))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение товара по ID.
        
        Args:
            item_id: ID товара
            
        Returns:
            Словарь с данными товара или None
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM tmc WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Получение всех товаров из базы.
        
        Returns:
            Список словарей с данными товаров
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM tmc ORDER BY id")
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def update_item(
        self,
        item_id: int,
        name: Optional[str] = None,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        amortization_months: Optional[int] = None
    ) -> bool:
        """
        Обновление данных товара.
        
        Args:
            item_id: ID товара
            name: Новое название (опционально)
            price: Новая цена (опционально)
            quantity: Новое количество (опционально)
            amortization_months: Новый срок амортизации (опционально)
            
        Returns:
            True если обновление успешно, False если товар не найден
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if price is not None:
            if price <= 0:
                raise ValueError("Цена должна быть больше нуля")
            updates.append("price = ?")
            params.append(price)
        if quantity is not None:
            if quantity <= 0:
                raise ValueError("Количество должно быть больше нуля")
            updates.append("quantity = ?")
            params.append(quantity)
        if amortization_months is not None:
            if amortization_months <= 0:
                raise ValueError("Срок амортизации должен быть больше нуля")
            updates.append("amortization_months = ?")
            params.append(amortization_months)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(item_id)
        
        cursor = self.connection.cursor()
        query = f"UPDATE tmc SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.connection.commit()
        
        return cursor.rowcount > 0
    
    def delete_item(self, item_id: int) -> bool:
        """
        Удаление товара из базы.
        
        Args:
            item_id: ID товара
            
        Returns:
            True если удаление успешно, False если товар не найден
        """
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM tmc WHERE id = ?", (item_id,))
        self.connection.commit()
        
        return cursor.rowcount > 0
    
    def get_total_monthly_cost(self) -> float:
        """
        Получение общей месячной стоимости всех товаров.
        
        Returns:
            Сумма месячных затрат на амортизацию
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT SUM(monthly_cost) as total FROM tmc")
        result = cursor.fetchone()
        
        return result['total'] if result['total'] else 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение сводной информации по всем товарам.
        
        Returns:
            Словарь со сводной информацией
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_items,
                SUM(quantity) as total_quantity,
                SUM(total_cost) as total_investment,
                SUM(monthly_cost) as total_monthly_cost
            FROM tmc
        """)
        result = cursor.fetchone()
        
        return dict(result) if result else {}
    
    def close(self):
        """Закрытие соединения с базой данных."""
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        """Поддержка context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие при выходе из context manager."""
        self.close()


def print_item(item: Dict[str, Any]):
    """Красивый вывод информации о товаре."""
    print(f"\n{'=' * 80}")
    print(f"ID: {item['id']}")
    print(f"Название: {item['name']}")
    print(f"Цена за единицу: {item['price']:,.2f} ₸")
    print(f"Количество: {item['quantity']} шт.")
    print(f"Общая стоимость: {item['total_cost']:,.2f} ₸")
    print(f"Срок амортизации: {item['amortization_months']} мес.")
    print(f"Стоимость в месяц: {item['monthly_cost']:,.2f} ₸")
    print(f"{'=' * 80}")


def print_all_items(items: List[Dict[str, Any]]):
    """Красивый вывод всех товаров в виде таблицы."""
    if not items:
        print("\n📦 База данных пуста")
        return
    
    print(f"\n{'=' * 120}")
    print(f"{'ID':<5} {'Название':<30} {'Цена':<15} {'Кол-во':<8} {'Стоимость':<15} {'Амортизация':<15} {'В месяц':<15}")
    print(f"{'=' * 120}")
    
    for item in items:
        print(
            f"{item['id']:<5} "
            f"{item['name']:<30} "
            f"{item['price']:>13,.2f} ₸ "
            f"{item['quantity']:>6} шт "
            f"{item['total_cost']:>13,.2f} ₸ "
            f"{item['amortization_months']:>13} мес "
            f"{item['monthly_cost']:>13,.2f} ₸"
        )
    
    print(f"{'=' * 120}")


def print_summary(summary: Dict[str, Any]):
    """Красивый вывод сводной информации."""
    print(f"\n{'=' * 80}")
    print("📊 СВОДНАЯ ИНФОРМАЦИЯ")
    print(f"{'=' * 80}")
    print(f"Всего позиций: {summary.get('total_items', 0)}")
    print(f"Общее количество: {summary.get('total_quantity', 0)} шт.")
    print(f"Общие инвестиции: {summary.get('total_investment', 0):,.2f} ₸")
    print(f"Итого в месяц: {summary.get('total_monthly_cost', 0):,.2f} ₸")
    print(f"{'=' * 80}")


# Пример использования
if __name__ == "__main__":
    # Создаем базу данных
    with TMCDatabase() as db:
        print("=" * 80)
        print("БАЗА ДАННЫХ ТОВАРНО-МАТЕРИАЛЬНЫХ ЦЕННОСТЕЙ")
        print("=" * 80)
        
        # Пример добавления товаров
        print("\n✅ База данных создана: tmc.db")
        print("\nПримеры использования:")
        print("\n# Добавление товара:")
        print('db.add_item("Рация", 50000, 10, 36)')
        print("\n# Получение всех товаров:")
        print("items = db.get_all_items()")
        print("\n# Получение сводки:")
        print("summary = db.get_summary()")
        print("\n# Общая месячная стоимость:")
        print("total = db.get_total_monthly_cost()")
