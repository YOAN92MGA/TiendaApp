# services/backup_service.py
import os
import shutil
from datetime import datetime
from typing import List

BACKUP_DIR = "backups"

def ensure_backup_dir():
    """Crea la carpeta de backups si no existe."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def create_backup(db_path: str = "store.db") -> str:
    """Crea una copia de seguridad del archivo de base de datos."""
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"store_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(db_path, backup_path)
    return backup_path

def list_backups() -> List[str]:
    """Devuelve lista de nombres de archivos de backup ordenados por fecha (más reciente primero)."""
    ensure_backup_dir()
    files = [f for f in os.listdir(BACKUP_DIR) if f.startswith("store_") and f.endswith(".db")]
    # Ordenar por fecha (el nombre contiene timestamp)
    files.sort(reverse=True)
    return files

def restore_backup(backup_name: str, db_path: str = "store.db") -> bool:
    """Restaura una copia de seguridad sobrescribiendo la base de datos actual."""
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"No se encuentra el backup: {backup_name}")
    # Copiar backup a la ubicación original
    shutil.copy2(backup_path, db_path)
    return True