from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from collections import OrderedDict
import os
from datetime import datetime
from functools import wraps
import unicodedata
from data import db_session
from data.users import User
from data.schedule import Schedule
from data.notes import Note
from data.materials import Material
from flask import send_file, abort

app = Flask(__name__)
app.secret_key = 'hackathon_secret_key_2025'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'doc', 'ppt'}
UPLOAD_FOLDER = 'static/materials'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_schedule_from_db(group_name):
    s = db_session.create_session()
    try:
        e = s.query(Schedule).filter(Schedule.group_name == group_name).order_by(Schedule.week_number, Schedule.lesson_number).all()
        if not e:
            return {}
        d = {'группа': group_name, 'group_id': e[0].group_id if e else None, 'последнее_обновление': e[0].last_updated.strftime('%Y-%m-%d %H:%M:%S') if e else None, 'недели': OrderedDict()}
        weeks = {}
        for entry in e:
            week_num = str(entry.week_number)
            if week_num not in weeks:
                weeks[week_num] = {}
            day_name = entry.day_name
            if day_name not in weeks[week_num]:
                weeks[week_num][day_name] = {'дата': entry.date, 'пары': []}
            weeks[week_num][day_name]['пары'].append({'номер_пары': entry.lesson_number, 'время': entry.time_slot, 'предмет': entry.subject, 'тип': entry.lesson_type, 'преподаватель': entry.teacher, 'аудитория': entry.classroom})
        for week_num in sorted(weeks.keys(), key=int):
            d['недели'][week_num] = weeks[week_num]
        return d
    finally:
        s.close()


def get_all_groups():
    s = db_session.create_session()
    try:
        groups = s.query(Schedule.group_name).distinct().all()
        return [group[0] for group in groups]
    finally:
        s.close()


def login_required_custom(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'student':
            return redirect(url_for('schedule'))
        else:
            return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('login')
        password = request.form.get('password')
        s = db_session.create_session()
        user = s.query(User).filter(User.username == username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.full_name
            session['role'] = user.role
            if user.is_student():
                session['group'] = user.group_name
                s.close()
                return redirect(url_for('schedule'))
            else:
                s.close()
                return redirect(url_for('teacher_dashboard'))
        s.close()
        return render_template('login.html', error='Неверный логин или пароль')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        group_name = request.form.get('group_name') if role == 'student' else None
        s = db_session.create_session()
        existing_user = s.query(User).filter(User.username == username).first()
        if existing_user:
            s.close()
            return render_template('register.html', error='Пользователь с таким логином уже существует', groups=get_all_groups())
        new_user = User(username=username, full_name=full_name, role=role, group_name=group_name)
        new_user.set_password(password)
        s.add(new_user)
        s.commit()
        session['user_id'] = new_user.id
        session['username'] = new_user.full_name
        session['role'] = new_user.role
        if new_user.is_student():
            session['group'] = new_user.group_name
        s.close()
        if role == 'student':
            return redirect(url_for('schedule'))
        else:
            return redirect(url_for('teacher_dashboard'))
    return render_template('register.html', groups=get_all_groups())


@app.route('/profile')
@login_required_custom
def profile():
    if session.get('role') == 'student':
        return redirect(url_for('student_profile'))
    else:
        return redirect(url_for('teacher_profile'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))




@app.route('/student/materials')
@login_required_custom
def student_materials():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    current_group = session.get('group')
    s = db_session.create_session()
    materials = s.query(Material).filter(Material.group_name == current_group).order_by(Material.upload_date.desc()).all()
    subjects = s.query(Material.subject).filter(Material.group_name == current_group).distinct().all()
    subjects = [s[0] for s in subjects]
    s.close()
    success = request.args.get('success')
    error = request.args.get('error')
    return render_template('student_materials.html', materials=materials, subjects=subjects, success=success, error=error)


@app.route('/student/upload_material_page')
@login_required_custom
def student_upload_material_page():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    s = db_session.create_session()
    student_name = session.get('username')
    materials = s.query(Material).filter(Material.teacher_name == student_name, Material.uploaded_by_role == 'student').order_by(Material.upload_date.desc()).all()
    s.close()
    success = request.args.get('success')
    error = request.args.get('error')
    return render_template('student_upload_material.html', materials=materials, success=success, error=error)


@app.route('/student/delete_material/<int:material_id>', methods=['POST'])
@login_required_custom
def student_delete_material(material_id):
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    s = db_session.create_session()
    material = s.query(Material).filter(Material.id == material_id).first()
    if not material:
        s.close()
        return redirect(url_for('student_upload_material_page') + '?error=Материал не найден')
    if material.teacher_name != session.get('username') or material.uploaded_by_role != 'student':
        s.close()
        return redirect(url_for('student_upload_material_page') + '?error=Вы не можете удалить этот материал')
    try:
        if os.path.exists(material.file_path):
            os.remove(material.file_path)
        s.delete(material)
        s.commit()
    except Exception as e:
        s.rollback()
        s.close()
        return redirect(url_for('student_upload_material_page') + f'?error=Ошибка удаления: {str(e)}')
    s.close()
    return redirect(url_for('student_upload_material_page') + '?success=Материал успешно удалён')


@app.route('/student/upload_material', methods=['POST'])
@login_required_custom
def student_upload_material():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    try:
        if 'file' not in request.files:
            return redirect(url_for('student_upload_material_page') + '?error=Файл не выбран')
        file = request.files['file']
        if file.filename == '':
            return redirect(url_for('student_upload_material_page') + '?error=Файл не выбран')
        if not allowed_file(file.filename):
            return redirect(url_for('student_upload_material_page') + '?error=Недопустимый формат файла')
        title = request.form.get('title')
        subject = request.form.get('subject')
        file_type = request.form.get('file_type')
        description = request.form.get('description', '')
        group_name = session.get('group')
        student_name = session.get('username')
        if not all([title, subject, file_type]):
            return redirect(url_for('student_upload_material_page') + '?error=Заполните все обязательные поля')
        original_filename = file.filename
        safe_chars = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.()"
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
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        counter = 1
        name, ext = os.path.splitext(filename)
        while os.path.exists(file_path):
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            counter += 1
        file.save(file_path)
        s = db_session.create_session()
        material = Material(group_name=group_name, subject=subject, title=title, description=description, file_path=file_path, file_type=file_type, teacher_name=student_name, upload_date=datetime.now(), uploaded_by_role='student')
        s.add(material)
        s.commit()
        s.close()
        return redirect(url_for('student_materials') + '?success=Материал успешно загружен!')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(url_for('student_upload_material_page') + f'?error=Ошибка загрузки: {str(e)}')


@app.route('/student/profile')
@login_required_custom
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('teacher_profile'))
    s = db_session.create_session()
    user = s.query(User).get(session['user_id'])
    s.close()
    return render_template('profile.html', user=user)



@app.route('/schedule')
@login_required_custom
def schedule():
    groups_list = get_all_groups()
    if session.get('role') == 'student':
        current_group = session.get('group', groups_list[0] if groups_list else None)
    else:
        current_group = request.args.get('group', groups_list[0] if groups_list else None)
    d = {}
    if current_group:
        d = get_schedule_from_db(current_group)
    return render_template('schedule.html', schedule=d, groups=groups_list, current_group=current_group)


@app.route('/student/schedule')
@login_required_custom
def student_schedule():
    return redirect(url_for('schedule'))

@app.route('/teacher/schedule')
@login_required_custom
def teacher_schedule():
    return redirect(url_for('schedule'))



@app.route('/teacher/dashboard')
@login_required_custom
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('schedule'))
    return render_template('teacher_dashboard.html')


@app.route('/teacher/materials')
@login_required_custom
def teacher_materials():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    s = db_session.create_session()
    teacher_name = session.get('username')
    materials = s.query(Material).filter(Material.teacher_name == teacher_name).order_by(Material.upload_date.desc()).all()
    groups = get_all_groups()
    s.close()
    success = request.args.get('success')
    error = request.args.get('error')
    return render_template('teacher_materials.html', materials=materials, groups=groups, success=success, error=error)


@app.route('/teacher/upload_material', methods=['POST'])
@login_required_custom
def upload_material():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    try:
        if 'file' not in request.files:
            return redirect(url_for('teacher_materials') + '?error=Файл не выбран')
        file = request.files['file']
        if file.filename == '':
            return redirect(url_for('teacher_materials') + '?error=Файл не выбран')
        if not allowed_file(file.filename):
            return redirect(url_for('teacher_materials') + '?error=Недопустимый формат файла')
        title = request.form.get('title')
        group_name = request.form.get('group_name')
        subject = request.form.get('subject')
        file_type = request.form.get('file_type')
        description = request.form.get('description', '')
        teacher_name = session.get('username')
        if not all([title, group_name, subject, file_type]):
            return redirect(url_for('teacher_materials') + '?error=Заполните все обязательные поля')
        original_filename = file.filename
        safe_chars = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.()"
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
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        counter = 1
        name, ext = os.path.splitext(filename)
        while os.path.exists(file_path):
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            counter += 1
        file.save(file_path)
        s = db_session.create_session()
        material = Material(group_name=group_name, subject=subject, title=title, description=description, file_path=file_path, file_type=file_type, teacher_name=teacher_name, upload_date=datetime.now(), uploaded_by_role='teacher')
        s.add(material)
        s.commit()
        s.close()
        return redirect(url_for('teacher_materials') + '?success=Материал успешно загружен!')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(url_for('teacher_materials') + f'?error=Ошибка загрузки: {str(e)}')


@app.route('/teacher/delete_material/<int:material_id>', methods=['POST'])
@login_required_custom
def delete_material(material_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    try:
        s = db_session.create_session()
        material = s.query(Material).filter(Material.id == material_id).first()
        if material:
            if os.path.exists(material.file_path):
                os.remove(material.file_path)
            s.delete(material)
            s.commit()
        s.close()
        return redirect(url_for('teacher_materials') + '?success=Материал удалён')
    except Exception as e:
        return redirect(url_for('teacher_materials') + f'?error=Ошибка удаления: {str(e)}')


@app.route('/teacher/profile')
@login_required_custom
def teacher_profile():
    if session.get('role') != 'teacher':
        return redirect(url_for('student_profile'))
    s = db_session.create_session()
    user = s.query(User).get(session['user_id'])
    s.close()
    return render_template('profile.html', user=user)



@app.route('/api/schedule/<group_name>')
def api_schedule(group_name):
    d = get_schedule_from_db(group_name)
    return jsonify(d)

@app.route('/api/schedule/<group_name>/week/<int:week_number>')
def api_week(group_name, week_number):
    d = get_schedule_from_db(group_name)
    week_data = d.get('недели', {}).get(str(week_number), {})
    return jsonify({'группа': group_name, 'неделя': week_number, 'расписание': week_data})

@app.route('/api/groups')
def api_groups():
    groups = get_all_groups()
    return jsonify(groups)



@app.route('/api/notes/save', methods=['POST'])
@login_required_custom
def save_note():
    data = request.get_json()
    user_id = session.get('user_id')
    group_name = data.get('group_name')
    week_number = data.get('week_number')
    day_name = data.get('day_name')
    note_text = data.get('note_text', '').strip()[:64]
    if not note_text:
        return jsonify({'success': False, 'error': 'Заметка пустая'})
    s = db_session.create_session()
    note = s.query(Note).filter(Note.user_id == user_id, Note.group_name == group_name, Note.week_number == week_number, Note.day_name == day_name).first()
    if note:
        note.note_text = note_text
        note.updated_at = datetime.now()
    else:
        note = Note(user_id=user_id, group_name=group_name, week_number=week_number, day_name=day_name, note_text=note_text)
        s.add(note)
    s.commit()
    s.close()
    return jsonify({'success': True, 'note': note_text})


@app.route('/api/notes/delete', methods=['POST'])
@login_required_custom
def delete_note():
    data = request.get_json()
    user_id = session.get('user_id')
    group_name = data.get('group_name')
    week_number = data.get('week_number')
    day_name = data.get('day_name')
    s = db_session.create_session()
    note = s.query(Note).filter(Note.user_id == user_id, Note.group_name == group_name, Note.week_number == week_number, Note.day_name == day_name).first()
    if note:
        s.delete(note)
        s.commit()
    s.close()
    return jsonify({'success': True})


@app.route('/api/notes/all', methods=['POST'])
@login_required_custom
def get_all_notes():
    data = request.get_json()
    user_id = session.get('user_id')
    group_name = data.get('group_name')
    s = db_session.create_session()
    notes = s.query(Note).filter(Note.user_id == user_id, Note.group_name == group_name).all()
    notes_dict = {}
    for note in notes:
        key = f"{note.week_number}_{note.day_name}"
        notes_dict[key] = note.note_text
    s.close()
    return jsonify({'success': True, 'notes': notes_dict})



@app.route('/download/material/<int:material_id>')
@login_required_custom
def download_material(material_id):
    s = db_session.create_session()
    try:
        material = s.query(Material).filter(Material.id == material_id).first()
        if not material:
            abort(404)
        if session.get('role') == 'student':
            if material.group_name != session.get('group'):
                abort(403)
        target_filename = os.path.basename(material.file_path)
        materials_dir = os.path.join('static', 'materials')
        target_normalized = unicodedata.normalize('NFC', target_filename)
        for filename in os.listdir(materials_dir):
            filename_normalized = unicodedata.normalize('NFC', filename)
            if filename_normalized == target_normalized:
                full_path = os.path.join(materials_dir, filename)
                return send_file(full_path, as_attachment=True, download_name=filename)
        abort(404)
    finally:
        s.close()



@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    db_session.global_init('db/university.db')
    print("🚀 Запуск приложения...")
    app.run(debug=True, use_reloader=False)
