import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import OrderedDict

class ScheduleParser:
    def __init__(self):
        self.base_url = "https://isu.uust.ru/module/schedule/schedule_2024_script.php"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        # Расписание звонков
        self.time_slots = {
            '1': '08:00-09:20',
            '2': '09:35-10:55',
            '3': '11:35-12:55',
            '4': '13:10-14:30',
            '5': '15:10-16:30',
            '6': '16:45-18:05',
            '7': '18:20-19:40',
            '8': '19:55-21:15',
            '9': '21:25-22:45'
        }
        
        # Дни недели в ПРАВИЛЬНОМ ПОРЯДКЕ
        self.weekdays = {
            '1': 'Понедельник',
            '2': 'Вторник',
            '3': 'Среда',
            '4': 'Четверг',
            '5': 'Пятница',
            '6': 'Суббота'
        }
        
        # Порядок дней для сортировки
        self.weekdays_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
    
    def extract_dates_from_html(self, html_content):
        """Извлекаем даты из HTML (заголовки таблицы)"""
        dates = {}
        
        # Ищем заголовки типа: <th>Понедельник (20.10.2025)</th>
        date_pattern = r'<th[^>]*>(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота)\s*\((\d{2}\.\d{2}\.\d{4})\)'
        matches = re.findall(date_pattern, html_content)
        
        for day_name, date_str in matches:
            dates[day_name] = date_str
        
        return dates
    
    def parse_week(self, group_id, week_number):
        """Парсит расписание для конкретной недели"""
        print(f"📅 Парсинг недели {week_number} для группы {group_id}...")
        
        data = {
            'week': str(week_number),
            'group_id': str(group_id),
            'funct': 'group',
            'show_temp': '0'
        }
        
        try:
            response = requests.post(self.base_url, data=data, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Парсим HTML и JavaScript
            html_content = response.text
            
            # Извлекаем даты из HTML
            dates = self.extract_dates_from_html(html_content)
            
            # Извлекаем JavaScript вставки с расписанием
            schedule_scripts = re.findall(r"\$\('#(\d+_\d+_group)'\)\.append\('(.+?)'\);", html_content)
            
            # ВАЖНО! Используем OrderedDict чтобы сохранить порядок
            week_schedule = OrderedDict()
            
            # Сначала создаём структуру для всех дней В ПРАВИЛЬНОМ ПОРЯДКЕ
            for day_name in self.weekdays_order:
                week_schedule[day_name] = {
                    'дата': dates.get(day_name, ''),
                    'пары': []
                }
            
            # Теперь заполняем пары
            for cell_id, content in schedule_scripts:
                # Парсим ID ячейки: "4_1_group" -> пара 4, день 1
                match = re.match(r'(\d+)_(\d+)_group', cell_id)
                if match:
                    lesson_number = match.group(1)
                    day_number = match.group(2)
                    
                    # Парсим содержимое пары
                    lesson_info = self.parse_lesson_content(content)
                    
                    if lesson_info:
                        day_name = self.weekdays.get(day_number, f'День {day_number}')
                        
                        if day_name in week_schedule:
                            week_schedule[day_name]['пары'].append({
                                'номер_пары': int(lesson_number),
                                'время': self.time_slots.get(lesson_number, ''),
                                **lesson_info
                            })
            
            # Сортируем пары по номеру для каждого дня
            for day in week_schedule:
                week_schedule[day]['пары'] = sorted(
                    week_schedule[day]['пары'], 
                    key=lambda x: x['номер_пары']
                )
            
            # Удаляем дни без пар
            week_schedule_filtered = OrderedDict()
            for day, data in week_schedule.items():
                if data['пары']:
                    week_schedule_filtered[day] = data
            
            return week_schedule_filtered
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге недели {week_number}: {e}")
            return {}
    
    def parse_lesson_content(self, content):
        """Извлекает информацию о паре из HTML"""
        try:
            # Убираем экранирование
            content = content.replace('\\/', '/')
            content = content.replace("\\'", "'")
            
            # Парсим HTML
            soup = BeautifulSoup(f'<div>{content}</div>', 'html.parser')
            text = soup.get_text(separator='|', strip=True)
            
            # Разбиваем на части
            parts = [p.strip() for p in text.split('|') if p.strip()]
            
            if len(parts) < 1:
                return None
            
            # Извлекаем название предмета и тип занятия
            subject_line = parts[0]
            match = re.match(r'(.+?)\s*\((.+?)\)', subject_line)
            
            if match:
                subject = match.group(1).strip()
                lesson_type = match.group(2).strip()
            else:
                subject = subject_line
                lesson_type = 'Неизвестно'
            
            # Извлекаем преподавателя и аудиторию
            teacher = None
            classroom = None
            
            for part in parts[1:]:
                if 'Корпус' in part:
                    classroom = part
                elif part and not part.startswith('Корпус') and len(part) > 2:
                    teacher = part
            
            return {
                'предмет': subject,
                'тип': lesson_type,
                'преподаватель': teacher,
                'аудитория': classroom
            }
            
        except Exception as e:
            print(f"⚠️ Ошибка парсинга содержимого пары: {e}")
            return None
    
    def parse_semester(self, group_id, group_name, start_week=1, end_week=18):
        """Парсит расписание на весь семестр"""
        print(f"\n🎓 Начинаем парсинг расписания для группы {group_name} (ID: {group_id})")
        print(f"📊 Недели: с {start_week} по {end_week}")
        print("="*70)
        
        full_schedule = {
            'группа': group_name,
            'group_id': group_id,
            'последнее_обновление': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'недели': {}
        }
        
        successful_weeks = 0
        total_lessons = 0
        
        for week in range(start_week, end_week + 1):
            week_data = self.parse_week(group_id, week)
            if week_data:
                full_schedule['недели'][str(week)] = week_data
                
                # Считаем количество пар
                lessons_in_week = sum(len(day['пары']) for day in week_data.values())
                total_lessons += lessons_in_week
                
                print(f"✅ Неделя {week} готова: {len(week_data)} дней, {lessons_in_week} пар")
                successful_weeks += 1
            else:
                print(f"⚠️ Неделя {week} пуста или недоступна")
        
        print(f"✨ Парсинг группы {group_name} завершён!")
        print(f"📊 Спарсено: {successful_weeks} недель, {total_lessons} пар")
        print("="*70)
        
        return full_schedule
    
    def save_to_json(self, schedule, filename='schedule_data.json'):
        """Сохраняет расписание в JSON файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)
            print(f"💾 Расписание сохранено в {filename}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False


def load_groups(filename='groups.json'):
    """Загружает список групп из JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            groups = json.load(f)
            print(f"📋 Загружено групп из {filename}: {len(groups)}")
            return groups
    except FileNotFoundError:
        print(f"⚠️ Файл {filename} не найден! Создаю с одной группой...")
        # Дефолтный список если файла нет
        default_groups = [
            {'id': 10990, 'name': 'ТОП-103Б'}
        ]
        # Сохраняем дефолтный список
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(default_groups, f, ensure_ascii=False, indent=2)
        return default_groups
    except Exception as e:
        print(f"❌ Ошибка загрузки списка групп: {e}")
        return [{'id': 10990, 'name': 'ТОП-103Б'}]


def main():
    """Основная функция для запуска парсера"""
    parser = ScheduleParser()
    
    # Загружаем список групп
    groups = load_groups('groups.json')
    
    print("\n" + "="*70)
    print("🚀 ЗАПУСК ПАРСЕРА РАСПИСАНИЯ УУНиТ")
    print(f"📊 Будет спарсено групп: {len(groups)}")
    print("="*70)
    
    all_schedules = {}
    successful = 0
    
    for i, group in enumerate(groups, 1):
        print(f"\n[{i}/{len(groups)}] Парсим группу {group['name']}...")
        
        schedule = parser.parse_semester(
            group_id=group['id'],
            group_name=group['name'],
            start_week=1,
            end_week=18
        )
        
        if schedule and schedule.get('недели'):
            # Сохраняем каждую группу отдельно
            safe_name = group['name'].replace('/', '_').replace('\\', '_')
            filename = f"schedule_{safe_name}.json"
            parser.save_to_json(schedule, filename)
            
            all_schedules[group['name']] = schedule
            successful += 1
        else:
            print(f"⚠️ Группа {group['name']} пропущена (нет данных)")
    
    # Сохраняем всё в один большой файл
    if all_schedules:
        with open('all_schedules.json', 'w', encoding='utf-8') as f:
            json.dump(all_schedules, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Все расписания сохранены в all_schedules.json")
    
    print("\n" + "="*70)
    print("✅ ПАРСИНГ ЗАВЕРШЁН!")
    print(f"📊 Успешно: {successful}/{len(groups)} групп")
    print(f"📁 Создано файлов: {successful + 1}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()