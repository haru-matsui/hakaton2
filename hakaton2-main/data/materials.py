import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Material(SqlAlchemyBase):
    __tablename__ = 'materials'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    group_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    subject = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    file_path = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    file_type = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    teacher_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    upload_date = sqlalchemy.Column(sqlalchemy.DateTime, default=sqlalchemy.func.now())
    
    # НОВОЕ ПОЛЕ - кто загрузил (teacher или student)
    uploaded_by_role = sqlalchemy.Column(sqlalchemy.String, default='teacher')

    def __repr__(self):
        return f'<Material {self.title}>'