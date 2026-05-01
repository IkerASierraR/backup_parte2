"""
application/restore_use_case.py
Caso de uso: restaurar un backup en la base sandbox.
"""
import os
from datetime import datetime
from typing import Callable, Optional

from domain.entities import ConnectionConfig, OperationStatus, RestoreResult
from domain.interfaces import IDatabaseRepository, ILogger
from shared.config import SANDBOX_SUFFIX


class RestoreUseCase:
    """Orquesta la restauración de un backup en una base de datos sandbox."""

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
        backup_path: str,
        data_directory: str,
        log_directory: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> RestoreResult:
        """
        Construye el nombre sandbox, obtiene archivos lógicos y ejecuta el restore.

        Args:
            config: Configuración de conexión.
            database_name: Nombre original de la BD.
            backup_path: Ruta al archivo .bak.
            data_directory: Directorio destino para el archivo .mdf.
            log_directory: Directorio destino para el archivo .ldf.
            progress_callback: Función para notificar progreso.

        Returns:
            RestoreResult con el resultado de la operación.
        """
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        sandbox_name = f"{database_name}_{SANDBOX_SUFFIX}_{ts}"

        self._logger.info(
            f"[RestoreUseCase] Restaurando '{backup_path}' → sandbox '{sandbox_name}'"
        )

        result = self._repo.execute_restore(
            config=config,
            backup_path=backup_path,
            sandbox_name=sandbox_name,
            data_path=data_directory,
            log_path=log_directory,
            progress_callback=progress_callback,
        )

        if result.status == OperationStatus.SUCCESS:
            self._logger.info(
                f"[RestoreUseCase] Restore exitoso en {result.duration_seconds:.1f}s"
            )
        else:
            self._logger.error(
                f"[RestoreUseCase] Restore fallido: {result.error_message}"
            )

        return result