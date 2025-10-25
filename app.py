from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from collections import OrderedDict
import os
from datetime import datetime
from functools import wraps

# Импорты для работы с БД
from data import db_session
from data.users import User
from data.schedule import Schedule
from data.notes import Note
from data.materials import Material

app = Flask(__name__)
app.secret_key = 'hackathon_secret_key_2025'


def get_schedule_from_db(group_name):
    """Получает расписание группы из БД"""
    db_sess = db_session.create_session()
    
    try:
        schedule_entries = db_sess.query(Schedule).filter(
            Schedule.group_name == group_name
        ).order_by(Schedule.week_number, Schedule.lesson_number).all()
        
        if not schedule_entries:
            return {}
        
        schedule_data = {
            'группа': group_name,
            'group_id': schedule_entries[0].group_id if schedule_entries else None,
            'последнее_обновление': schedule_entries[0].last_updated.strftime('%Y-%m-%d %H:%M:%S') if schedule_entries else None,
            'недели': OrderedDict()
        }
        
        weeks = {}
        for entry in schedule_entries:
            week_num = str(entry.week_number)
            if week_num not in weeks:
                weeks[week_num] = {}
            
            day_name = entry.day_name
            if day_name not in weeks[week_num]:
                weeks[week_num][day_name] = {
                    'дата': entry.date,
                    'пары': []
                }
            
            weeks[week_num][day_name]['пары'].append({
                'номер_пары': entry.lesson_number,
                'время': entry.time_slot,
                'предмет': entry.subject,
                'тип': entry.lesson_type,
                'преподаватель': entry.teacher,
                'аудитория': entry.classroom
            })
        
        for week_num in sorted(weeks.keys(), key=int):
            schedule_data['недели'][week_num] = weeks[week_num]
        
        return schedule_data
        
    finally:
        db_sess.close()


def get_all_groups():
    """Получает список всех групп из БД"""
    db_sess = db_session.create_session()
    try:
        groups = db_sess.query(Schedule.group_name).distinct().all()
        return [group[0] for group in groups]
    finally:
        db_sess.close()


def login_required_custom(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== МАРШРУТЫ ====================

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
        if session.get('role') == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('login')
        password = request.form.get('password')
        
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.username == username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.full_name
            session['role'] = user.role
            
            if user.is_student():
                session['group'] = user.group_name
                db_sess.close()
                return redirect(url_for('student_dashboard'))
            else:
                session['subject'] = user.subject
                db_sess.close()
                return redirect(url_for('teacher_dashboard'))
        
        db_sess.close()
        return render_template('login.html', error='Неверный логин или пароль')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        
        group_name = request.form.get('group_name') if role == 'student' else None
        subject = request.form.get('subject') if role == 'teacher' else None
        
        db_sess = db_session.create_session()
        
        existing_user = db_sess.query(User).filter(User.username == username).first()
        if existing_user:
            db_sess.close()
            return render_template('register.html', 
                                 error='Пользователь с таким логином уже существует',
                                 groups=get_all_groups())
        
        new_user = User(
            username=username,
            full_name=full_name,
            role=role,
            group_name=group_name,
            subject=subject
        )
        new_user.set_password(password)
        
        db_sess.add(new_user)
        db_sess.commit()
        
        session['user_id'] = new_user.id
        session['username'] = new_user.full_name
        session['role'] = new_user.role
        
        if new_user.is_student():
            session['group'] = new_user.group_name
        else:
            session['subject'] = new_user.subject
        
        db_sess.close()
        
        if role == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('teacher_dashboard'))
    
    return render_template('register.html', groups=get_all_groups())

@app.route('/profile')
@login_required_custom
def profile():
    """Универсальный профиль - редирект на нужный"""
    if session.get('role') == 'student':
        return redirect(url_for('student_profile'))
    else:
        return redirect(url_for('teacher_profile'))

@app.route('/logout')
def logout():
    """Выход"""
    session.clear()
    return redirect(url_for('login'))


# ==================== СТУДЕНТ ====================

@app.route('/student/dashboard')
@login_required_custom
def student_dashboard():
    """Главная страница студента"""
    if session.get('role') != 'student':
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('student_dashboard.html')


# ==================== РАСПИСАНИЕ (ДЛЯ ВСЕХ) ====================

@app.route('/schedule')
@login_required_custom
def schedule():
    """Универсальная страница расписания для всех"""
    
    # Получаем все группы
    groups_list = get_all_groups()
    
    # Определяем какую группу показать
    if session.get('role') == 'student':
        # Для студента - его группа по умолчанию
        current_group = session.get('group', groups_list[0] if groups_list else None)
    else:
        # Для преподавателя - первая группа или выбранная
        current_group = request.args.get('group', groups_list[0] if groups_list else None)
    
    # Получаем расписание
    schedule_data = {}
    if current_group:
        schedule_data = get_schedule_from_db(current_group)
    
    return render_template('schedule.html',
                         schedule=schedule_data,
                         groups=groups_list,
                         current_group=current_group)


# Редиректы для обратной совместимости
@app.route('/student/schedule')
@login_required_custom
def student_schedule():
    """Редирект на общее расписание"""
    return redirect(url_for('schedule'))


@app.route('/teacher/schedule')
@login_required_custom
def teacher_schedule():
    """Редирект на общее расписание"""
    return redirect(url_for('schedule'))


@app.route('/student/materials')
@login_required_custom
def student_materials():
    """Страница материалов для студента"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    current_group = session.get('group')
    db_sess = db_session.create_session()
    
    # Получаем материалы для группы студента
    materials = db_sess.query(Material).filter(
        Material.group_name == current_group
    ).order_by(Material.upload_date.desc()).all()
    
    # Получаем список уникальных предметов для фильтра
    subjects = db_sess.query(Material.subject).filter(
        Material.group_name == current_group
    ).distinct().all()
    subjects = [s[0] for s in subjects]
    
    db_sess.close()
    
    return render_template('materials.html', 
                         materials=materials,
                         subjects=subjects)


@app.route('/student/profile')
@login_required_custom
def student_profile():
    """Профиль студента"""
    if session.get('role') != 'student':
        return redirect(url_for('teacher_profile'))
    
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(session['user_id'])
    db_sess.close()
    
    return render_template('profile.html', user=user)


# ==================== ПРЕПОДАВАТЕЛЬ ====================

@app.route('/teacher/dashboard')
@login_required_custom
def teacher_dashboard():
    """Главная страница преподавателя"""
    if session.get('role') != 'teacher':
        return redirect(url_for('student_dashboard'))
    
    return render_template('teacher_dashboard.html')


@app.route('/teacher/materials')
@login_required_custom
def teacher_materials():
    """Страница материалов для преподавателя"""
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    
    db_sess = db_session.create_session()
    
    # Получаем все материалы
    materials = db_sess.query(Material).order_by(Material.upload_date.desc()).all()
    
    # Получаем список уникальных предметов
    subjects = db_sess.query(Material.subject).distinct().all()
    subjects = [s[0] for s in subjects]
    
    db_sess.close()
    
    return render_template('materials.html', 
                         materials=materials,
                         subjects=subjects)


@app.route('/teacher/profile')
@login_required_custom
def teacher_profile():
    """Профиль преподавателя"""
    if session.get('role') != 'teacher':
        return redirect(url_for('student_profile'))
    
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(session['user_id'])
    db_sess.close()
    
    return render_template('profile.html', user=user)


# ==================== API ====================

@app.route('/api/schedule/<group_name>')
def api_schedule(group_name):
    """API расписания"""
    schedule_data = get_schedule_from_db(group_name)
    return jsonify(schedule_data)


@app.route('/api/schedule/<group_name>/week/<int:week_number>')
def api_week(group_name, week_number):
    """API недели"""
    schedule_data = get_schedule_from_db(group_name)
    week_data = schedule_data.get('недели', {}).get(str(week_number), {})
    return jsonify({
        'группа': group_name,
        'неделя': week_number,
        'расписание': week_data
    })


@app.route('/api/groups')
def api_groups():
    """API групп"""
    groups = get_all_groups()
    return jsonify(groups)


# ==================== API ЗАМЕТОК ====================

@app.route('/api/notes/save', methods=['POST'])
@login_required_custom
def save_note():
    """Сохранить заметку"""
    data = request.get_json()
    
    user_id = session.get('user_id')
    group_name = data.get('group_name')
    week_number = data.get('week_number')
    day_name = data.get('day_name')
    note_text = data.get('note_text', '').strip()[:64]
    
    if not note_text:
        return jsonify({'success': False, 'error': 'Заметка пустая'})
    
    db_sess = db_session.create_session()
    
    note = db_sess.query(Note).filter(
        Note.user_id == user_id,
        Note.group_name == group_name,
        Note.week_number == week_number,
        Note.day_name == day_name
    ).first()
    
    if note:
        note.note_text = note_text
        note.updated_at = datetime.now()
    else:
        note = Note(
            user_id=user_id,
            group_name=group_name,
            week_number=week_number,
            day_name=day_name,
            note_text=note_text
        )
        db_sess.add(note)
    
    db_sess.commit()
    db_sess.close()
    
    return jsonify({'success': True, 'note': note_text})


@app.route('/api/notes/delete', methods=['POST'])
@login_required_custom
def delete_note():
    """Удалить заметку"""
    data = request.get_json()
    
    user_id = session.get('user_id')
    group_name = data.get('group_name')
    week_number = data.get('week_number')
    day_name = data.get('day_name')
    
    db_sess = db_session.create_session()
    
    note = db_sess.query(Note).filter(
        Note.user_id == user_id,
        Note.group_name == group_name,
        Note.week_number == week_number,
        Note.day_name == day_name
    ).first()
    
    if note:
        db_sess.delete(note)
        db_sess.commit()
    
    db_sess.close()
    
    return jsonify({'success': True})


@app.route('/api/notes/all', methods=['POST'])
@login_required_custom
def get_all_notes():
    """Получить все заметки"""
    data = request.get_json()
    
    user_id = session.get('user_id')
    group_name = data.get('group_name')
    
    db_sess = db_session.create_session()
    
    notes = db_sess.query(Note).filter(
        Note.user_id == user_id,
        Note.group_name == group_name
    ).all()
    
    notes_dict = {}
    for note in notes:
        key = f"{note.week_number}_{note.day_name}"
        notes_dict[key] = note.note_text
    
    db_sess.close()
    
    return jsonify({'success': True, 'notes': notes_dict})

# ==================== СКАЧИВАНИЕ ФАЙЛОВ ====================

from flask import send_file, abort
import os

import unicodedata

@app.route('/download/material/<int:material_id>')
@login_required_custom
def download_material(material_id):
    """Скачивание файла материала"""
    db_sess = db_session.create_session()
    
    try:
        material = db_sess.query(Material).filter(Material.id == material_id).first()
        
        if not material:
            abort(404)
        
        # Для студента проверяем группу
        if session.get('role') == 'student':
            if material.group_name != session.get('group'):
                abort(403)
        
        # Извлекаем имя файла из пути
        target_filename = os.path.basename(material.file_path)
        materials_dir = os.path.join('static', 'materials')
        
        print(f"🔍 Ищем файл: {target_filename}")
        
        # Нормализуем имя файла из БД
        target_normalized = unicodedata.normalize('NFC', target_filename)
        
        # Ищем файл в папке с нормализацией
        for filename in os.listdir(materials_dir):
            filename_normalized = unicodedata.normalize('NFC', filename)
            
            if filename_normalized == target_normalized:
                print(f"✅ Файл найден: {filename}")
                full_path = os.path.join(materials_dir, filename)
                
                return send_file(
                    full_path,
                    as_attachment=True,
                    download_name=filename
                )
        
        print(f"❌ Файл не найден в папке")
        abort(404)
        
    finally:
        db_sess.close()
# ==================== ОБРАБОТЧИКИ ОШИБОК ====================

@app.errorhandler(404)
def page_not_found(e):
    """Страница 404 - не найдено"""
    return render_template('404.html'), 404


if __name__ == '__main__':
    db_session.global_init('db/university.db')
    
    groups = get_all_groups()
    
    print("\n" + "="*70)
    print("🎓 ЛИЧНЫЙ КАБИНЕТ СТУДЕНТА - ХАКАТОН 2025")
    print("="*70)
    print(f"🌐 Сайт:         http://127.0.0.1:5000/")
    print(f"🔑 Студент:      student1 / password")
    print(f"🔑 Преподаватель: teacher1 / password")
    print(f"📊 Загружено групп из БД: {len(groups)}")
    if groups:
        print(f"📋 Группы: {', '.join(groups)}")
    else:
        print("⚠️  Групп нет! Запустите: python parser.py")
    print("="*70 + "\n")
    
    app.run(debug=True, use_reloader=False)