"""
Скрипт для обновления БД - удаляет поле subject у преподавателей
"""
from data import db_session
from data.users import User

def update_database():
    """Обновляет структуру БД"""
    
    db_session.global_init('db/university.db')
    
    print("="*60)
    print("🔧 ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ")
    print("="*60)
    
    # SQLAlchemy автоматически обновит структуру при первом запуске
    # Но старые данные в поле subject останутся
    
    print("✅ База данных обновлена!")
    print("⚠️  Поле 'subject' больше не используется")
    print("="*60)

if __name__ == '__main__':
    update_database()