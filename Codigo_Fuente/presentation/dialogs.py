"""
presentation/dialogs.py
Ventanas emergentes simples para mostrar información al usuario.
"""
import customtkinter as ctk
from shared.config import (
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
    UI_FONT_SIZE_NORMAL,
    UI_FONT_SIZE_SMALL,
)


def show_info(parent, title: str, message: str) -> None:
    """Muestra una ventana emergente informativa."""
    _show_dialog(parent, title, message, "ℹ️", COLOR_INFO)


def show_success(parent, title: str, message: str) -> None:
    """Muestra una ventana emergente de éxito."""
    _show_dialog(parent, title, message, "✔️", COLOR_SUCCESS)


def show_warning(parent, title: str, message: str) -> None:
    """Muestra una ventana emergente de advertencia."""
    _show_dialog(parent, title, message, "⚠️", COLOR_WARNING)


def show_error(parent, title: str, message: str) -> None:
    """Muestra una ventana emergente de error."""
    _show_dialog(parent, title, message, "❌", COLOR_ERROR)


def ask_yes_no(parent, title: str, message: str) -> bool:
    """
    Muestra una ventana emergente con opción Sí/No.
    Retorna True si el usuario elige Sí, False si elige No.
    """
    result = {"value": False}
    
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("400x200")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    
    # Centrar en el padre
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
    y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
    dialog.geometry(f"+{x}+{y}")
    
    dialog.grid_columnconfigure(0, weight=1)
    
    # Icono
    ctk.CTkLabel(
        dialog,
        text="⚠️",
        font=ctk.CTkFont(size=40),
    ).grid(row=0, column=0, pady=(20, 10))
    
    # Mensaje
    ctk.CTkLabel(
        dialog,
        text=message,
        font=ctk.CTkFont(size=UI_FONT_SIZE_NORMAL),
        wraplength=350,
    ).grid(row=1, column=0, padx=20, pady=(0, 20))
    
    # Botones
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.grid(row=2, column=0, pady=(0, 20))
    
    def _on_yes():
        result["value"] = True
        dialog.destroy()
    
    def _on_no():
        result["value"] = False
        dialog.destroy()
    
    ctk.CTkButton(
        btn_frame,
        text="Sí",
        width=100,
        command=_on_yes,
    ).pack(side="left", padx=10)
    
    ctk.CTkButton(
        btn_frame,
        text="No",
        width=100,
        fg_color="transparent",
        border_width=1,
        command=_on_no,
    ).pack(side="left", padx=10)
    
    dialog.wait_window()
    return result["value"]


def _show_dialog(parent, title: str, message: str, icon: str, color: str) -> None:
    """Crea y muestra una ventana emergente genérica."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("400x220")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    
    # Centrar en el padre
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
    y = parent.winfo_y() + (parent.winfo_height() - 220) // 2
    dialog.geometry(f"+{x}+{y}")
    
    dialog.grid_columnconfigure(0, weight=1)
    
    # Icono
    ctk.CTkLabel(
        dialog,
        text=icon,
        font=ctk.CTkFont(size=40),
    ).grid(row=0, column=0, pady=(20, 10))
    
    # Mensaje
    ctk.CTkLabel(
        dialog,
        text=message,
        font=ctk.CTkFont(size=UI_FONT_SIZE_NORMAL),
        wraplength=350,
    ).grid(row=1, column=0, padx=20, pady=(0, 20))
    
    # Botón cerrar
    ctk.CTkButton(
        dialog,
        text="Aceptar",
        width=100,
        command=dialog.destroy,
    ).grid(row=2, column=0, pady=(0, 20))
    
    dialog.wait_window()