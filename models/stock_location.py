from sqlalchemy import Column, Integer, String
from config.database import Base

class StockLocation(Base):
    __tablename__ = "stock_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)