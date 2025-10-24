from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'hackathon_secret_key_2025'

# Глобальная переменная для хранения всех расписаний
all_schedules = {}
groups_list = []

def load_all_schedules():
    """Загружает все расписания групп"""
    global all_schedules, groups_list
    try:
        if os.path.exists('all_schedules.json'):
            with open('all_schedules.json', 'r', encoding='utf-8') as f:
                all_schedules = json.load(f)
            groups_list = list(all_schedules.keys())
            print(f"✅ Загружено расписаний: {len(all_schedules)} групп")
            print(f"📋 Группы: {', '.join(groups_list)}")
        else:
            print("⚠️ Файл all_schedules.json не найден!")
            print("💡 Запусти сначала: python parser.py")
            all_schedules = {}
            groups_list = []
    except Exception as e:
        print(f"❌ Ошибка загрузки расписаний: {e}")
        all_schedules = {}
        groups_list = []

def load_json_data(filename):
    """Загружает данные из JSON файла"""
    filepath = os.path.join('static', 'data', filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def login_required(f):
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
    """Главная страница - перенаправление"""
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
        login_input = request.form.get('login')
        password = request.form.get('password')
        
        users_data = load_json_data('users.json')
        
        # Проверяем студентов
        for student in users_data.get('students', []):
            if student['login'] == login_input and student['password'] == password:
                session['user_id'] = student['id']
                session['username'] = student['name']
                session['role'] = 'student'
                session['group'] = student['group']
                return redirect(url_for('student_dashboard'))
        
        # Проверяем преподавателей
        for teacher in users_data.get('teachers', []):
            if teacher['login'] == login_input and teacher['password'] == password:
                session['user_id'] = teacher['id']
                session['username'] = teacher['name']
                session['role'] = 'teacher'
                session['subject'] = teacher['subject']
                return redirect(url_for('teacher_dashboard'))
        
        return render_template('login.html', error='Неверный логин или пароль')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('login'))

# ==================== СТУДЕНТ ====================

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    """Главная страница студента"""
    if session.get('role') != 'student':
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('student_dashboard.html')

@app.route('/student/schedule')
@login_required
def schedule():
    """Страница расписания"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    # Получаем текущую группу студента
    current_group = session.get('group', 'ТОП-103Б')
    
    # Получаем расписание текущей группы
    schedule_data = all_schedules.get(current_group, {})
    
    return render_template('schedule.html', 
                         schedule=schedule_data,
                         groups=groups_list,
                         current_group=current_group)

@app.route('/student/materials')
@login_required
def materials():
    """Страница учебных материалов"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    materials_data = load_json_data('materials.json')
    return render_template('materials.html', materials=materials_data.get('materials', []))

@app.route('/student/ipr')
@login_required
def ipr():
    """Страница ИПР"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    ipr_data = load_json_data('ipr.json')
    user_ipr = None
    
    for student_ipr in ipr_data.get('students', []):
        if student_ipr['student_id'] == session.get('user_id'):
            user_ipr = student_ipr
            break
    
    return render_template('ipr.html', ipr=user_ipr)

@app.route('/student/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    """Страница обратной связи"""
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Здесь сохраняем отзыв
        return render_template('feedback.html', success=True)
    
    teachers_data = load_json_data('users.json')
    return render_template('feedback.html', teachers=teachers_data.get('teachers', []))

# ==================== ПРЕПОДАВАТЕЛЬ ====================

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    """Главная страница преподавателя"""
    if session.get('role') != 'teacher':
        return redirect(url_for('student_dashboard'))
    
    return render_template('teacher_dashboard.html')

@app.route('/teacher/grades')
@login_required
def grades():
    """Страница успеваемости"""
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    
    grades_data = load_json_data('grades.json')
    return render_template('grades.html', students=grades_data.get('students', []))

# ==================== API ====================

@app.route('/api/schedule/<group_name>')
def api_schedule(group_name):
    """API для получения расписания конкретной группы"""
    schedule_data = all_schedules.get(group_name, {})
    return jsonify(schedule_data)

@app.route('/api/schedule/<group_name>/week/<int:week_number>')
def api_week(group_name, week_number):
    """API для получения конкретной недели группы"""
    schedule_data = all_schedules.get(group_name, {})
    week_data = schedule_data.get('недели', {}).get(str(week_number), {})
    return jsonify({
        'группа': group_name,
        'неделя': week_number,
        'расписание': week_data
    })

@app.route('/api/groups')
def api_groups():
    """API для получения списка групп"""
    return jsonify(groups_list)

if __name__ == '__main__':
    load_all_schedules()
    
    print("\n" + "="*70)
    print("🎓 ЛИЧНЫЙ КАБИНЕТ СТУДЕНТА - ХАКАТОН 2025")
    print("="*70)
    print(f"🌐 Сайт:         http://127.0.0.1:5000/")
    print(f"🔑 Студент:      student1 / password")
    print(f"🔑 Преподаватель: teacher1 / password")
    print(f"📊 Загружено групп: {len(groups_list)}")
    if groups_list:
        print(f"📋 Группы: {', '.join(groups_list)}")
    print("="*70 + "\n")
    
    app.run(debug=True, use_reloader=False)