from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from application.orchestrator import BackupOrchestrator
from application.restore_backup_use_case import RestoreBackupUseCase
from domain.entities import ConnectionConfig
from infrastructure.sql_server_repository import SqlServerRepository
from shared.logger import UILogger, build_session_id

app = FastAPI(title="SQL-SafeBridge API", version="1.0.0")
repo = SqlServerRepository()


def _serialize_result(result: Any) -> Dict[str, Any]:
    payload = result.__dict__.copy()
    for k, v in list(payload.items()):
        if hasattr(v, "value"):
            payload[k] = v.value
        elif isinstance(v, datetime):
            payload[k] = v.isoformat()
        elif hasattr(v, "__dict__"):
            payload[k] = _serialize_result(v)
    return payload


class ConnectionPayload(BaseModel):
    server: str
    username: str = ""
    password: str = ""
    use_windows_auth: bool = False

    def to_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            server=self.server,
            username=self.username,
            password=self.password,
            use_windows_auth=self.use_windows_auth,
        )


class BackupPayload(ConnectionPayload):
    database_name: str
    backup_directory: str


class RestorePayload(ConnectionPayload):
    backup_file: str
    target_database: Optional[str] = None
    force: bool = False


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/servers")
def servers() -> Dict[str, List[str]]:
    return {"servers": SqlServerRepository.discover_servers()}


@app.post("/connect")
def connect(payload: ConnectionPayload) -> Dict[str, Any]:
    config = payload.to_config()
    if not repo.test_connection(config):
        raise HTTPException(status_code=400, detail="No se pudo conectar al servidor")
    if not repo.validate_permissions(config):
        raise HTTPException(status_code=403, detail="Permisos insuficientes: se requiere sysadmin")

    return {
        "databases": repo.list_databases(config),
        "default_backup_path": repo.get_default_backup_path(config),
    }


@app.post("/backup")
def backup(payload: BackupPayload) -> Dict[str, Any]:
    config = payload.to_config()
    session_id = build_session_id(payload.database_name)
    logger = UILogger(session_id=session_id, ui_callback=lambda *_: None)
    orchestrator = BackupOrchestrator(repository=repo, logger=logger)
    result = orchestrator.run(config, payload.database_name, payload.backup_directory)
    logger.save_json()
    return _serialize_result(result)


@app.post("/restore")
def restore(payload: RestorePayload) -> Dict[str, Any]:
    config = payload.to_config()
    session_id = build_session_id("restore_backup")
    logger = UILogger(session_id=session_id, ui_callback=lambda *_: None)
    use_case = RestoreBackupUseCase(repository=repo, logger=logger)
    default_path = repo.get_default_backup_path(config)
    result = use_case.execute(
        config=config,
        backup_file=payload.backup_file,
        data_directory=default_path,
        log_directory=default_path,
        target_database=payload.target_database,
        force=payload.force,
    )
    logger.save_json()
    return _serialize_result(result)
