from data import db_session
from data.users import User

def update_database():
    db_session.global_init('db/university.db')
    print("🚀 БД обновлена")

if __name__ == '__main__':
    update_database()