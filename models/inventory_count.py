from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime
from config.database import Base

class InventoryCount(Base):
    __tablename__ = "inventory_counts"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("stock_locations.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    items = Column(JSON, nullable=False)  # lista de dicts: {product_id, batch_id, counted_quantity, expected_quantity, difference}
    notes = Column(String, nullable=True)