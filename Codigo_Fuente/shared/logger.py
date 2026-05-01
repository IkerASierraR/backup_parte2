"""
shared/logger.py
Sistema de logging con salida a archivo y callback para la UI.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from shared.config import LOGS_DIR, LOG_EXTENSION, JSON_LOG_EXTENSION


class UILogger:
    """
    Logger que escribe en archivo (.log y .json) y notifica
    a la interfaz gráfica mediante un callback opcional.
    """

    def __init__(
        self,
        session_id: str,
        ui_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """
        Args:
            session_id: Identificador único de sesión (usado en el nombre de archivo).
            ui_callback: Función que recibe (nivel, mensaje) para mostrar en la UI.
        """
        self._session_id = session_id
        self._ui_callback = ui_callback
        self._log_entries: list = []

        # Configurar el logger estándar de Python
        self._logger = logging.getLogger(f"sql_safebridge.{session_id}")
        self._logger.setLevel(logging.DEBUG)

        if not self._logger.handlers:
            # Handler para archivo .log legible
            log_file = LOGS_DIR / f"{session_id}{LOG_EXTENSION}"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        # Ruta para JSON estructurado
        self._json_file = LOGS_DIR / f"{session_id}{JSON_LOG_EXTENSION}"

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def info(self, message: str) -> None:
        """Registra un mensaje informativo."""
        self._log("INFO", message)

    def warning(self, message: str) -> None:
        """Registra una advertencia."""
        self._log("WARNING", message)

    def error(self, message: str) -> None:
        """Registra un error."""
        self._log("ERROR", message)

    def debug(self, message: str) -> None:
        """Registra un mensaje de depuración."""
        self._log("DEBUG", message)

    def save_json(self) -> None:
        """Persiste todos los entries en formato JSON."""
        try:
            with open(self._json_file, "w", encoding="utf-8") as f:
                json.dump(self._log_entries, f, indent=2, default=str)
        except OSError as exc:
            self._logger.error("No se pudo guardar el log JSON: %s", exc)

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _log(self, level: str, message: str) -> None:
        """Centraliza el registro en archivo, JSON y UI."""
        timestamp = datetime.now().isoformat()
        entry = {"timestamp": timestamp, "level": level, "message": message}
        self._log_entries.append(entry)

        # Escribir en archivo estándar
        log_fn = getattr(self._logger, level.lower(), self._logger.info)
        log_fn(message)

        # Notificar a la UI
        if self._ui_callback:
            try:
                self._ui_callback(level, message)
            except Exception:
                pass  # La UI no debe romper el flujo principal


def build_session_id(database_name: str) -> str:
    """Genera un identificador de sesión basado en la base y el timestamp."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = database_name.replace(" ", "_")
    return f"{safe_name}_{ts}"
