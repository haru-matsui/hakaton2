import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import OrderedDict
from data import sion
from data.schedule import Schedule

class ScheduleParser:
    def __init__(self):
        self.base_url = "https://isu.uust.ru/module/schedule/schedule_2024_script.php"
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest'}
        self.time_slots = {'1': '08:00-09:20', '2': '09:35-10:55', '3': '11:35-12:55', '4': '13:10-14:30', '5': '15:10-16:30', '6': '16:45-18:05', '7': '18:20-19:40', '8': '19:55-21:15', '9': '21:25-22:45'}
        self.weekdays = {'1': 'Понедельник', '2': 'Вторник', '3': 'Среда', '4': 'Четверг', '5': 'Пятница', '6': 'Суббота'}
        self.weekdays_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
    
    def extract_dates_from_html(self, html_content):
        dates = {}
        date_pattern = r'<th[^>]*>(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота)\s*\((\d{2}\.\d{2}\.\d{4})\)'
        matches = re.findall(date_pattern, html_content)
        for day_name, date_str in matches:
            dates[day_name] = date_str
        return dates
    
    def parse_week(self, group_id, week_number):
        data = {'week': str(week_number), 'group_id': str(group_id), 'funct': 'group', 'show_temp': '0'}
        try:
            response = requests.post(self.base_url, data=data, headers=self.headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            dates = self.extract_dates_from_html(html_content)
            ss = re.findall(r"\$\('#(\d+_\d+_group)'\)\.append\('(.+?)'\);", html_content)
            ws = OrderedDict()
            for day_name in self.weekdays_order:
                ws[day_name] = {'дата': dates.get(day_name, ''), 'пары': []}
            for cell_id, content in ss:
                match = re.match(r'(\d+)_(\d+)_group', cell_id)
                if match:
                    lesson_number = match.group(1)
                    day_number = match.group(2)
                    li = self.parse_lesson_content(content)
                    if li:
                        day_name = self.weekdays.get(day_number, f'День {day_number}')
                        if day_name in ws:
                            ws[day_name]['пары'].append({'номер_пары': int(lesson_number), 'время': self.time_slots.get(lesson_number, ''), **li})
            for day in ws:
                ws[day]['пары'] = sorted(ws[day]['пары'], key=lambda x: x['номер_пары'])
            ws_filtered = OrderedDict()
            for day, data in ws.items():
                if data['пары']:
                    ws_filtered[day] = data
            return ws_filtered
        except Exception as e:
            return {}
    
    def parse_lesson_content(self, content):
        try:
            content = content.replace('\\/', '/')
            content = content.replace("\\'", "'")
            soup = BeautifulSoup(f'<div>{content}</div>', 'html.parser')
            text = soup.get_text(separator='|', strip=True)
            parts = [p.strip() for p in text.split('|') if p.strip()]
            if len(parts) < 1:
                return None
            subject_line = parts[0]
            match = re.match(r'(.+?)\s*\((.+?)\)', subject_line)
            if match:
                subject = match.group(1).strip()
                lesson_type = match.group(2).strip()
            else:
                subject = subject_line
                lesson_type = 'Неизвестно'
            teacher = None
            classroom = None
            for part in parts[1:]:
                if 'Корпус' in part:
                    classroom = part
                elif part and not part.startswith('Корпус') and len(part) > 2:
                    teacher = part
            return {'предмет': subject, 'тип': lesson_type, 'преподаватель': teacher, 'аудитория': classroom}
        except Exception as e:
            return None
    
    def save_to_database(self, group_id, group_name, week_number, week_data):
        try:
            s = sion.create_session()
            s.query(Schedule).filter(Schedule.group_id == group_id, Schedule.week_number == week_number).delete()
            for day_name, day_data in week_data.items():
                date_str = day_data.get('дата', '')
                for lesson in day_data['пары']:
                    schedule_entry = Schedule(group_name=group_name, group_id=group_id, week_number=week_number, day_name=day_name, date=date_str, lesson_number=lesson['номер_пары'], time_slot=lesson['время'], subject=lesson['предмет'], lesson_type=lesson['тип'], teacher=lesson['преподаватель'], classroom=lesson['аудитория'], last_updated=datetime.now())
                    s.add(schedule_entry)
            s.commit()
            return True
        except Exception as e:
            s.rollback()
            return False
        finally:
            s.close()
    
    def parse_semester(self, group_id, group_name, start_week=1, end_week=18):
        successful_weeks = 0
        total_lessons = 0
        for week in range(start_week, end_week + 1):
            week_data = self.parse_week(group_id, week)
            if week_data:
                if self.save_to_database(group_id, group_name, week, week_data):
                    lessons_in_week = sum(len(day['пары']) for day in week_data.values())
                    total_lessons += lessons_in_week
                    successful_weeks += 1
        return successful_weeks > 0


def load_groups(filename='groups.json'):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            groups = json.load(f)
            return groups
    except FileNotFoundError:
        default_groups = [{'id': 10990, 'name': 'ТОП-103Б'}]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(default_groups, f, ensure_ascii=False, indent=2)
        return default_groups
    except Exception as e:
        return [{'id': 10990, 'name': 'ТОП-103Б'}]


def main():
    sion.global_init('db/university.db')
    parser = ScheduleParser()
    groups = load_groups('groups.json')
    print("🚀 Запуск парсера...")
    successful = 0
    for i, group in enumerate(groups, 1):
        success = parser.parse_semester(group_id=group['id'], group_name=group['name'], start_week=1, end_week=18)
        if success:
            successful += 1

if __name__ == '__main__':
    main()