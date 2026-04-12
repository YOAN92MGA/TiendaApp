import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream
from config.database import engine, Base, SessionLocal
from models.user import User
from models.stock_location import StockLocation
from utils.security import hash_password
from ui.login_window import LoginWindow

def create_database():
    Base.metadata.create_all(bind=engine)

def create_initial_data():
    # ... (igual que antes, pero asegúrate de que los nombres de ubicación sean "Almacen" sin acento)
    db = SessionLocal()
    try:
        if db.query(StockLocation).count() == 0:
            locations = [
                StockLocation(name="Almacen", description="Bodega principal"),
                StockLocation(name="Piso", description="Área de ventas"),
                StockLocation(name="Especiales", description="Productos especiales"),
            ]
            db.add_all(locations)
            db.commit()
        if db.query(User).count() == 0:
            admin = User(username="admin", password=hash_password("admin123"), role="admin")
            db.add(admin)
            db.commit()
    finally:
        db.close()

def main():
    create_database()
    create_initial_data()

    app = QApplication(sys.argv)

    # Cargar hoja de estilos
    style_file = QFile("styles.qss")
    if style_file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(style_file)
        app.setStyleSheet(stream.readAll())
        style_file.close()

    db = SessionLocal()
    window = LoginWindow(db)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()