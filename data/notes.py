import datetime
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Note(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'notes'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    group_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    week_number = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    day_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)  # Понедельник, Вторник и т.д.
    note_text = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)  # Максимум 64 символа
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def __repr__(self):
        return f'<Note user_id={self.user_id} {self.day_name} week={self.week_number}>'