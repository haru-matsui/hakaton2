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
    
    create_test_users()
    create_test_materials()
    
    print("\n" + "="*70)
    print("✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА!")
    print("📊 База данных готова к использованию")
    print("="*70)


def create_test_users():
    """Создаёт тестовых пользователей"""
    db_sess = db_session.create_session()
    
    try:
        existing_users = db_sess.query(User).count()
        if existing_users > 0:
            print(f"ℹ️ В БД уже есть {existing_users} пользователей")
            return
        
        student = User(
            username='student1',
            full_name='Иванов Иван Иванович',
            role='student',
            group_name='ТОП-103Б'
        )
        student.set_password('password')
        db_sess.add(student)
        
        teacher = User(
            username='teacher1',
            full_name='Петров Петр Петрович',
            role='teacher',
            subject='Программирование'
        )
        teacher.set_password('password')
        db_sess.add(teacher)
        
        admin = User(
            username='admin',
            full_name='Администратор Системы',
            role='teacher',
            is_admin=True
        )
        admin.set_password('admin123')
        db_sess.add(admin)
        
        db_sess.commit()
        
        print("\n👥 Созданы тестовые пользователи:")
        print("   Студент: student1 / password")
        print("   Преподаватель: teacher1 / password")
        print("   Админ: admin / admin123")
        
    except Exception as e:
        print(f"❌ Ошибка создания пользователей: {e}")
        db_sess.rollback()
    finally:
        db_sess.close()


def create_test_materials():
    """Создаёт тестовые материалы"""
    db_sess = db_session.create_session()
    
    try:
        existing_materials = db_sess.query(Material).count()
        if existing_materials > 0:
            print(f"ℹ️ В БД уже есть {existing_materials} материалов")
            return
        
        materials = [
            Material(
                group_name='ТОП-103Б',
                subject='Программирование',
                title='Введение в Python',
                description='Основы языка программирования Python',
                file_path='/static/materials/python_intro.pdf',
                file_type='Лекция',
                teacher_name='Петров Петр Петрович'
            ),
            Material(
                group_name='ТОП-103Б',
                subject='Программирование',
                title='ООП в Python',
                description='Объектно-ориентированное программирование',
                file_path='/static/materials/python_oop.pptx',
                file_type='Презентация',
                teacher_name='Петров Петр Петрович'
            ),
            Material(
                group_name='ТОП-103Б',
                subject='Математика',
                title='Линейная алгебра',
                description='Матрицы и определители',
                file_path='/static/materials/linear_algebra.pdf',
                file_type='Лекция',
                teacher_name='Сидоров Сидор Сидорович'
            ),
        ]
        
        for material in materials:
            db_sess.add(material)
        
        db_sess.commit()
        
        print(f"\n📚 Создано {len(materials)} тестовых материалов")
        
    except Exception as e:
        print(f"❌ Ошибка создания материалов: {e}")
        db_sess.rollback()
    finally:
        db_sess.close()


if __name__ == '__main__':
    create_database()