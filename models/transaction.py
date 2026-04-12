from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from config.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("product_batches.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)  # 'entry', 'sale', 'transfer', 'expense'
    quantity = Column(Integer)
    total = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("ProductBatch", backref="transactions")
    user = relationship("User", backref="transactions")