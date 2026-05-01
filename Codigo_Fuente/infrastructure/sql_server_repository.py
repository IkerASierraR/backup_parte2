"""
infrastructure/sql_server_repository.py
Implementación concreta del repositorio SQL Server usando pyodbc.
"""
import os
import re
import socket
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pyodbc

from domain.entities import (
    BackupResult,
    ConnectionConfig,
    LogicalFile,
    OperationStatus,
    RestoreResult,
    ValidationResult,
)
from domain.interfaces import IDatabaseRepository

# Controladores ODBC en orden de preferencia
ODBC_DRIVER_CANDIDATES: List[str] = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server",
]

# Timeout (segundos) usado exclusivamente para sondear la disponibilidad
# de un servidor.  Debe ser corto para evitar bloqueos en la UI.
_PROBE_TIMEOUT: int = 3

# SQLSTATE codes y fragmentos de mensaje que indican "driver no instalado".
# Se usan para diferenciar errores de driver de errores de red/autenticación.
_DRIVER_NOT_FOUND_INDICATORS: List[str] = [
    "im002",   # SQLSTATE: Data source name not found
    "im003",   # SQLSTATE: Specified driver could not be loaded
    "data source name not found",
    "driver not found",
]


class SqlServerRepository(IDatabaseRepository):
    """
    Implementación de IDatabaseRepository para SQL Server via pyodbc.
    Todas las conexiones son sin pool (se abren y cierran por operación)
    para evitar problemas de estado entre hilos.
    """

    # ------------------------------------------------------------------
    # Descubrimiento automático de servidores
    # ------------------------------------------------------------------

    @staticmethod
    def get_available_driver() -> str:
        """
        Devuelve el primer controlador ODBC de SQL Server disponible en
        el sistema.  Si no encuentra ninguno de los conocidos, devuelve
        el primero de la lista como valor por defecto.
        """
        installed = [d.lower() for d in pyodbc.drivers()]
        for driver in ODBC_DRIVER_CANDIDATES:
            if driver.lower() in installed:
                return driver
        # Buscar cualquier driver que contenga "sql server"
        for d in pyodbc.drivers():
            if "sql server" in d.lower():
                return d
        return ODBC_DRIVER_CANDIDATES[0]

    @staticmethod
    def _detect_instances_from_registry() -> List[str]:
        """
        Lee el registro de Windows para obtener las instancias de SQL Server
        instaladas localmente.  Devuelve una lista con los nombres de instancia
        (p. ej. ``['MSSQLSERVER', 'SQLEXPRESS']``).
        Si no se puede leer el registro (sistema no Windows u otro error)
        devuelve una lista vacía.
        """
        instances: List[str] = []
        try:
            import winreg  # Sólo disponible en Windows

            key_path = r"SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL"
            access_flags = [
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,  # type: ignore[attr-defined]
                winreg.KEY_READ,  # type: ignore[attr-defined]
            ]
            for flags in access_flags:
                try:
                    with winreg.OpenKey(  # type: ignore[attr-defined]
                        winreg.HKEY_LOCAL_MACHINE, key_path, 0, flags  # type: ignore[attr-defined]
                    ) as key:
                        i = 0
                        while True:
                            try:
                                name, _, _ = winreg.EnumValue(key, i)  # type: ignore[attr-defined]
                                instances.append(name)
                                i += 1
                            except OSError:
                                break
                    if instances:
                        break
                except OSError:
                    continue
        except Exception:
            pass
        return instances

    @staticmethod
    def discover_servers() -> List[str]:
        """
        Genera una lista ordenada de candidatos de servidor basada en el
        nombre del equipo local.

        Orden de prioridad:
        1. Instancia por defecto (``HOSTNAME``) — más habitual en Enterprise.
        2. ``HOSTNAME\\SQLEXPRESS`` — habitual en Express.
        3. Otras instancias detectadas desde el registro de Windows.
        4. Variantes ``localhost`` como último recurso.
        """
        hostname = socket.gethostname()
        seen: Dict[str, None] = {}  # dict ordenado como conjunto

        def _add(server: str) -> None:
            seen[server] = None

        # Primero las instancias detectadas en el registro (respetan orden real)
        registry_instances = SqlServerRepository._detect_instances_from_registry()
        for inst in registry_instances:
            if inst.upper() == "MSSQLSERVER":
                _add(hostname)          # instancia por defecto
            else:
                _add(rf"{hostname}\{inst}")

        # Añadir candidatos conocidos si aún no están
        for candidate in [
            hostname,
            rf"{hostname}\SQLEXPRESS",
            rf"{hostname}\MSSQLSERVER",
            r"localhost\SQLEXPRESS",
            "localhost",
            "(local)",
        ]:
            _add(candidate)

        return list(seen.keys())

    @classmethod
    def try_auto_connect(cls) -> Optional[ConnectionConfig]:
        """
        Intenta conectarse automáticamente con Autenticación Windows usando
        la lista de candidatos devuelta por ``discover_servers``.

        Todos los candidatos se sondean **en paralelo** con un timeout corto
        (``_PROBE_TIMEOUT`` segundos) para no bloquear la interfaz.  Se devuelve
        la configuración del candidato con mayor prioridad (índice más bajo) que
        haya respondido correctamente.

        Returns:
            ``ConnectionConfig`` si alguna conexión tuvo éxito; ``None`` si no.
        """
        candidates = cls.discover_servers()
        driver = cls.get_available_driver()
        results: Dict[int, ConnectionConfig] = {}
        lock = threading.Lock()

        def _probe(idx: int, server: str) -> None:
            config = ConnectionConfig(
                server=server,
                use_windows_auth=True,
                driver=driver,
            )
            try:
                conn = pyodbc.connect(
                    config.build_connection_string(),
                    autocommit=True,
                    timeout=_PROBE_TIMEOUT,
                )
                conn.cursor().execute("SELECT 1")
                conn.close()
                with lock:
                    results[idx] = config
            except Exception:
                pass

        threads = [
            threading.Thread(target=_probe, args=(i, srv), daemon=True)
            for i, srv in enumerate(candidates)
        ]
        for t in threads:
            t.start()
        # Esperar a que todos los hilos terminen (o a que transcurra el margen)
        join_timeout = _PROBE_TIMEOUT + 1
        for t in threads:
            t.join(timeout=join_timeout)

        if results:
            best_idx = min(results.keys())
            return results[best_idx]
        return None

    # ------------------------------------------------------------------
    # Conexión / Utilidades internas
    # ------------------------------------------------------------------

    def _connect(self, config: ConnectionConfig) -> pyodbc.Connection:
        """
        Abre una conexión y la retorna.

        Si el driver configurado en ``config`` no está disponible, intenta
        automáticamente los controladores de ``ODBC_DRIVER_CANDIDATES``.
        """
        last_exc: Optional[Exception] = None

        # Intentar primero con el driver del config; luego con los alternativos
        drivers_to_try = [config.driver] + [
            d for d in ODBC_DRIVER_CANDIDATES if d != config.driver
        ]
        for driver in drivers_to_try:
            try:
                conn_str = (
                    f"DRIVER={{{driver}}};"
                    f"SERVER={config.server};"
                    f"DATABASE={config.database};"
                    f"TrustServerCertificate={'yes' if config.trust_certificate else 'no'};"
                )
                if config.use_windows_auth:
                    conn_str += "Trusted_Connection=yes;"
                else:
                    conn_str += f"UID={config.username};PWD={config.password};"

                conn = pyodbc.connect(conn_str, autocommit=True, timeout=30)
                return conn
            except pyodbc.Error as exc:
                last_exc = exc
                err_msg = str(exc).lower()
                # Si el error es del driver (no encontrado), probar el siguiente
                if any(ind in err_msg for ind in _DRIVER_NOT_FOUND_INDICATORS):
                    continue
                # Cualquier otro error (host no alcanzable, autenticación…) se
                # propaga inmediatamente para no enmascararlo.
                raise

        raise last_exc or pyodbc.Error("No se encontró un controlador ODBC compatible.")

    def _execute_scalar(self, config: ConnectionConfig, query: str) -> any:
        """Ejecuta una consulta y retorna el primer campo del primer resultado."""
        with self._connect(config) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None

    # ------------------------------------------------------------------
    # IDatabaseRepository — implementaciones
    # ------------------------------------------------------------------

    def test_connection(self, config: ConnectionConfig) -> bool:
        """Prueba la conexión a SQL Server."""
        try:
            with self._connect(config) as conn:
                conn.cursor().execute("SELECT 1")
            return True
        except pyodbc.Error:
            return False

    def validate_permissions(self, config: ConnectionConfig) -> bool:
        """Verifica rol sysadmin."""
        try:
            result = self._execute_scalar(
                config, "SELECT IS_SRVROLEMEMBER('sysadmin')"
            )
            return result == 1
        except pyodbc.Error:
            return False

    def list_databases(self, config: ConnectionConfig) -> List[str]:
        """Lista bases de datos excluyendo las del sistema y sandboxes previos."""
        query = """
            SELECT name
            FROM sys.databases
            WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
              AND name NOT LIKE '%_SAFEBRIDGE_%'
              AND state_desc = 'ONLINE'
            ORDER BY name
        """
        with self._connect(config) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [row.name for row in cursor.fetchall()]

    def database_exists(self, config: ConnectionConfig, database_name: str) -> bool:
        """Verifica si una base de datos existe en el servidor (consulta parametrizada)."""
        try:
            with self._connect(config) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM sys.databases WHERE name = ?",
                    (database_name,),
                )
                return cursor.fetchone() is not None
        except pyodbc.Error:
            return False

    def get_default_backup_path(self, config: ConnectionConfig) -> str:
        """Obtiene la ruta de backup configurada en el servidor."""
        query = """
            SELECT SERVERPROPERTY('InstanceDefaultBackupPath')
        """
        try:
            path = self._execute_scalar(config, query)
            if path:
                return str(path)
        except pyodbc.Error:
            pass
        # Fallback: directorio de datos del servidor
        try:
            path = self._execute_scalar(
                config, "SELECT SERVERPROPERTY('InstanceDefaultDataPath')"
            )
            if path:
                return str(path)
        except pyodbc.Error:
            pass
        return "C:\\Backup"

    def execute_backup(
        self,
        config: ConnectionConfig,
        database_name: str,
        backup_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> BackupResult:
        """Ejecuta BACKUP DATABASE ... WITH INIT, FORMAT."""
        result = BackupResult(
            database_name=database_name,
            backup_path=backup_path,
            started_at=datetime.now(),
            status=OperationStatus.RUNNING,
        )
        try:
            if progress_callback:
                progress_callback(
                    f"Iniciando backup de '{database_name}' → {backup_path}"
                )

            sql = f"""
                BACKUP DATABASE [{database_name}]
                TO DISK = N'{backup_path}'
                WITH INIT, FORMAT,
                     NAME = N'{database_name} - Full Backup',
                     STATS = 10
            """
            with self._connect(config) as conn:
                conn.timeout = 0  # Sin timeout para operaciones largas
                cursor = conn.cursor()
                cursor.execute(sql)
                # STATS genera mensajes informativos; los capturamos
                while cursor.nextset():
                    pass

            result.finished_at = datetime.now()
            result.status = OperationStatus.SUCCESS

            # Obtener tamaño del archivo
            try:
                size = os.path.getsize(backup_path) / (1024 * 1024)
                result.file_size_mb = round(size, 2)
            except OSError:
                pass

            if progress_callback:
                progress_callback(
                    f"Backup completado en {result.duration_seconds:.1f}s"
                    + (
                        f" — {result.file_size_mb} MB"
                        if result.file_size_mb
                        else ""
                    )
                )

        except pyodbc.Error as exc:
            result.finished_at = datetime.now()
            result.status = OperationStatus.FAILED
            result.error_message = str(exc)
            if progress_callback:
                progress_callback(f"ERROR en backup: {exc}")

        return result

    def get_logical_files(
        self, config: ConnectionConfig, backup_path: str
    ) -> List[LogicalFile]:
        """Ejecuta RESTORE FILELISTONLY para obtener los archivos lógicos."""
        files: List[LogicalFile] = []
        sql = f"RESTORE FILELISTONLY FROM DISK = N'{backup_path}'"
        with self._connect(config) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                files.append(
                    LogicalFile(
                        logical_name=row.LogicalName,
                        physical_name=row.PhysicalName,
                        file_type=row.Type,  # 'D' o 'L'
                    )
                )
        return files

    def execute_restore(
        self,
        config: ConnectionConfig,
        backup_path: str,
        sandbox_name: str,
        data_path: str,
        log_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> RestoreResult:
        """Restaura el backup en la base sandbox."""
        result = RestoreResult(
            source_backup_path=backup_path,
            sandbox_database=sandbox_name,
            started_at=datetime.now(),
            status=OperationStatus.RUNNING,
        )
        try:
            if progress_callback:
                progress_callback(
                    f"Restaurando backup en sandbox '{sandbox_name}'"
                )

            logical_files = self.get_logical_files(config, backup_path)

            # Construir cláusulas MOVE
            move_clauses: List[str] = []
            for lf in logical_files:
                ext = ".mdf" if lf.file_type == "D" else ".ldf"
                dest = (
                    data_path if lf.file_type == "D" else log_path
                )
                target = os.path.join(dest, f"{sandbox_name}{ext}")
                move_clauses.append(
                    f"MOVE N'{lf.logical_name}' TO N'{target}'"
                )

            moves = ",\n     ".join(move_clauses)
            sql = f"""
                RESTORE DATABASE [{sandbox_name}]
                FROM DISK = N'{backup_path}'
                WITH {moves},
                     REPLACE,
                     STATS = 10
            """
            with self._connect(config) as conn:
                conn.timeout = 0
                cursor = conn.cursor()
                cursor.execute(sql)
                while cursor.nextset():
                    pass

            result.finished_at = datetime.now()
            result.status = OperationStatus.SUCCESS
            if progress_callback:
                progress_callback(
                    f"Restore completado en {result.duration_seconds:.1f}s"
                )

        except pyodbc.Error as exc:
            result.finished_at = datetime.now()
            result.status = OperationStatus.FAILED
            result.error_message = str(exc)
            if progress_callback:
                progress_callback(f"ERROR en restore: {exc}")

        return result

    def execute_checkdb(
        self,
        config: ConnectionConfig,
        database_name: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> ValidationResult:
        """Ejecuta DBCC CHECKDB y captura mensajes."""
        result = ValidationResult(
            database_name=database_name,
            started_at=datetime.now(),
            status=OperationStatus.RUNNING,
        )
        messages: List[str] = []

        if progress_callback:
            progress_callback(f"Ejecutando DBCC CHECKDB('{database_name}')")

        try:
            sql = f"DBCC CHECKDB(N'{database_name}') WITH NO_INFOMSGS, ALL_ERRORMSGS"
            with self._connect(config) as conn:
                conn.timeout = 0
                cursor = conn.cursor()
                # Capturar mensajes de SQL Server
                conn.add_output_converter(pyodbc.SQL_WVARCHAR, lambda x: x)

                cursor.execute(sql)
                # Iterar todos los resultsets (DBCC puede generar varios)
                while True:
                    try:
                        rows = cursor.fetchall()
                        for row in rows:
                            msg = " | ".join(str(v) for v in row if v is not None)
                            if msg:
                                messages.append(msg)
                    except pyodbc.ProgrammingError:
                        break
                    if not cursor.nextset():
                        break

            output = "\n".join(messages)
            result.checkdb_output = output

            # Analizar errores en la salida
            error_count = len(
                re.findall(r"\berror\b", output, re.IGNORECASE)
            )
            result.error_count = error_count
            result.finished_at = datetime.now()
            result.status = (
                OperationStatus.SUCCESS if error_count == 0 else OperationStatus.FAILED
            )

            if progress_callback:
                status_msg = "SIN ERRORES" if error_count == 0 else f"{error_count} ERRORES DETECTADOS"
                progress_callback(
                    f"DBCC CHECKDB finalizado: {status_msg} "
                    f"({result.duration_seconds:.1f}s)"
                )

        except pyodbc.Error as exc:
            result.finished_at = datetime.now()
            result.status = OperationStatus.FAILED
            result.error_message = str(exc)
            if progress_callback:
                progress_callback(f"ERROR en CHECKDB: {exc}")

        return result

    def drop_database(
        self, config: ConnectionConfig, database_name: str
    ) -> bool:
        """Elimina la base sandbox de forma segura."""
        try:
            # Primero poner en single user y luego eliminar
            sql_single = (
                f"ALTER DATABASE [{database_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
            )
            sql_drop = f"DROP DATABASE [{database_name}]"
            with self._connect(config) as conn:
                cursor = conn.cursor()
                cursor.execute(sql_single)
                cursor.execute(sql_drop)
            return True
        except pyodbc.Error:
            return False