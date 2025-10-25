import sqlalchemy
from sqlalchemy import orm
from werkzeug.security import generate_password_hash, check_password_hash
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    password_hash = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    full_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    role = sqlalchemy.Column(sqlalchemy.String, nullable=False)  # 'student' или 'teacher'
    
    # Только для студентов
    group_name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    
    # УДАЛИЛИ subject - он больше не нужен!
    
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=sqlalchemy.func.now())

    def set_password(self, password):
        """Хеширует пароль"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет пароль"""
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        """Проверка роли студента"""
        return self.role == 'student'

    def is_teacher(self):
        """Проверка роли преподавателя"""
        return self.role == 'teacher'

    def __repr__(self):
        return f'<User {self.username}>'