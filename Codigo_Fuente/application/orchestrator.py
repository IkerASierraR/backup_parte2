"""
application/orchestrator.py
Orquestador principal: coordina todos los casos de uso en secuencia.
"""
from datetime import datetime
from typing import Callable, Optional

from application.backup_use_case import BackupUseCase
from application.restore_use_case import RestoreUseCase
from application.validation_use_case import ValidationUseCase
from domain.entities import ConnectionConfig, OperationStatus, OrchestrationResult
from domain.interfaces import IDatabaseRepository, ILogger


class BackupOrchestrator:
    """
    Coordina el flujo completo:
    Conectar → Validar permisos → Backup → Restore → CHECKDB → Logs → DROP sandbox
    """

    def __init__(
        self,
        repository: IDatabaseRepository,
        logger: ILogger,
    ) -> None:
        self._repo = repository
        self._logger = logger
        self._backup_uc = BackupUseCase(repository, logger)
        self._restore_uc = RestoreUseCase(repository, logger)
        self._validation_uc = ValidationUseCase(repository, logger)

    def run(
        self,
        config: ConnectionConfig,
        database_name: str,
        backup_directory: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> OrchestrationResult:
        """
        Ejecuta el flujo completo de orquestación.

        Args:
            config: Configuración de conexión a SQL Server.
            database_name: Base de datos a respaldar y validar.
            backup_directory: Directorio donde guardar el .bak.
            progress_callback: Callback (mensaje: str) → None para notificar la UI.

        Returns:
            OrchestrationResult con el resultado agregado de todas las fases.
        """
        result = OrchestrationResult(
            database_name=database_name,
            backup_path=backup_directory,
            started_at=datetime.now(),
            status=OperationStatus.RUNNING,
        )

        def _cb(msg: str) -> None:
            self._logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        # ── 1. Validar conexión ──────────────────────────────────────
        _cb("Verificando conexión…")
        if not self._repo.test_connection(config):
            return self._fail(result, "No se pudo establecer conexión con SQL Server.")

        # ── 2. Validar permisos ──────────────────────────────────────
        _cb("Verificando permisos…")
        if not self._repo.validate_permissions(config):
            return self._fail(result, "El usuario no tiene rol sysadmin.")

        # ── 3. Backup ────────────────────────────────────────────────
        _cb("Generando respaldo…")
        backup_result = self._backup_uc.execute(
            config=config,
            database_name=database_name,
            backup_directory=backup_directory,
            progress_callback=_cb,
        )
        result.backup_result = backup_result

        if backup_result.status != OperationStatus.SUCCESS:
            return self._fail(
                result,
                f"Respaldo fallido: {backup_result.error_message}",
            )

        # ── 4. Restore sandbox ───────────────────────────────────────
        _cb("Restaurando copia de seguridad…")
        restore_result = self._restore_uc.execute(
            config=config,
            database_name=database_name,
            backup_path=backup_result.backup_path,
            data_directory=backup_directory,
            log_directory=backup_directory,
            progress_callback=_cb,
        )
        result.restore_result = restore_result

        if restore_result.status != OperationStatus.SUCCESS:
            return self._fail(
                result,
                f"Restauración fallida: {restore_result.error_message}",
            )

        sandbox_name = restore_result.sandbox_database

        # ── 5. DBCC CHECKDB ──────────────────────────────────────────
        _cb("Ejecutando prueba de integridad…")
        validation_result = self._validation_uc.execute(
            config=config,
            sandbox_name=sandbox_name,
            progress_callback=_cb,
        )
        result.validation_result = validation_result

        # ── 6. DROP sandbox ──────────────────────────────────────────
        _cb("Limpiando entorno…")
        dropped = self._repo.drop_database(config, sandbox_name)
        result.sandbox_cleaned = dropped
        if dropped:
            _cb("Entorno de prueba eliminado.")
        else:
            _cb("No se pudo eliminar el entorno de prueba.")

        # ── Resultado final ──────────────────────────────────────────
        result.finished_at = datetime.now()
        if validation_result.status == OperationStatus.SUCCESS:
            result.status = OperationStatus.SUCCESS
            _cb("✔️ Prueba exitosa")
        else:
            result.status = OperationStatus.FAILED
            result.error_message = (
                f"La prueba encontró {validation_result.error_count} errores."
            )
            _cb(f"❌ {result.error_message}")

        return result

    # ------------------------------------------------------------------

    def _fail(
        self,
        result: OrchestrationResult,
        message: str,
    ) -> OrchestrationResult:
        """Marca el resultado como fallido y lo retorna."""
        self._logger.error(f"[Orchestrator] FALLO: {message}")
        result.finished_at = datetime.now()
        result.status = OperationStatus.FAILED
        result.error_message = message
        return result