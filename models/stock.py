from sqlalchemy import Column, Integer, ForeignKey
from config.database import Base

class Stock(Base):
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("stock_locations.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)