"""Conexiones cortas, migraciones verificables y backups consistentes con WAL."""

from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import fcntl
import time
import os
from pathlib import Path
import sqlite3
from typing import Iterator
from uuid import uuid4

from app.domain.package_errors import StorageError

MIGRATIONS = Path(__file__).resolve().parent / "infrastructure" / "migrations"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Database:
    def __init__(self, path: Path, *, timeout_ms: int = 5000) -> None:
        self.path = path
        self.timeout_ms = timeout_ms

    @contextmanager
    def connection(self, *, read_only: bool = False) -> Iterator[sqlite3.Connection]:
        address=self.path.resolve().as_uri()+"?mode=ro" if read_only else str(self.path)
        connection = sqlite3.connect(address, uri=read_only, isolation_level=None, timeout=self.timeout_ms / 1000)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA busy_timeout={int(self.timeout_ms)}")
            connection.execute("PRAGMA synchronous=FULL")
            if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise StorageError("No se pudieron activar las claves foráneas.")
            yield connection
        finally:
            connection.close()

    def initialize(self, *, target_version: int | None = None) -> None:
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        lock_path=self.path.with_name(self.path.name+'.schema.lock')
        with lock_path.open('a') as lock:
            deadline=time.monotonic()+self.timeout_ms/1000
            while True:
                try:
                    fcntl.flock(lock.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic()>=deadline:
                        raise StorageError('Otra sesión está migrando el esquema. Espera y vuelve a abrir la aplicación.')
                    time.sleep(.05)
            try:
                self._initialize(target_version=target_version)
            finally:
                fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

    def _initialize(self, *, target_version: int | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        migrations = sorted(MIGRATIONS.glob("*.sql"))
        if [int(path.name.split('_',1)[0]) for path in migrations]!=list(range(1,len(migrations)+1)):
            raise StorageError('Las migraciones deben ser consecutivas y conservar sus nombres versionados.')
        latest = len(migrations) if target_version is None else target_version
        if not 1 <= latest <= len(migrations):
            raise StorageError("Versión de migración desconocida.")
        try:
            with self.connection() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
                connection.execute('BEGIN')
                installed = {row['version']: dict(row) for row in connection.execute("SELECT * FROM schema_migrations")}
                user_version = connection.execute("PRAGMA user_version").fetchone()[0]
                connection.rollback()
                if set(installed) != set(range(1, len(installed)+1)) or user_version != len(installed):
                    raise StorageError("El historial del esquema y user_version no coinciden.")
                if len(installed) > latest:
                    raise StorageError("La base requiere una versión más nueva de la aplicación; no se degrada.")
                for version, row in installed.items():
                    text = migrations[version-1].read_bytes()
                    if hashlib.sha256(text).hexdigest() != row['checksum']:
                        raise StorageError("Una migración aplicada fue modificada. Restaura su versión original.")
            if installed and len(installed) < latest:
                self.backup(self.path.parent / "backups" / f"before-schema-{latest}-{uuid4().hex}.sqlite3")
            with self.connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    if connection.execute('PRAGMA user_version').fetchone()[0]>latest:
                        raise StorageError('Otra versión migró la base. Esta aplicación no puede degradarla.')
                    for index, path in enumerate(migrations[:latest], 1):
                        if connection.execute("SELECT 1 FROM schema_migrations WHERE version=?", (index,)).fetchone():
                            continue
                        text = path.read_text(encoding="utf-8")
                        statement = ""
                        for line in text.splitlines(keepends=True):
                            statement += line
                            if sqlite3.complete_statement(statement):
                                connection.execute(statement)
                                statement = ""
                        if statement.strip():
                            raise StorageError("Migración SQL incompleta.")
                        connection.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (index, path.name, hashlib.sha256(path.read_bytes()).hexdigest(), utc_now()))
                        connection.execute(f"PRAGMA user_version={index}")
                    if connection.execute("PRAGMA foreign_key_check").fetchall():
                        raise StorageError("La migración no conserva las relaciones.")
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise
        except (sqlite3.DatabaseError, OSError) as exc:
            raise StorageError("No se pudo inicializar el almacenamiento. Los cambios del esquema se revirtieron.") from exc

    def backup(self, destination: Path) -> Path:
        if destination.exists() or destination.is_symlink():
            raise StorageError("El destino ya existe; no se sobrescribirá.")
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        staged = destination.parent / f".{uuid4().hex}.backup-tmp"
        try:
            descriptor = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            with self.connection(read_only=True) as source, closing(sqlite3.connect(staged)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or target.execute("PRAGMA foreign_key_check").fetchall():
                    raise StorageError("La copia no pasó la validación de integridad.")
            os.link(staged, destination)  # Publicación sin sobrescribir otra copia.
            return destination
        except (OSError, sqlite3.DatabaseError) as exc:
            raise StorageError("No se pudo completar el respaldo; no se modificó la base original.") from exc
        finally:
            if staged.exists():
                staged.unlink()


def restore_backup(source: Path, destination: Path) -> Path:
    if not source.is_file() or destination.exists() or any(Path(str(destination)+suffix).exists() for suffix in ('-wal','-shm')):
        raise StorageError("Restaura a una ruta nueva; la fuente debe ser una copia existente.")
    # No abrir una base inexistente ni escribir en el respaldo de origen.
    try:
        with closing(sqlite3.connect(source.as_uri()+"?mode=ro", uri=True)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or connection.execute("PRAGMA foreign_key_check").fetchall():
                raise StorageError("El respaldo no tiene integridad válida.")
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone():
                raise StorageError("El archivo no es un respaldo de YouTube Studio AI.")
        return Database(source).backup(destination)
    except sqlite3.DatabaseError as exc:
        raise StorageError("El archivo de respaldo no es una base válida.") from exc
