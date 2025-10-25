"""
Миграция БД - добавляет поле uploaded_by_role в таблицу materials
"""
import sqlite3
import os

def migrate_materials():
    """Добавляет поле uploaded_by_role"""
    
    db_path = 'db/university.db'
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена!")
        return
    
    print("\n" + "="*60)
    print("🔧 МИГРАЦИЯ ТАБЛИЦЫ MATERIALS")
    print("="*60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(materials)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"\n📊 Текущие колонки: {column_names}")
        
        # Проверяем есть ли uploaded_by_role
        if 'uploaded_by_role' not in column_names:
            print("\n⚙️  Добавляю колонку uploaded_by_role...")
            
            # Добавляем колонку
            cursor.execute("""
                ALTER TABLE materials 
                ADD COLUMN uploaded_by_role TEXT DEFAULT 'teacher'
            """)
            
            print("✅ Колонка uploaded_by_role добавлена!")
            
            # Обновляем все существующие записи
            cursor.execute("""
                UPDATE materials 
                SET uploaded_by_role = 'teacher' 
                WHERE uploaded_by_role IS NULL
            """)
            
            print("✅ Все существующие материалы помечены как от преподавателя!")
        else:
            print("\n✅ Колонка uploaded_by_role уже существует!")
        
        conn.commit()
        
        # Показываем итоговую структуру
        cursor.execute("PRAGMA table_info(materials)")
        columns = cursor.fetchall()
        
        print("\n📊 Финальная структура таблицы materials:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        print("\n" + "="*60)
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    migrate_materials()