"""
application/backup_use_case.py
Caso de uso: ejecutar un BACKUP FULL.
"""
import os
from datetime import datetime
from typing import Callable, Optional

from domain.entities import BackupResult, ConnectionConfig, OperationStatus
from domain.interfaces import IDatabaseRepository, ILogger


class BackupUseCase:
    """Orquesta la generación de un backup FULL en SQL Server."""

    def __init__(
        self,
        repository: IDatabaseRepository,
        logger: ILogger,
    ) -> None:
        self._repo = repository
        self._logger = logger

    def execute(
        self,
        config: ConnectionConfig,
        database_name: str,
        backup_directory: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> BackupResult:
        """
        Genera el nombre de archivo, valida el directorio y ejecuta el backup.

        Args:
            config: Configuración de conexión.
            database_name: Nombre de la BD a respaldar.
            backup_directory: Directorio donde se guardará el .bak.
            progress_callback: Función para notificar progreso.

        Returns:
            BackupResult con el resultado de la operación.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{database_name}_{ts}_FULL.bak"
        backup_path = os.path.join(backup_directory, filename)

        self._logger.info(f"[BackupUseCase] Iniciando backup: {backup_path}")

        result = self._repo.execute_backup(
            config=config,
            database_name=database_name,
            backup_path=backup_path,
            progress_callback=progress_callback,
        )

        if result.status == OperationStatus.SUCCESS:
            self._logger.info(
                f"[BackupUseCase] Backup exitoso — {result.file_size_mb} MB "
                f"en {result.duration_seconds:.1f}s"
            )
        else:
            self._logger.error(
                f"[BackupUseCase] Backup fallido: {result.error_message}"
            )

        return result