"""Compose the single Work-package workflow; no editorial generation or paid SDKs."""

import json

from app.config import Settings
from app.storage import Database,utc_now
from app.engine.audio.kokoro import KokoroSpeech
from app.engine.ingestion.importer import PackageImporter
from app.engine.pipeline.cache import ContentCache
from app.engine.pipeline.executor import ProductionExecutor
from app.engine.pipeline.service import WorkStudio
from app.engine.pipeline.sqlite_store import SqliteWorkStore
from app.engine.timing.whisper import WhisperCppAlignment


def prepare_storage(settings: Settings) -> Database:
    """Aplica migraciones y carga el catálogo solo en un espacio vacío."""
    database=Database(settings.database_path);database.initialize()
    # Preserve the canonical catalogue; JSON is used only on a genuinely empty workspace.
    with database.connection() as c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute('SELECT 1 FROM channels LIMIT 1').fetchone():
            path=settings.project_root/'config/canales.json'
            if path.is_file():
                value=json.loads(path.read_text());now=utc_now()
                for index,channel in enumerate(value.get('channels',[])):
                    c.execute('INSERT INTO channels VALUES (?,?,?,?,?,?,?,?,?)',(channel['id'],channel['name'],'',channel['category'],'en-US','US','active',now,now))
                    c.execute('INSERT INTO channel_storage VALUES (?,?,?,?,?,?)',(channel['id'],channel.get('color','#72b9a8'),'canales/'+channel['folder'].removeprefix('canales/')+'/REGISTRO_MAESTRO.md',index,None,None))
        c.commit()
    return database


def create_studio(settings: Settings | None=None) -> WorkStudio:
    """Ensambla servicios locales existentes sin realizar generación multimedia."""
    settings=settings or Settings();store=SqliteWorkStore(prepare_storage(settings))
    speech=KokoroSpeech(settings.project_root)
    return WorkStudio(settings,store,store,PackageImporter(settings,store),speech)


def create_executor(settings: Settings,store: SqliteWorkStore) -> ProductionExecutor:
    """Conserva el ensamblaje del worker histórico para compatibilidad."""
    aligner=WhisperCppAlignment(settings.project_root/'data/models/whisper/model.bin',str(settings.project_root/'data/tools/whisper/build/bin/whisper-cli'))
    return ProductionExecutor(settings,store,ContentCache(settings.cache_root),KokoroSpeech(settings.project_root),aligner)

