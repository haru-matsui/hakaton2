from data import db_session
from data.materials import Material
from datetime import datetime
import os

def add_materials():
    db_session.global_init('db/university.db')
    db_sess = db_session.create_session()
    try:
        materials_list = [
            {'group_name': 'ТОП-103Б', 'subject': 'Матан', 'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_7.pdf', 'description': 'описание..', 'file_type': 'Лекция', 'teacher_name': 'Кужаев А.Ф.'},
            {'group_name': 'ТОП-103Б', 'subject': 'Матан', 'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_8.pdf', 'description': 'описание..', 'file_type': 'Лекция', 'teacher_name': 'Кужаев А.Ф.'},
            {'group_name': 'ТОП-103Б', 'subject': 'Матан', 'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_9.pdf', 'description': 'описание..', 'file_type': 'Лекция', 'teacher_name': 'Кужаев А.Ф.'},
            {'group_name': 'ТОП-104Б', 'subject': 'Матан', 'file_path': 'static/materials/Математический_анализ_ТОП_ИТ_Лекция_11.pdf', 'description': 'описание..', 'file_type': 'Лекция', 'teacher_name': 'Кужаев А.Ф.'},
        ]
        count_added = 0
        count_skipped = 0
        for mat_data in materials_list:
            file_path = mat_data['file_path']
            existing = db_sess.query(Material).filter(Material.file_path == file_path).first()
            if existing:
                count_skipped += 1
                continue
            filename = os.path.basename(file_path)
            title_from_file = os.path.splitext(filename)[0]
            title_formatted = title_from_file.replace('_', ' ').title()
            material = Material(group_name=mat_data['group_name'], subject=mat_data['subject'], title=title_formatted, description=mat_data.get('description'), file_path=file_path, file_type=mat_data['file_type'], teacher_name=mat_data.get('teacher_name'), upload_date=datetime.now())
            db_sess.add(material)
            count_added += 1
        db_sess.commit()
    except Exception as e:
        import traceback
        traceback.print_exc()
        db_sess.rollback()
    finally:
        db_sess.close()

if __name__ == '__main__':
    add_materials()