from data import sion
from data.users import User

def update_database():
    sion.global_init('db/university.db')
    print("🚀 БД обновлена")

if __name__ == '__main__':
    update_database()