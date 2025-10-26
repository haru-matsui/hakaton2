"""
Скрипт для инициализации базы данных университета
"""
import os
from data import db_session
from data.users import User
from data.schedule import Schedule
from data.notes import Note
from data.materials import Material


def create_database():
    """Создаёт базу данных и таблицы"""

    if not os.path.exists('db'):
        os.makedirs('db')
        print("📁 Создана папка db/")

    db_file = 'db/university.db'
    db_session.global_init(db_file)
    print(f"✅ База данных инициализирована: {db_file}")
    print("\n" + "=" * 70)
    print("✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА!")
    print("📊 База данных готова к использованию")
    print("=" * 70)


if __name__ == '__main__':
    create_database()
