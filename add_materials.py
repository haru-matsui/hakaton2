"""
Скрипт для добавления материалов в БД
Автоматически берёт название из имени файла
"""
from data import db_session
from data.materials import Material
from datetime import datetime
import os

def add_materials():
    """Добавляет материалы в базу данных"""
    
    # Инициализируем БД
    db_session.global_init('db/university.db')
    db_sess = db_session.create_session()
    
    try:
        # Список материалов для добавления
        # Название берётся из имени файла автоматически!
        materials_list = [
            {
                'group_name': 'ТОП-103Б',
                'subject': 'Матан',
                'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_7.pdf',
                'description': 'описание..',
                'file_type': 'Лекция',
                'teacher_name': 'Кужаев А.Ф.'
            },
            {
                'group_name': 'ТОП-103Б',
                'subject': 'Матан',
                'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_8.pdf',
                'description': 'описание..',
                'file_type': 'Лекция',
                'teacher_name': 'Кужаев А.Ф.'
            },
            {
                'group_name': 'ТОП-103Б',
                'subject': 'Матан',
                'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_9.pdf',
                'description': 'описание..',
                'file_type': 'Лекция',
                'teacher_name': 'Кужаев А.Ф.'
            },
            {
                'group_name': 'ТОП-104Б',
                'subject': 'Матан',
                'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_11.pdf',
                'description': 'описание..',
                'file_type': 'Лекция',
                'teacher_name': 'Кужаев А.Ф.'
            },
        ]
        
        # Добавляем материалы в БД
        count_added = 0
        count_skipped = 0
        
        for mat_data in materials_list:
            file_path = mat_data['file_path']
            
            # ✅ ПРОВЕРЯЕМ НА ДУБЛИКАТ ПО ПУТИ К ФАЙЛУ
            existing = db_sess.query(Material).filter(
                Material.file_path == file_path
            ).first()
            
            if existing:
                print(f"⏭️  Пропущен (уже есть): {file_path}")
                count_skipped += 1
                continue
            
            # Автоматически извлекаем название из имени файла
            filename = os.path.basename(file_path)
            title_from_file = os.path.splitext(filename)[0]
            title_formatted = title_from_file.replace('_', ' ').title()
            
            # Создаём новый материал
            material = Material(
                group_name=mat_data['group_name'],
                subject=mat_data['subject'],
                title=title_formatted,
                description=mat_data.get('description'),
                file_path=file_path,
                file_type=mat_data['file_type'],
                teacher_name=mat_data.get('teacher_name'),
                upload_date=datetime.now()
            )
            
            db_sess.add(material)
            count_added += 1
            print(f"✅ Добавлен: {title_formatted}")
        
        db_sess.commit()
        
        print(f"\n" + "="*60)
        print(f"✅ Успешно добавлено: {count_added} материалов")
        print(f"⏭️  Пропущено (дубликаты): {count_skipped}")
        print(f"="*60)
        
        # Проверяем что добавилось
        all_materials = db_sess.query(Material).all()
        print(f"\n📊 Всего материалов в БД: {len(all_materials)}")
        
        # Группируем по предметам
        subjects = {}
        for mat in all_materials:
            if mat.subject not in subjects:
                subjects[mat.subject] = 0
            subjects[mat.subject] += 1
        
        print("\n📚 Материалов по предметам:")
        for subject, count in subjects.items():
            print(f"   {subject}: {count}")
        
        # Группируем по группам
        groups = {}
        for mat in all_materials:
            if mat.group_name not in groups:
                groups[mat.group_name] = 0
            groups[mat.group_name] += 1
        
        print("\n👥 Материалов по группам:")
        for group, count in groups.items():
            print(f"   {group}: {count}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        db_sess.rollback()
    finally:
        db_sess.close()


if __name__ == '__main__':
    add_materials()