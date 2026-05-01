"""
shared/config.py
Configuración global de la aplicación.
"""
import os
from pathlib import Path

# Directorio raíz del proyecto (sql_safebridge/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Directorio de logs
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Nombre de la aplicación
APP_NAME = "SQL-SafeBridge"
APP_VERSION = "1.0.0"

# Sufijo para bases sandbox
SANDBOX_SUFFIX = "SAFEBRIDGE"

# Tiempo máximo de espera para operaciones (segundos)
OPERATION_TIMEOUT = 3600  # 1 hora

# Extensiones de archivo
BACKUP_EXTENSION = ".bak"
LOG_EXTENSION = ".log"
JSON_LOG_EXTENSION = ".json"

# Rutas de datos SQL Server (defaults comunes en Windows)
SQL_DEFAULT_DATA_PATH_WINDOWS = r"C:\Program Files\Microsoft SQL Server\MSSQL15.MSSQLSERVER\MSSQL\DATA"
SQL_DEFAULT_BACKUP_PATH_WINDOWS = r"C:\Program Files\Microsoft SQL Server\MSSQL15.MSSQLSERVER\MSSQL\Backup"

# Tema UI
UI_THEME = "dark"
UI_COLOR_SCHEME = "blue"
UI_FONT_FAMILY = "Roboto"
UI_FONT_SIZE_NORMAL = 13
UI_FONT_SIZE_TITLE = 20
UI_FONT_SIZE_SMALL = 11

# Colores
COLOR_SUCCESS = "#2ecc71"
COLOR_ERROR = "#e74c3c"
COLOR_WARNING = "#f39c12"
COLOR_INFO = "#3498db"
COLOR_MUTED = "#7f8c8d"
