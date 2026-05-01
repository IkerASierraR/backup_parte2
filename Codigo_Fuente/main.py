"""Entrada de backend para SQL-SafeBridge (modo API para Electron)."""
import subprocess
import sys


def main() -> None:
    cmd = [sys.executable, "-m", "uvicorn", "api_server:app", "--host", "127.0.0.1", "--port", "8765"]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
