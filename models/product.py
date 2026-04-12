from sqlalchemy import Column, Integer, String, Date, Boolean
from datetime import datetime
from config.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    category_icon = Column(String, nullable=True)
    is_special = Column(Boolean, default=False)   # <--- nuevo campo
    created_at = Column(Date, default=datetime.utcnow)