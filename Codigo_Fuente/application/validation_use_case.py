"""
application/validation_use_case.py
Caso de uso: ejecutar DBCC CHECKDB sobre la base sandbox.
"""
from typing import Callable, Optional

from domain.entities import ConnectionConfig, OperationStatus, ValidationResult
from domain.interfaces import IDatabaseRepository, ILogger


class ValidationUseCase:
    """Orquesta la validación de integridad mediante DBCC CHECKDB."""

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
        sandbox_name: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> ValidationResult:
        """
        Ejecuta DBCC CHECKDB sobre la base sandbox.

        Args:
            config: Configuración de conexión.
            sandbox_name: Nombre de la base sandbox.
            progress_callback: Función para notificar progreso.

        Returns:
            ValidationResult con el resultado de la validación.
        """
        self._logger.info(
            f"[ValidationUseCase] Ejecutando DBCC CHECKDB('{sandbox_name}')"
        )

        result = self._repo.execute_checkdb(
            config=config,
            database_name=sandbox_name,
            progress_callback=progress_callback,
        )

        if result.status == OperationStatus.SUCCESS:
            self._logger.info(
                f"[ValidationUseCase] CHECKDB OK — sin errores "
                f"({result.duration_seconds:.1f}s)"
            )
        else:
            self._logger.error(
                f"[ValidationUseCase] CHECKDB falló: "
                f"{result.error_count} errores — {result.error_message or ''}"
            )

        return result