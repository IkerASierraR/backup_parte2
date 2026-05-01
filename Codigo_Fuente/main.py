"""
main.py
Punto de entrada de SQL-SafeBridge.

Verifica e instala automáticamente las dependencias requeridas antes de
arrancar la interfaz gráfica.
"""
import importlib
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Auto-instalador de dependencias
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES = {
    "pyodbc": "pyodbc>=4.0.39",
    "customtkinter": "customtkinter>=5.2.0",
}


def _ensure_dependencies() -> None:
    """
    Verifica que todas las dependencias estén instaladas.
    Si alguna falta, la instala automáticamente usando uv o pip.
    """
    missing = []
    missing_specs = []
    for module_name, pip_spec in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
            missing_specs.append(pip_spec)

    if not missing:
        return

    print(
        f"[SQL-SafeBridge] Las siguientes dependencias no están instaladas: "
        f"{', '.join(missing)}\n"
        "Se procederá a instalarlas automáticamente."
    )
    
    # Intentar primero con uv (más moderno y rápido)
    try:
        subprocess.check_call(
            ["uv", "pip", "install"] + missing_specs
        )
        print("[SQL-SafeBridge] Dependencias instaladas correctamente con uv.")
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        # uv no está disponible o falló, intentar con pip
        pass
    
    # Intentar con pip (método tradicional)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing_specs
        )
        print("[SQL-SafeBridge] Dependencias instaladas correctamente con pip.")
        return
    except subprocess.CalledProcessError:
        # pip falló, posiblemente por entorno gestionado externamente
        pass
    
    # Último intento: pip con --break-system-packages
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--break-system-packages", "--quiet"] + missing_specs
        )
        print("[SQL-SafeBridge] Dependencias instaladas correctamente con pip (--break-system-packages).")
        return
    except subprocess.CalledProcessError as exc:
        print(
            f"[SQL-SafeBridge] ERROR al instalar dependencias: {exc}\n"
            "Por favor instálalas manualmente:\n"
            f"  pip install {' '.join(missing_specs)}"
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Bootstrap de la aplicación
# ---------------------------------------------------------------------------

def main() -> None:
    """Función principal de arranque."""
    _ensure_dependencies()

    # Las importaciones se hacen después de garantizar que las libs existen
    from presentation.app_controller import AppController

    app = AppController()
    app.mainloop()


if __name__ == "__main__":
    # Asegurarse de que el directorio del proyecto esté en sys.path
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    main()