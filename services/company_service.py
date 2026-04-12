from sqlalchemy.orm import Session
from models.company_settings import CompanySettings

def get_company_settings(db: Session) -> CompanySettings:
    """Obtiene la configuración de la empresa (crea una por defecto si no existe)."""
    settings = db.query(CompanySettings).first()
    if not settings:
        settings = CompanySettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

def update_company_settings(db: Session, **kwargs) -> CompanySettings:
    """Actualiza la configuración de la empresa con los valores proporcionados."""
    settings = get_company_settings(db)
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings