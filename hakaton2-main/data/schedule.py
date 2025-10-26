import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Schedule(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'schedule'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    group_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    group_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    week_number = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    day_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)  # Понедельник, Вторник и т.д.
    date = sqlalchemy.Column(sqlalchemy.String)  # Дата в формате DD.MM.YYYY
    lesson_number = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    time_slot = sqlalchemy.Column(sqlalchemy.String)  # Время пары (08:00-09:20)
    subject = sqlalchemy.Column(sqlalchemy.String)  # Название предмета
    lesson_type = sqlalchemy.Column(sqlalchemy.String)  # Лекция, Практика и т.д.
    teacher = sqlalchemy.Column(sqlalchemy.String)  # ФИО преподавателя
    classroom = sqlalchemy.Column(sqlalchemy.String)  # Аудитория
    last_updated = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return f'<Schedule {self.group_name} - {self.day_name} - Пара {self.lesson_number}>'