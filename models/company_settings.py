from sqlalchemy import Column, Integer, String, Float, Text
from config.database import Base

class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), default="Mi Tienda")
    nif = Column(String(50), default="")
    address = Column(String(300), default="")
    phone = Column(String(50), default="")
    email = Column(String(100), default="")
    logo_path = Column(String(500), nullable=True)  # ruta del archivo de logo
    tax_rate = Column(Float, default=0.0)  # impuesto general (ej. 10.0 = 10%)
    receipt_footer = Column(Text, default="¡Gracias por su compra!")
    currency = Column(String(10), default="CUP")