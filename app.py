from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from collections import OrderedDict
import os
from datetime import datetime
from functools import wraps
import unicodedata

# Импорты для работы с БД
from data import db_session
from data.users import User
from data.schedule import Schedule
from data.notes import Note
from data.materials import Material

# Для загрузки файлов
from flask import send_file, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'hackathon_secret_key_2025'

# Настройки загрузки файлов
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'doc', 'ppt'}
UPLOAD_FOLDER = 'static/materials'


def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


# ==================== ОСНОВНЫЕ СТРАНИЦЫ ====================

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
                # Для преподавателя НЕ добавляем subject в сессию
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
            group_name=group_name
        )
        new_user.set_password(password)
        
        db_sess.add(new_user)
        db_sess.commit()
        
        session['user_id'] = new_user.id
        session['username'] = new_user.full_name
        session['role'] = new_user.role
        
        if new_user.is_student():
            session['group'] = new_user.group_name
        
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
    
    # Получаем сообщения
    success = request.args.get('success')
    error = request.args.get('error')
    
    return render_template('student_materials.html', 
                         materials=materials,
                         subjects=subjects,
                         success=success,
                         error=error)

@app.route('/student/upload_material_page')
@login_required_custom
def student_upload_material_page():
    """Страница загрузки материала для студента"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    db_sess = db_session.create_session()
    
    # Получаем ТОЛЬКО материалы этого студента
    student_name = session.get('username')
    materials = db_sess.query(Material).filter(
        Material.teacher_name == student_name,
        Material.uploaded_by_role == 'student'
    ).order_by(Material.upload_date.desc()).all()
    
    db_sess.close()
    
    # Получаем сообщения
    success = request.args.get('success')
    error = request.args.get('error')
    
    return render_template('student_upload_material.html',
                         materials=materials,
                         success=success,
                         error=error)

@app.route('/student/delete_material/<int:material_id>', methods=['POST'])
@login_required_custom
def student_delete_material(material_id):
    """Удаление материала студентом"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    db_sess = db_session.create_session()
    
    # Получаем материал
    material = db_sess.query(Material).filter(Material.id == material_id).first()
    
    if not material:
        db_sess.close()
        return redirect(url_for('student_upload_material_page') + '?error=Материал не найден')
    
    # Проверяем что это материал этого студента
    if material.teacher_name != session.get('username') or material.uploaded_by_role != 'student':
        db_sess.close()
        return redirect(url_for('student_upload_material_page') + '?error=Вы не можете удалить этот материал')
    
    try:
        # Удаляем файл
        if os.path.exists(material.file_path):
            os.remove(material.file_path)
            print(f"🗑️  Файл удалён: {material.file_path}")
        
        # Удаляем запись из БД
        db_sess.delete(material)
        db_sess.commit()
        
        print(f"✅ Материал удалён: {material.title}")
        
    except Exception as e:
        print(f"❌ Ошибка удаления: {e}")
        db_sess.rollback()
        db_sess.close()
        return redirect(url_for('student_upload_material_page') + f'?error=Ошибка удаления: {str(e)}')
    
    db_sess.close()
    return redirect(url_for('student_upload_material_page') + '?success=Материал успешно удалён')

@app.route('/student/upload_material', methods=['POST'])
@login_required_custom
def student_upload_material():
    """Загрузка материала студентом"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    try:
        # Проверяем что файл загружен
        if 'file' not in request.files:
            return redirect(url_for('student_upload_material_page') + '?error=Файл не выбран')
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(url_for('student_upload_material_page') + '?error=Файл не выбран')
        
        if not allowed_file(file.filename):
            return redirect(url_for('student_upload_material_page') + '?error=Недопустимый формат файла')
        
        # Получаем данные из формы
        title = request.form.get('title')
        subject = request.form.get('subject')
        file_type = request.form.get('file_type')
        description = request.form.get('description', '')
        
        # Группа и ФИО автоматически
        group_name = session.get('group')
        student_name = session.get('username')
        
        # Проверяем обязательные поля
        if not all([title, subject, file_type]):
            return redirect(url_for('student_upload_material_page') + '?error=Заполните все обязательные поля')
        
        # Безопасное имя файла с поддержкой русского
        original_filename = file.filename
        
        safe_chars = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        safe_chars += "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        safe_chars += "0123456789-_.()"
        
        filename = ""
        for char in original_filename:
            if char in safe_chars:
                filename += char
            elif char == " ":
                filename += "_"
        
        if not filename or filename == '.pdf':
            name_from_title = ""
            for char in title:
                if char in safe_chars:
                    name_from_title += char
                elif char == " ":
                    name_from_title += "_"
            
            ext = os.path.splitext(original_filename)[1]
            filename = name_from_title + ext
        
        print(f"📝 Оригинальное имя: {original_filename}")
        print(f"📝 Безопасное имя: {filename}")
        
        # Создаём папку если её нет
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Проверяем существование файла с таким именем
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        counter = 1
        name, ext = os.path.splitext(filename)
        
        while os.path.exists(file_path):
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            counter += 1
        
        # Сохраняем файл
        file.save(file_path)
        print(f"✅ Файл сохранён: {file_path}")
        
        # Добавляем в БД
        db_sess = db_session.create_session()
        
        material = Material(
            group_name=group_name,
            subject=subject,
            title=title,
            description=description,
            file_path=file_path,
            file_type=file_type,
            teacher_name=student_name,  # ФИО студента
            upload_date=datetime.now(),
            uploaded_by_role='student'  # ПОМЕЧАЕМ КАК ОТ СТУДЕНТА!
        )
        
        db_sess.add(material)
        db_sess.commit()
        db_sess.close()
        
        print(f"✅ Материал добавлен студентом: {title}")
        print(f"👤 Студент: {student_name}")
        
        return redirect(url_for('student_materials') + '?success=Материал успешно загружен!')
        
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('student_upload_material_page') + f'?error=Ошибка загрузки: {str(e)}')


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


# ==================== РАСПИСАНИЕ (ДЛЯ ВСЕХ) ====================

@app.route('/schedule')
@login_required_custom
def schedule():
    """Универсальная страница расписания для всех"""
    
    # Получаем все группы
    groups_list = get_all_groups()
    
    # 🔍 ОТЛАДКА
    print(f"\n{'='*60}")
    print(f"🔍 ОТЛАДКА РАСПИСАНИЯ:")
    print(f"   Роль пользователя: {session.get('role')}")
    print(f"   Группа студента: {session.get('group')}")
    print(f"   Все группы в БД: {groups_list}")
    
    # Определяем какую группу показать
    if session.get('role') == 'student':
        # Для студента - его группа по умолчанию
        current_group = session.get('group', groups_list[0] if groups_list else None)
    else:
        # Для преподавателя - первая группа или выбранная
        current_group = request.args.get('group', groups_list[0] if groups_list else None)
    
    print(f"   Выбранная группа: {current_group}")
    
    # Получаем расписание
    schedule_data = {}
    if current_group:
        schedule_data = get_schedule_from_db(current_group)
        print(f"   Недель в расписании: {len(schedule_data.get('недели', {}))}")
    else:
        print(f"   ⚠️  Группа не выбрана!")
    
    print(f"{'='*60}\n")
    
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
    """Страница управления материалами для преподавателя"""
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    
    db_sess = db_session.create_session()
    
    # ИЗМЕНЕНО: Получаем ТОЛЬКО материалы этого преподавателя
    teacher_name = session.get('username')
    materials = db_sess.query(Material).filter(
        Material.teacher_name == teacher_name
    ).order_by(Material.upload_date.desc()).all()
    
    # Получаем список групп
    groups = get_all_groups()
    
    db_sess.close()
    
    # Получаем сообщения из URL параметров
    success = request.args.get('success')
    error = request.args.get('error')
    
    return render_template('teacher_materials.html', 
                         materials=materials,
                         groups=groups,
                         success=success,
                         error=error)

@app.route('/teacher/upload_material', methods=['POST'])
@login_required_custom
def upload_material():
    """Загрузка нового материала"""
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    
    try:
        # Проверяем что файл загружен
        if 'file' not in request.files:
            return redirect(url_for('teacher_materials') + '?error=Файл не выбран')
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(url_for('teacher_materials') + '?error=Файл не выбран')
        
        if not allowed_file(file.filename):
            return redirect(url_for('teacher_materials') + '?error=Недопустимый формат файла')
        
        # Получаем данные из формы
        title = request.form.get('title')
        group_name = request.form.get('group_name')
        subject = request.form.get('subject')
        file_type = request.form.get('file_type')
        description = request.form.get('description', '')
        
        # ФИО преподавателя АВТОМАТИЧЕСКИ из сессии
        teacher_name = session.get('username')
        
        # Проверяем обязательные поля
        if not all([title, group_name, subject, file_type]):
            return redirect(url_for('teacher_materials') + '?error=Заполните все обязательные поля')
        
        # Безопасное имя файла с поддержкой русского
        original_filename = file.filename
        
        # Убираем опасные символы, но ОСТАВЛЯЕМ русские буквы
        safe_chars = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        safe_chars += "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        safe_chars += "0123456789-_.()"
        
        filename = ""
        for char in original_filename:
            if char in safe_chars:
                filename += char
            elif char == " ":
                filename += "_"
        
        # Если имя стало пустым
        if not filename or filename == '.pdf':
            name_from_title = ""
            for char in title:
                if char in safe_chars:
                    name_from_title += char
                elif char == " ":
                    name_from_title += "_"
            
            ext = os.path.splitext(original_filename)[1]
            filename = name_from_title + ext
        
        print(f"📝 Оригинальное имя: {original_filename}")
        print(f"📝 Безопасное имя: {filename}")
        
        # Создаём папку если её нет
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Проверяем существование файла с таким именем
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        counter = 1
        name, ext = os.path.splitext(filename)
        
        while os.path.exists(file_path):
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            counter += 1
        
        # Сохраняем файл
        file.save(file_path)
        print(f"✅ Файл сохранён: {file_path}")
        
        # Добавляем в БД
        db_sess = db_session.create_session()
        
        material = Material(
            group_name=group_name,
            subject=subject,
            title=title,
            description=description,
            file_path=file_path,
            file_type=file_type,
            teacher_name=teacher_name,  # Автоматом из сессии!
            upload_date=datetime.now(),
            uploaded_by_role='teacher'
        )
        
        db_sess.add(material)
        db_sess.commit()
        db_sess.close()
        
        print(f"✅ Материал добавлен в БД: {title}")
        print(f"👤 Преподаватель: {teacher_name}")
        
        return redirect(url_for('teacher_materials') + '?success=Материал успешно загружен!')
        
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('teacher_materials') + f'?error=Ошибка загрузки: {str(e)}')

@app.route('/teacher/delete_material/<int:material_id>', methods=['POST'])
@login_required_custom
def delete_material(material_id):
    """Удаление материала"""
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    
    try:
        db_sess = db_session.create_session()
        
        material = db_sess.query(Material).filter(Material.id == material_id).first()
        
        if material:
            # Удаляем файл с диска
            if os.path.exists(material.file_path):
                os.remove(material.file_path)
                print(f"✅ Файл удалён: {material.file_path}")
            
            # Удаляем из БД
            db_sess.delete(material)
            db_sess.commit()
            print(f"✅ Материал удалён из БД: {material.title}")
        
        db_sess.close()
        
        return redirect(url_for('teacher_materials') + '?success=Материал удалён')
        
    except Exception as e:
        print(f"❌ Ошибка удаления: {e}")
        return redirect(url_for('teacher_materials') + f'?error=Ошибка удаления: {str(e)}')


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





# ==================== API ДЛЯ РАСПИСАНИЯ ====================

@app.route('/api/schedule/<group_name>')
def api_schedule(group_name):
    """API расписания для группы"""
    schedule_data = get_schedule_from_db(group_name)
    return jsonify(schedule_data)


@app.route('/api/schedule/<group_name>/week/<int:week_number>')
def api_week(group_name, week_number):
    """API конкретной недели"""
    schedule_data = get_schedule_from_db(group_name)
    week_data = schedule_data.get('недели', {}).get(str(week_number), {})
    return jsonify({
        'группа': group_name,
        'неделя': week_number,
        'расписание': week_data
    })


@app.route('/api/groups')
def api_groups():
    """API списка всех групп"""
    groups = get_all_groups()
    return jsonify(groups)


# ==================== API ДЛЯ ЗАМЕТОК ====================

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
    """Получить все заметки пользователя"""
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
    print(f"📊 Загружено групп из БД: {len(groups)}")
    if groups:
        print(f"📋 Группы: {', '.join(groups)}")
    else:
        print("⚠️  Групп нет! Запустите: python parser.py")
    print("="*70 + "\n")
    
    app.run(debug=True, use_reloader=False)