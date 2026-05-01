"""
presentation/login_screen.py
Pantalla de login: auto-detección del servidor, Autenticación Windows (por
defecto) o SQL Server, con banner de estado para el intento automático.
"""
import socket
import tkinter as tk
from typing import Callable, List

import customtkinter as ctk

from shared.config import (
    APP_NAME,
    APP_VERSION,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
    UI_FONT_SIZE_NORMAL,
    UI_FONT_SIZE_SMALL,
    UI_FONT_SIZE_TITLE,
)


class LoginScreen(ctk.CTkFrame):
    """
    Frame de inicio de sesión.

    Flujo:
    1. Al mostrar la pantalla se auto-rellena el campo servidor con el nombre
       del equipo local.
    2. El modo de autenticación predeterminado es Windows Authentication;
       al activar SQL Server Auth se revelan los campos de usuario/contraseña.
    3. Llama a ``on_login_success(server, username, password, use_windows_auth)``
       cuando el usuario pulsa Conectar y los campos son válidos.
    """

    def __init__(
        self,
        master,
        on_login_success: Callable[[str, str, str, bool], None],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_success = on_login_success
        self._hostname = socket.gethostname()
        self._build_ui()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construye los widgets de la pantalla de login."""
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        # Ícono de base de datos
        ctk.CTkLabel(
            self,
            text="🗄️",
            font=ctk.CTkFont(size=64),
        ).grid(row=0, column=0, pady=(30, 4))

        # Título
        ctk.CTkLabel(
            self,
            text=APP_NAME,
            font=ctk.CTkFont(size=UI_FONT_SIZE_TITLE, weight="bold"),
        ).grid(row=1, column=0, pady=(0, 4))

        ctk.CTkLabel(
            self,
            text=f"v{APP_VERSION} — Gestión de Respaldos SQL Server",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=2, column=0, pady=(0, 20))

        # Banner de equipo detectado
        detected_frame = ctk.CTkFrame(self, fg_color="transparent")
        detected_frame.grid(row=3, column=0, pady=(0, 6))
        ctk.CTkLabel(
            detected_frame,
            text=f"🖥️  Equipo detectado: ",
            font=ctk.CTkFont(size=UI_FONT_SIZE_SMALL),
            text_color="gray",
        ).pack(side="left")
        ctk.CTkLabel(
            detected_frame,
            text=self._hostname,
            font=ctk.CTkFont(size=UI_FONT_SIZE_SMALL, weight="bold"),
            text_color=COLOR_INFO,
        ).pack(side="left")

        # Card central
        card = ctk.CTkFrame(self, corner_radius=16)
        card.grid(row=4, column=0, padx=60, pady=6, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # ── Servidor ────────────────────────────────────────────────
        ctk.CTkLabel(card, text="Servidor SQL Server", anchor="w").grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 2)
        )
        # Usar un ComboBox para que las sugerencias detectadas automáticamente
        # sean seleccionables desde el menú desplegable.
        self._server_entry = ctk.CTkComboBox(
            card,
            values=[
                self._hostname,
                rf"{self._hostname}\SQLEXPRESS",
            ],
            height=38,
        )
        # Pre-rellenar con la instancia por defecto (sin nombre de instancia)
        self._server_entry.set(self._hostname)
        self._server_entry.grid(row=1, column=0, sticky="ew", padx=20)

        # ── Modo de autenticación ────────────────────────────────────
        ctk.CTkLabel(card, text="Autenticación", anchor="w").grid(
            row=2, column=0, sticky="w", padx=20, pady=(14, 4)
        )
        auth_frame = ctk.CTkFrame(card, fg_color="transparent")
        auth_frame.grid(row=3, column=0, sticky="w", padx=20)

        self._auth_var = tk.StringVar(value="windows")
        ctk.CTkRadioButton(
            auth_frame,
            text="Windows (recomendado)",
            variable=self._auth_var,
            value="windows",
            command=self._on_auth_change,
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            auth_frame,
            text="SQL Server",
            variable=self._auth_var,
            value="sql",
            command=self._on_auth_change,
        ).pack(side="left")

        # ── Credenciales (SQL Server Auth) ───────────────────────────
        self._cred_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._cred_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self._cred_frame, text="Usuario", anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        self._user_entry = ctk.CTkEntry(
            self._cred_frame,
            placeholder_text="sa",
            height=38,
        )
        self._user_entry.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(self._cred_frame, text="Contraseña", anchor="w").grid(
            row=2, column=0, sticky="w", pady=(10, 2)
        )
        self._pwd_entry = ctk.CTkEntry(
            self._cred_frame,
            placeholder_text="••••••••",
            show="•",
            height=38,
        )
        self._pwd_entry.grid(row=3, column=0, sticky="ew")

        # El frame de credenciales se oculta por defecto (Windows Auth)
        # Se mostrará cuando el usuario elija SQL Server Auth
        self._cred_frame.grid(
            row=4, column=0, sticky="ew", padx=20, pady=(6, 0)
        )
        self._cred_frame.grid_remove()

        # ── Mensaje de error ─────────────────────────────────────────
        self._error_label = ctk.CTkLabel(
            card,
            text="",
            text_color=COLOR_ERROR,
            font=ctk.CTkFont(size=11),
            wraplength=340,
        )
        self._error_label.grid(row=5, column=0, pady=(8, 0))

        # ── Botón conectar ───────────────────────────────────────────
        self._connect_btn = ctk.CTkButton(
            card,
            text="Conectar",
            height=42,
            font=ctk.CTkFont(size=UI_FONT_SIZE_NORMAL, weight="bold"),
            command=self._on_connect,
        )
        self._connect_btn.grid(
            row=6, column=0, sticky="ew", padx=20, pady=(14, 20)
        )

        # Bind Enter en los campos de texto (el ComboBox del servidor no admite
        # bind de Return de la misma forma, así que sólo se enlaza en credenciales)
        for entry in (self._user_entry, self._pwd_entry):
            entry.bind("<Return>", lambda _e: self._on_connect())

    # ------------------------------------------------------------------
    # Cambio de modo de autenticación
    # ------------------------------------------------------------------

    def _on_auth_change(self) -> None:
        """Muestra u oculta los campos de credenciales según el modo elegido."""
        if self._auth_var.get() == "sql":
            self._cred_frame.grid()
        else:
            self._cred_frame.grid_remove()

    # ------------------------------------------------------------------
    # Acción del botón Conectar
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        """Valida campos y llama al callback de éxito."""
        server = self._server_entry.get().strip()
        use_windows_auth = self._auth_var.get() == "windows"

        if not server:
            self._show_error("El campo Servidor es obligatorio.")
            return

        username = ""
        password = ""
        if not use_windows_auth:
            username = self._user_entry.get().strip()
            password = self._pwd_entry.get()
            if not username:
                self._show_error("El campo Usuario es obligatorio.")
                return
            if not password:
                self._show_error("El campo Contraseña es obligatorio.")
                return

        self._error_label.configure(text="")
        self._connect_btn.configure(state="disabled", text="Conectando…")
        self.after(50, lambda: self._on_success(server, username, password, use_windows_auth))

    def _show_error(self, message: str) -> None:
        """Muestra un mensaje de error en el formulario."""
        self._error_label.configure(text=message)
        self._connect_btn.configure(state="normal", text="Conectar")

    def reset(self) -> None:
        """Restablece el estado del botón (útil si la conexión falla)."""
        self._connect_btn.configure(state="normal", text="Conectar")
        if self._auth_var.get() == "sql":
            self._pwd_entry.delete(0, tk.END)

    def show_auto_connect_status(self, message: str, color: str = "gray") -> None:
        """Muestra un mensaje de estado del intento de conexión automática."""
        self._error_label.configure(text=message, text_color=color)

    def set_server_suggestions(self, servers: List[str]) -> None:
        """
        Actualiza la lista desplegable del campo Servidor con los candidatos
        detectados automáticamente.  Si la lista no está vacía, establece el
        primer elemento como valor actual (mayor prioridad).
        """
        if not servers:
            return
        self._server_entry.configure(values=servers)
        # Seleccionar el candidato de mayor prioridad sólo si el campo aún
        # tiene el valor por defecto (hostname sin instancia) para no
        # sobreescribir lo que el usuario haya escrito manualmente.
        current = self._server_entry.get().strip()
        if current == self._hostname:
            self._server_entry.set(servers[0])
