import sqlite3
import os

def migrate_materials():
    db_path = 'db/university.db'
    if not os.path.exists(db_path):
        return
    print("🚀 Миграция...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(materials)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        if 'uploaded_by_role' not in column_names:
            cursor.execute("ALTER TABLE materials ADD COLUMN uploaded_by_role TEXT DEFAULT 'teacher'")
            cursor.execute("UPDATE materials SET uploaded_by_role = 'teacher' WHERE uploaded_by_role IS NULL")
        conn.commit()
    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_materials()