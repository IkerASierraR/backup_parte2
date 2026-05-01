"""
application/restore_backup_use_case.py
Caso de uso: restaurar un archivo .bak seleccionado por el usuario.
"""
import os
from datetime import datetime
from typing import Callable, Optional

from domain.entities import ConnectionConfig, OperationStatus, RestoreResult
from domain.interfaces import IDatabaseRepository, ILogger
from shared.config import SANDBOX_SUFFIX


class RestoreBackupUseCase:
    """Orquesta la restauración directa de un backup desde un archivo .bak."""

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
        backup_file: str,
        data_directory: str,
        log_directory: str,
        target_database: Optional[str] = None,
        force: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> RestoreResult:
        """
        Restaura el archivo .bak en una base de datos sandbox (o un nombre dado).

        Args:
            config: Configuración de conexión.
            backup_file: Ruta completa al archivo .bak.
            data_directory: Directorio destino para el archivo .mdf.
            log_directory: Directorio destino para el archivo .ldf.
            target_database: Nombre opcional de la base destino. Si no se provee,
                             se genera uno con sufijo SAFEBRIDGE.
            force: Si es True, sobrescribe la base destino si ya existe.
            progress_callback: Función para notificar progreso.

        Returns:
            RestoreResult con el resultado de la restauración.
        """
        if target_database is None:
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            base_name = os.path.splitext(os.path.basename(backup_file))[0]
            target_database = f"{base_name}_{SANDBOX_SUFFIX}_{ts}"
        else:
            # El usuario proporcionó un nombre de base destino
            pass

        # Verificar si la base destino ya existe
        if self._repo.database_exists(config, target_database):
            if not force:
                msg = (
                    f"La base de datos '{target_database}' ya existe. "
                    "No se puede restaurar porque podrían perderse datos."
                )
                self._logger.warning(f"[RestoreBackupUseCase] {msg}")
                if progress_callback:
                    progress_callback(f"⚠️ {msg}")
                
                result = RestoreResult(
                    source_backup_path=backup_file,
                    sandbox_database=target_database,
                    started_at=datetime.now(),
                    finished_at=datetime.now(),
                    status=OperationStatus.CANCELLED,
                    error_message=msg,
                )
                return result
            else:
                self._logger.warning(
                    f"[RestoreBackupUseCase] La base '{target_database}' ya existe. "
                    "Se sobrescribirá por fuerza (force=True)."
                )
                if progress_callback:
                    progress_callback(
                        f"⚠️ Sobrescribiendo '{target_database}'..."
                    )

        self._logger.info(
            f"[RestoreBackupUseCase] Restaurando '{backup_file}' → '{target_database}'"
        )

        result = self._repo.execute_restore(
            config=config,
            backup_path=backup_file,
            sandbox_name=target_database,
            data_path=data_directory,
            log_path=log_directory,
            progress_callback=progress_callback,
        )

        if result.status == OperationStatus.SUCCESS:
            self._logger.info(
                f"[RestoreBackupUseCase] Restauración completada en {result.duration_seconds:.1f}s"
            )
        else:
            self._logger.error(
                f"[RestoreBackupUseCase] Error al restaurar: {result.error_message}"
            )

        return result