from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QInputDialog, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import Session
from models.cash_register import CashRegister
from services.cash_service import get_registers, add_movement
from ui.cash_movements_view import CashMovementsView

class CashRegisterWindow(QWidget):
    def __init__(self, db: Session, user):
        super().__init__()
        self.db = db
        self.user = user
        self.setWindowTitle("Gestión de Cajas")
        self.setStyleSheet("background-color: #F5F7FA;")
        layout = QVBoxLayout()

        # Botones superiores
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Nueva caja")
        self.add_btn.clicked.connect(self.add_register)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Tabla de cajas
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Principal"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.view_movements)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_registers()

    def load_registers(self):
        registers = get_registers(self.db)
        self.table.setRowCount(len(registers))
        for row, reg in enumerate(registers):
            self.table.setItem(row, 0, QTableWidgetItem(str(reg.id)))
            self.table.setItem(row, 1, QTableWidgetItem(reg.name))
            self.table.setItem(row, 2, QTableWidgetItem("Sí" if reg.is_main else "No"))

    def add_register(self):
        name, ok = QInputDialog.getText(self, "Nueva caja", "Nombre de la caja:")
        if ok and name:
            is_main = False
            if not self.db.query(CashRegister).filter(CashRegister.is_main == True).first():
                is_main = True
            new_reg = CashRegister(name=name, is_main=is_main)
            self.db.add(new_reg)
            self.db.commit()
            self.load_registers()
            QMessageBox.information(self, "Éxito", f"Caja '{name}' creada.")

    def view_movements(self, index):
        row = index.row()
        reg_id = int(self.table.item(row, 0).text())
        reg_name = self.table.item(row, 1).text()
        self.movements_view = CashMovementsView(self.db, reg_id, reg_name)
        self.movements_view.show()