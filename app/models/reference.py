from sqlalchemy import Column, Integer, String

from app.database import Base


class Ward(Base):
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    zone = Column(String, nullable=True)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    default_priority = Column(String, nullable=False, default="medium")
    sla_hours = Column(Integer, nullable=False, default=36)
