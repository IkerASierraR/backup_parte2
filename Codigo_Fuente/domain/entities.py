"""
domain/entities.py
Entidades del dominio de SQL-SafeBridge.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OperationStatus(Enum):
    """Estado de una operación."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ConnectionConfig:
    """Configuración de conexión a SQL Server."""
    server: str
    username: str = ""
    password: str = ""
    database: str = "master"
    driver: str = "ODBC Driver 18 for SQL Server"
    trust_certificate: bool = True
    use_windows_auth: bool = False

    def build_connection_string(self) -> str:
        """Construye el connection string dinámicamente según el modo de autenticación."""
        base = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"TrustServerCertificate={'yes' if self.trust_certificate else 'no'};"
        )
        if self.use_windows_auth:
            return base + "Trusted_Connection=yes;"
        return base + f"UID={self.username};PWD={self.password};"


@dataclass
class BackupResult:
    """Resultado de una operación de backup."""
    database_name: str
    backup_path: str
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    status: OperationStatus = OperationStatus.PENDING
    error_message: Optional[str] = None
    file_size_mb: Optional[float] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class RestoreResult:
    """Resultado de una operación de restore."""
    source_backup_path: str
    sandbox_database: str
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    status: OperationStatus = OperationStatus.PENDING
    error_message: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class ValidationResult:
    """Resultado de DBCC CHECKDB."""
    database_name: str
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    status: OperationStatus = OperationStatus.PENDING
    error_count: int = 0
    warning_count: int = 0
    checkdb_output: str = ""
    error_message: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        return self.status == OperationStatus.SUCCESS and self.error_count == 0

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class OrchestrationResult:
    """Resultado completo de la orquestación."""
    database_name: str
    backup_path: str
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    status: OperationStatus = OperationStatus.PENDING
    backup_result: Optional[BackupResult] = None
    restore_result: Optional[RestoreResult] = None
    validation_result: Optional[ValidationResult] = None
    sandbox_cleaned: bool = False
    error_message: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


@dataclass
class LogicalFile:
    """Archivo lógico dentro de un backup."""
    logical_name: str
    physical_name: str
    file_type: str  # 'D' para datos, 'L' para log