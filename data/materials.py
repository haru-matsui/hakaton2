import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Material(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'materials'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    group_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)  # Группа
    subject = sqlalchemy.Column(sqlalchemy.String, nullable=False)  # Предмет
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)  # Название материала
    description = sqlalchemy.Column(sqlalchemy.Text)  # Описание
    file_path = sqlalchemy.Column(sqlalchemy.String)  # Путь к файлу (презентация, PDF и т.д.)
    file_type = sqlalchemy.Column(sqlalchemy.String)  # Тип файла (презентация, лекция, практика и т.д.)
    upload_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    teacher_name = sqlalchemy.Column(sqlalchemy.String)  # ФИО преподавателя

    def __repr__(self):
        return f'<Material {self.title} ({self.group_name})>'