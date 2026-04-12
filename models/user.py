from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from config.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)

    password = Column(String, nullable=False)

    role = Column(String, default="employee")

    created_at = Column(DateTime, default=datetime.utcnow)