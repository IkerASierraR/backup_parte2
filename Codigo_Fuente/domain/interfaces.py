"""
domain/interfaces.py
Interfaces (puertos) del dominio — contratos que la infraestructura debe implementar.
"""
from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from domain.entities import (
    BackupResult,
    ConnectionConfig,
    LogicalFile,
    RestoreResult,
    ValidationResult,
)


class IDatabaseRepository(ABC):
    """Contrato para operaciones contra SQL Server."""

    @abstractmethod
    def test_connection(self, config: ConnectionConfig) -> bool:
        """Valida que la conexión sea exitosa."""

    @abstractmethod
    def validate_permissions(self, config: ConnectionConfig) -> bool:
        """Verifica que el usuario tenga rol sysadmin."""

    @abstractmethod
    def list_databases(self, config: ConnectionConfig) -> List[str]:
        """Retorna la lista de bases de datos disponibles."""

    @abstractmethod
    def database_exists(self, config: ConnectionConfig, database_name: str) -> bool:
        """Verifica si una base de datos existe en el servidor."""

    @abstractmethod
    def execute_backup(
        self,
        config: ConnectionConfig,
        database_name: str,
        backup_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> BackupResult:
        """Ejecuta un BACKUP FULL de la base de datos."""

    @abstractmethod
    def get_logical_files(
        self, config: ConnectionConfig, backup_path: str
    ) -> List[LogicalFile]:
        """Obtiene los archivos lógicos de un backup."""

    @abstractmethod
    def execute_restore(
        self,
        config: ConnectionConfig,
        backup_path: str,
        sandbox_name: str,
        data_path: str,
        log_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> RestoreResult:
        """Restaura un backup en la base sandbox."""

    @abstractmethod
    def execute_checkdb(
        self,
        config: ConnectionConfig,
        database_name: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> ValidationResult:
        """Ejecuta DBCC CHECKDB sobre una base de datos."""

    @abstractmethod
    def drop_database(
        self, config: ConnectionConfig, database_name: str
    ) -> bool:
        """Elimina una base de datos."""

    @abstractmethod
    def get_default_backup_path(self, config: ConnectionConfig) -> str:
        """Obtiene la ruta de backup por defecto de SQL Server."""


class ILogger(ABC):
    """Contrato para el sistema de logs."""

    @abstractmethod
    def info(self, message: str) -> None:
        """Registra un mensaje informativo."""

    @abstractmethod
    def warning(self, message: str) -> None:
        """Registra un mensaje de advertencia."""

    @abstractmethod
    def error(self, message: str) -> None:
        """Registra un mensaje de error."""

    @abstractmethod
    def debug(self, message: str) -> None:
        """Registra un mensaje de depuración."""