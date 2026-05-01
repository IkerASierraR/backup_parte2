# 🗄️ SQL-SafeBridge

**SQL-SafeBridge** es una aplicación de escritorio para Windows que automatiza el ciclo completo de respaldo y validación de bases de datos SQL Server: genera un backup FULL, lo restaura en una base sandbox aislada, ejecuta `DBCC CHECKDB` para verificar su integridad y, finalmente, elimina la sandbox automáticamente. Todo desde una interfaz gráfica moderna.

> Versión: **1.0.0**

---

## Tabla de contenidos

1. [Características](#características)
2. [Arquitectura](#arquitectura)
3. [Requisitos previos](#requisitos-previos)
4. [Instalación](#instalación)
5. [Uso](#uso)
   - [Iniciar la aplicación](#iniciar-la-aplicación)
   - [Pantalla de login](#pantalla-de-login)
   - [Dashboard principal](#dashboard-principal)
   - [Flujo de backup y validación](#flujo-de-backup-y-validación)
   - [Restaurar un archivo .bak](#restaurar-un-archivo-bak)
6. [Estructura del proyecto](#estructura-del-proyecto)
7. [Módulos](#módulos)
   - [domain](#domain)
   - [application](#application)
   - [infrastructure](#infrastructure)
   - [presentation](#presentation)
   - [shared](#shared)
8. [Logging](#logging)
9. [Configuración](#configuración)
10. [Dependencias](#dependencias)
11. [Preguntas frecuentes](#preguntas-frecuentes)

---

## Características

| Funcionalidad | Descripción |
|---|---|
| **Auto-detección de servidor** | Detecta instancias SQL Server del equipo local mediante el registro de Windows y sondeo de red |
| **Autenticación Windows / SQL Server** | Compatible con ambos modos de autenticación |
| **Backup FULL automático** | Genera un archivo `.bak` con marca de tiempo (`<BD>_YYYYMMDD_HHMMSS_FULL.bak`) |
| **Restore a sandbox** | Restaura el backup en una base temporal aislada (`<BD>_SAFEBRIDGE_<timestamp>`) |
| **DBCC CHECKDB** | Valida la integridad completa de la sandbox |
| **Limpieza automática** | Elimina la base sandbox al finalizar la validación |
| **Restauración directa** | Permite restaurar cualquier archivo `.bak` externo a una base de datos nueva |
| **Logging dual** | Genera registros en texto plano (`.log`) y JSON estructurado (`.json`) |
| **Interfaz gráfica** | UI oscura y moderna con CustomTkinter; barra de progreso y panel de actividad en tiempo real |
| **Auto-instalación de dependencias** | Si `pyodbc` o `customtkinter` no están instalados, el arranque los instala automáticamente |

---

## Arquitectura

SQL-SafeBridge sigue **Clean Architecture** (también conocida como arquitectura hexagonal/puertos y adaptadores):

```
┌─────────────────────────────────────────────────────┐
│                   Presentation                       │
│  LoginScreen  ·  DashboardScreen  ·  AppController  │
└────────────────────────┬────────────────────────────┘
                         │ llama a
┌────────────────────────▼────────────────────────────┐
│                   Application                        │
│  BackupOrchestrator  ·  BackupUseCase               │
│  RestoreUseCase  ·  ValidationUseCase               │
│  RestoreBackupUseCase                               │
└────────────────────────┬────────────────────────────┘
                         │ usa interfaces de
┌────────────────────────▼────────────────────────────┐
│                    Domain                            │
│  Entities (BackupResult, RestoreResult, …)          │
│  Interfaces (IDatabaseRepository, ILogger)          │
└────────────────────────┬────────────────────────────┘
                         │ implementadas por
┌────────────────────────▼────────────────────────────┐
│                 Infrastructure                       │
│  SqlServerRepository  (pyodbc)                      │
└─────────────────────────────────────────────────────┘
```

La capa de **dominio** no depende de ninguna otra; la capa de **infraestructura** es el único sitio donde se usa `pyodbc`.

---

## Requisitos previos

| Requisito | Versión mínima |
|---|---|
| Python | 3.10 + |
| SQL Server | 2017 + (cualquier edición, incluida Express) |
| Controlador ODBC | ODBC Driver 17/18 for SQL Server (o el controlador genérico "SQL Server") |
| Sistema operativo | Windows 10/11 (la auto-detección de instancias usa el registro de Windows) |

> **Nota:** El usuario de SQL Server con el que se conecta la aplicación debe tener el rol **sysadmin**, ya que las operaciones de backup, restore y DBCC CHECKDB lo requieren.

---

## Instalación

### 1. Clonar o descargar el repositorio

```bash
git clone https://github.com/IkerASierraR/cf-de-backup.git
cd cf-de-backup/SQL_SAFEBRIDGE
```

### 2. (Opcional) Crear un entorno virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instalar dependencias manualmente

```bash
pip install pyodbc>=4.0.39 customtkinter>=5.2.0
```

> Si no realizas este paso, la aplicación intentará instalarlas automáticamente al arrancar usando `uv` (si está disponible) o `pip`.

### 4. Instalar el controlador ODBC

Descarga e instala el **Microsoft ODBC Driver 18 for SQL Server** desde:  
[https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)

---

## Uso

### Iniciar la aplicación

Desde la carpeta `SQL_SAFEBRIDGE`:

```bash
python main.py
```

### Pantalla de login

Al iniciar, SQL-SafeBridge intenta **conectarse automáticamente** al SQL Server local usando Autenticación Windows. Durante ese proceso:

- Se muestra un mensaje de estado (`🔍 Detectando servidor SQL Server automáticamente…`).
- El desplegable *Servidor SQL Server* se rellena con las instancias detectadas.
- Si la conexión automática tiene éxito, se salta directamente al dashboard.
- Si falla, se muestra un aviso y el usuario puede conectarse manualmente.

**Opciones de autenticación:**

| Modo | Cuándo usarlo |
|---|---|
| **Windows (recomendado)** | El usuario de Windows tiene acceso a SQL Server; no se necesita usuario/contraseña |
| **SQL Server** | Se especifican usuario (p. ej. `sa`) y contraseña |

### Dashboard principal

El dashboard muestra:

- **Servidor y usuario** conectados.
- Selector de **base de datos** (lista obtenida del servidor).
- Campo de **ruta de backup** (ruta predeterminada de SQL Server o carpeta personalizable).
- Botón **▶ Ejecutar respaldo y validación**.
- Botón **📂 Restaurar desde .bak**.
- **Barra de progreso** y **panel de actividad** con logs en tiempo real.
- Botón de **cerrar sesión**.

### Flujo de backup y validación

Al pulsar **▶ Ejecutar respaldo y validación**, el orquestador ejecuta estas fases en orden:

```
1. Verificar conexión
2. Verificar permisos (rol sysadmin)
3. BACKUP FULL  →  <ruta>/<BD>_YYYYMMDD_HHMMSS_FULL.bak
4. RESTORE      →  <BD>_SAFEBRIDGE_<timestamp>  (base sandbox)
5. DBCC CHECKDB →  sobre la base sandbox
6. DROP DATABASE →  elimina la sandbox
```

Al finalizar se muestra un diálogo de éxito (✔️) o error (❌) y los logs quedan guardados en `logs/`.

### Restaurar un archivo .bak

Pulsando **📂 Restaurar desde .bak** se abre un selector de archivos. Una vez elegido el `.bak`:

- Si no se especifica un nombre destino, se genera automáticamente (`<nombre_archivo>_SAFEBRIDGE_<timestamp>`).
- Si la base de datos destino ya existe, se solicita confirmación para sobreescribirla.
- El resultado queda en el servidor SQL Server y los logs en `logs/`.

---

## Estructura del proyecto

```
cf-de-backup/
└── SQL_SAFEBRIDGE/
    ├── main.py                          # Punto de entrada
    ├── requirements.txt
    ├── logs/                            # Logs generados en tiempo de ejecución
    │
    ├── domain/
    │   ├── entities.py                  # Entidades y enumeraciones del dominio
    │   └── interfaces.py               # Contratos (puertos) abstractos
    │
    ├── application/
    │   ├── orchestrator.py             # Orquestador principal del flujo completo
    │   ├── backup_use_case.py          # Caso de uso: BACKUP FULL
    │   ├── restore_use_case.py         # Caso de uso: RESTORE a sandbox
    │   ├── restore_backup_use_case.py  # Caso de uso: RESTORE desde .bak externo
    │   └── validation_use_case.py      # Caso de uso: DBCC CHECKDB
    │
    ├── infrastructure/
    │   └── sql_server_repository.py    # Implementación pyodbc de IDatabaseRepository
    │
    ├── presentation/
    │   ├── app_controller.py           # Ventana raíz y navegación entre pantallas
    │   ├── login_screen.py             # Pantalla de login con auto-detección
    │   ├── dashboard_screen.py         # Panel de control principal
    │   └── dialogs.py                  # Diálogos de información/error/confirmación
    │
    └── shared/
        ├── config.py                   # Constantes globales y configuración
        └── logger.py                   # UILogger (archivo .log + .json + callback UI)
```

---

## Módulos

### domain

| Archivo | Contenido |
|---|---|
| `entities.py` | `OperationStatus`, `ConnectionConfig`, `BackupResult`, `RestoreResult`, `ValidationResult`, `OrchestrationResult`, `LogicalFile` |
| `interfaces.py` | `IDatabaseRepository` (contrato de repositorio), `ILogger` (contrato de logger) |

### application

| Clase | Responsabilidad |
|---|---|
| `BackupOrchestrator` | Coordina el flujo completo: conexión → permisos → backup → restore → checkdb → drop |
| `BackupUseCase` | Genera nombre de fichero y ejecuta `BACKUP DATABASE … TO DISK` |
| `RestoreUseCase` | Construye el nombre sandbox y ejecuta `RESTORE DATABASE` |
| `ValidationUseCase` | Ejecuta `DBCC CHECKDB` y parsea el resultado |
| `RestoreBackupUseCase` | Restaura un `.bak` externo con opción de forzar sobreescritura |

### infrastructure

`SqlServerRepository` implementa `IDatabaseRepository` con `pyodbc`:

| Método | Acción SQL |
|---|---|
| `test_connection` | Abre y cierra una conexión |
| `validate_permissions` | `IS_SRVROLEMEMBER('sysadmin')` |
| `list_databases` | `SELECT name FROM sys.databases` |
| `database_exists` | `DB_ID(name) IS NOT NULL` |
| `execute_backup` | `BACKUP DATABASE … TO DISK` |
| `get_logical_files` | `RESTORE FILELISTONLY FROM DISK` |
| `execute_restore` | `RESTORE DATABASE … FROM DISK … WITH MOVE` |
| `execute_checkdb` | `DBCC CHECKDB(…)` |
| `drop_database` | `ALTER DATABASE … SET SINGLE_USER; DROP DATABASE` |
| `get_default_backup_path` | `SERVERPROPERTY('InstanceDefaultBackupPath')` |
| `discover_servers` | Registro de Windows + sondeo TCP |
| `try_auto_connect` | Prueba candidatos locales con Autenticación Windows |

### presentation

| Clase | Responsabilidad |
|---|---|
| `AppController` | Ventana raíz (`ctk.CTk`); gestiona navegación, threading y callbacks |
| `LoginScreen` | Formulario de conexión con auto-detección y selector de modo de auth |
| `DashboardScreen` | Panel de control: selección de BD, ruta, botones de acción, progreso y log |
| `dialogs` | Funciones `show_error`, `show_success`, `show_warning`, `ask_yes_no` |

### shared

| Archivo | Contenido destacado |
|---|---|
| `config.py` | `APP_NAME`, `APP_VERSION`, `SANDBOX_SUFFIX`, `OPERATION_TIMEOUT`, rutas por defecto de SQL Server, constantes de tema UI |
| `logger.py` | `UILogger`: escribe en `.log` (legible) y `.json` (estructurado) y notifica a la UI vía callback; `build_session_id` genera IDs únicos de sesión |

---

## Logging

Cada operación genera dos ficheros en `SQL_SAFEBRIDGE/logs/`:

| Fichero | Formato | Ejemplo |
|---|---|---|
| `<BD>_YYYYMMDD_HHMMSS.log` | Texto plano | `2024-06-15 10:32:05 [INFO] Backup exitoso — 1024.5 MB en 45.3s` |
| `<BD>_YYYYMMDD_HHMMSS.json` | JSON array | `[{"timestamp": "…", "level": "INFO", "message": "…"}, …]` |

Los niveles de log son: `DEBUG`, `INFO`, `WARNING`, `ERROR`.

---

## Configuración

Las constantes de configuración se encuentran en `shared/config.py`:

| Constante | Valor por defecto | Descripción |
|---|---|---|
| `APP_NAME` | `"SQL-SafeBridge"` | Nombre de la aplicación |
| `APP_VERSION` | `"1.0.0"` | Versión |
| `SANDBOX_SUFFIX` | `"SAFEBRIDGE"` | Sufijo para bases sandbox |
| `OPERATION_TIMEOUT` | `3600` | Tiempo máximo de espera (segundos) |
| `UI_THEME` | `"dark"` | Tema de la interfaz (`"dark"` / `"light"`) |
| `UI_COLOR_SCHEME` | `"blue"` | Esquema de color de CustomTkinter |
| `SQL_DEFAULT_DATA_PATH_WINDOWS` | `C:\Program Files\…\DATA` | Ruta de datos por defecto de SQL Server |
| `SQL_DEFAULT_BACKUP_PATH_WINDOWS` | `C:\Program Files\…\Backup` | Ruta de backup por defecto de SQL Server |

---

## Dependencias

| Paquete | Versión mínima | Uso |
|---|---|---|
| `pyodbc` | 4.0.39 | Conexión y operaciones contra SQL Server |
| `customtkinter` | 5.2.0 | Interfaz gráfica moderna |

Ambas se instalan automáticamente si no están presentes al arrancar `main.py`.

---

## Preguntas frecuentes

**¿Por qué necesito rol sysadmin?**  
Las operaciones `BACKUP DATABASE`, `RESTORE DATABASE` y `DBCC CHECKDB` requieren permisos elevados en SQL Server. El rol `sysadmin` garantiza acceso completo a estas operaciones.

**¿La sandbox se elimina automáticamente?**  
Sí. Al finalizar `DBCC CHECKDB`, el orquestador ejecuta `DROP DATABASE` sobre la base sandbox. Si el drop falla (por ejemplo, porque hay conexiones activas), se registra una advertencia en el log pero la operación de validación no se marca como fallida.

**¿Puedo usar SQL Server Express?**  
Sí, siempre que el usuario tenga permisos sysadmin. Ten en cuenta que SQL Server Express tiene un límite de 10 GB por base de datos.

**¿La aplicación funciona en Linux/macOS?**  
La auto-detección de instancias usa el registro de Windows, por lo que esa funcionalidad no estará disponible. Sin embargo, si se proporciona manualmente el nombre del servidor, las operaciones de backup/restore/validación deberían funcionar si el controlador ODBC está instalado.

**¿Dónde se guardan los backups?**  
En la ruta que se indique en el campo *Ruta de backup* del dashboard. Por defecto se usa la ruta predeterminada de SQL Server (`SERVERPROPERTY('InstanceDefaultBackupPath')`).

**¿Cómo cambio el tema de la interfaz?**  
Modifica `UI_THEME` en `shared/config.py` a `"light"` para el tema claro.
