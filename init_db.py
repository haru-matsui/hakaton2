import os
from data import db_session
from data.users import User
from data.schedule import Schedule
from data.notes import Note
from data.materials import Material

def create_database():
    if not os.path.exists('db'):
        os.makedirs('db')
    db_file = 'db/university.db'
    db_session.global_init(db_file)
    print("🚀 БД инициализирована")

if __name__ == '__main__':
    create_database()
