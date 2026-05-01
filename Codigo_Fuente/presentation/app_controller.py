"""
presentation/app_controller.py
Controlador principal de la aplicación.
"""
import threading
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from application.orchestrator import BackupOrchestrator
from application.restore_backup_use_case import RestoreBackupUseCase
from domain.entities import ConnectionConfig, OperationStatus
from infrastructure.sql_server_repository import SqlServerRepository
from presentation.dashboard_screen import DashboardScreen
from presentation.dialogs import show_error, show_success, show_warning
from presentation.login_screen import LoginScreen
from shared.config import (
    APP_NAME,
    APP_VERSION,
    BASE_DIR,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
    UI_COLOR_SCHEME,
    UI_THEME,
)
from shared.logger import UILogger, build_session_id


class AppController(ctk.CTk):
    """
    Ventana raíz de la aplicación.
    Maneja la navegación entre LoginScreen y DashboardScreen.

    Al iniciarse intenta una conexión automática con Autenticación Windows;
    si tiene éxito pasa directamente al dashboard, de lo contrario muestra
    la pantalla de login con el formulario completo.
    """

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode(UI_THEME)
        ctk.set_default_color_theme(UI_COLOR_SCHEME)

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("900x700")
        self.minsize(800, 600)

        self._config: Optional[ConnectionConfig] = None
        self._repository = SqlServerRepository()
        self._logger: Optional[UILogger] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._show_login()
        # Intentar conexión automática en segundo plano
        threading.Thread(target=self._try_auto_connect, daemon=True).start()

    # ------------------------------------------------------------------
    # Conexión automática
    # ------------------------------------------------------------------

    def _try_auto_connect(self) -> None:
        """
        Ejecuta en segundo plano: intenta conectarse con Autenticación Windows
        usando los servidores candidatos del equipo local.
        Siempre pasa la lista de candidatos al login para que el usuario
        pueda elegir entre ellos si la conexión automática falla.
        """
        self.after(
            0,
            lambda: self._update_login_status(
                "🔍 Detectando servidor SQL Server automáticamente…",
                "gray",
            ),
        )

        # Obtener candidatos y pasarlos al login como sugerencias de inmediato
        candidates = SqlServerRepository.discover_servers()
        self.after(0, lambda: self._update_server_suggestions(candidates))

        config = SqlServerRepository.try_auto_connect()
        if config is None:
            self.after(
                0,
                lambda: self._update_login_status(
                    "⚠️ No se detectó SQL Server automáticamente. "
                    "Selecciona una opción del desplegable o escribe el servidor manualmente.",
                    COLOR_WARNING,
                ),
            )
            return

        # Obtener bases de datos y ruta de backup
        try:
            databases = self._repository.list_databases(config)
            default_path = self._repository.get_default_backup_path(config)
        except Exception:
            databases = []
            default_path = ""

        self._config = config
        self.after(
            0,
            lambda: self._show_main(
                config.server, "Windows Auth", databases, default_path
            ),
        )

    def _update_login_status(self, message: str, color: str) -> None:
        """Actualiza el banner de estado en la pantalla de login (si está visible)."""
        for widget in self.winfo_children():
            if isinstance(widget, LoginScreen):
                widget.show_auto_connect_status(message, color)
                break

    def _update_server_suggestions(self, servers: list) -> None:
        """Pasa la lista de servidores detectados al combobox del login."""
        for widget in self.winfo_children():
            if isinstance(widget, LoginScreen):
                widget.set_server_suggestions(servers)
                break

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def _clear_frames(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()

    def _show_login(self) -> None:
        """Muestra la pantalla de login centrada."""
        self._clear_frames()
        frame = LoginScreen(
            master=self,
            on_login_success=self._handle_login,
        )
        frame.grid(row=0, column=0, sticky="nsew")

    def _show_main(
        self,
        server: str,
        username: str,
        databases: list,
        default_backup_path: str,
    ) -> None:
        """Muestra el dashboard a pantalla completa."""
        self._clear_frames()
        self._dashboard = DashboardScreen(
            master=self,
            server_name=server,
            username=username,
            databases=databases,
            default_backup_path=default_backup_path,
            on_run=self._handle_run,
            on_restore=self._handle_restore,
            on_logout=self._handle_logout,
        )
        self._dashboard.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_login(
        self,
        server: str,
        username: str,
        password: str,
        use_windows_auth: bool,
    ) -> None:
        """Valida credenciales y navega al dashboard."""
        config = ConnectionConfig(
            server=server,
            username=username,
            password=password,
            use_windows_auth=use_windows_auth,
        )

        def _do_connect() -> None:
            ok = self._repository.test_connection(config)
            if not ok:
                if use_windows_auth:
                    hint = (
                        f"No se pudo conectar al servidor '{server}' usando "
                        "Autenticación Windows.\n\n"
                        "Posibles causas:\n"
                        "• El nombre del servidor o instancia es incorrecto\n"
                        "  (usa el desplegable para ver las opciones detectadas)\n"
                        "• SQL Server no está iniciado\n"
                        "• La cuenta de Windows no tiene acceso a SQL Server"
                    )
                else:
                    hint = (
                        f"No se pudo conectar al servidor '{server}'.\n\n"
                        "Posibles causas:\n"
                        "• El nombre del servidor o instancia es incorrecto\n"
                        "• El usuario o la contraseña son incorrectos\n"
                        "• La autenticación SQL Server no está habilitada"
                    )
                self.after(0, lambda: self._on_login_failed(hint))
                return

            has_perm = self._repository.validate_permissions(config)
            if not has_perm:
                self.after(
                    0,
                    lambda: self._on_login_failed(
                        "Permisos insuficientes.\n\n"
                        "El usuario necesita rol sysadmin en SQL Server."
                    ),
                )
                return

            databases = self._repository.list_databases(config)
            default_path = self._repository.get_default_backup_path(config)
            self._config = config
            display_user = "Windows Auth" if use_windows_auth else username
            self.after(
                0,
                lambda: self._show_main(server, display_user, databases, default_path),
            )

        threading.Thread(target=_do_connect, daemon=True).start()

    def _on_login_failed(self, message: str) -> None:
        """Muestra error en ventana emergente y restablece el login."""
        show_error(self, "Error de conexión", message)
        for widget in self.winfo_children():
            if isinstance(widget, LoginScreen):
                widget.reset()
                break

    def _handle_logout(self) -> None:
        """Cierra sesión y vuelve al login."""
        self._config = None
        self._show_login()

    def _handle_run(self, database_name: str, backup_path: str) -> None:
        """Inicia la orquestación completa (backup + validación)."""
        if not self._config:
            return

        session_id = build_session_id(database_name)
        self._logger = UILogger(
            session_id=session_id,
            ui_callback=self._ui_log_callback,
        )

        self._dashboard.start_operation()

        orchestrator = BackupOrchestrator(
            repository=self._repository,
            logger=self._logger,
        )

        def _run() -> None:
            result = orchestrator.run(
                config=self._config,
                database_name=database_name,
                backup_directory=backup_path,
                progress_callback=self._dashboard.update_progress,
            )
            self._logger.save_json()
            self.after(0, lambda: self._on_operation_done(result))

        threading.Thread(target=_run, daemon=True).start()

    def _handle_restore(self, backup_file: str, target_database: Optional[str], force: bool) -> None:
        """Inicia la restauración de un archivo .bak cargado por el usuario."""
        if not self._config:
            return

        session_id = build_session_id("restore_backup")
        self._logger = UILogger(
            session_id=session_id,
            ui_callback=self._ui_log_callback,
        )

        self._dashboard.start_operation()

        use_case = RestoreBackupUseCase(
            repository=self._repository,
            logger=self._logger,
        )

        default_dir = self._repository.get_default_backup_path(self._config)

        def _run() -> None:
            result = use_case.execute(
                config=self._config,
                backup_file=backup_file,
                data_directory=default_dir,
                log_directory=default_dir,
                target_database=target_database,
                force=force,
                progress_callback=self._dashboard.update_progress,
            )
            self._logger.save_json()
            self.after(0, lambda: self._on_restore_done(result))

        threading.Thread(target=_run, daemon=True).start()

    def _on_operation_done(self, result) -> None:
        """Finaliza la operación de respaldo + validación."""
        if result.status == OperationStatus.SUCCESS:
            self._dashboard.operation_finished(
                success=True, message="✔️ Prueba exitosa"
            )
            show_success(
                self,
                "Proceso completado",
                "El respaldo y la validación se completaron correctamente."
            )
        else:
            self._dashboard.operation_finished(
                success=False, message=f"❌ {result.error_message or 'Error'}"
            )
            show_error(
                self,
                "Error",
                f"El proceso falló:\n\n{result.error_message or 'Error desconocido'}"
            )

    def _on_restore_done(self, result) -> None:
        """Finaliza la restauración desde archivo."""
        if result.status == OperationStatus.SUCCESS:
            self._dashboard.operation_finished(
                success=True, message=f"✔️ Restauración completada: {result.sandbox_database}"
            )
            show_success(
                self,
                "Restauración completada",
                f"Base de datos restaurada como:\n{result.sandbox_database}"
            )
        elif result.status == OperationStatus.CANCELLED:
            self._dashboard.operation_finished(
                success=False, message="⚠️ Restauración cancelada"
            )
            show_warning(
                self,
                "Restauración cancelada",
                result.error_message or "La base de datos ya existe."
            )
        else:
            self._dashboard.operation_finished(
                success=False, message="❌ Error al restaurar"
            )
            show_error(
                self,
                "Error",
                f"La restauración falló:\n\n{result.error_message or 'Error desconocido'}"
            )

    # ------------------------------------------------------------------
    # Callbacks de UI desde hilos
    # ------------------------------------------------------------------

    def _ui_log_callback(self, level: str, message: str) -> None:
        """Recibe logs desde el logger y los reenvía al panel de actividad."""
        if hasattr(self, "_dashboard"):
            self.after(0, lambda: self._dashboard.append_log(level, message))
