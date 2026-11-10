"""Publish one immutable input per import; failures remove only the folder we created."""

from pathlib import Path
import shutil
from uuid import uuid4

from app.files import atomic_new
from app.engine.domain.serialization import digest,encoded
from app.domain.package_errors import StudioError
from app.engine.ingestion.zip_reader import ZipReader


class PackageImporter:
    def __init__(self,settings,repository,reader: ZipReader | None=None):
        self.settings,self.repository,self.reader=settings,repository,reader or ZipReader()

    def import_zip(self,source: Path) -> str:
        checksum=digest(source.read_bytes());project=str(uuid4())
        base=self.settings.imports_root/project
        self.settings.safe(str(base.relative_to(self.settings.project_root)))
        created=False
        try:
            with self.reader.inspect(source,self.settings.temporary_root) as result:
                base.mkdir(parents=True,exist_ok=False);created=True
                shutil.copytree(result.root,base/'input')
                shutil.copyfile(source,base/'original.zip')
                if digest((base/'original.zip').read_bytes())!=checksum:raise StudioError('El ZIP cambió durante la importación.')
                atomic_new(base/'canonical.json',encoded(result.manifest))
                atomic_new(base/'receipt.json',encoded({'project_id':project,'zip_sha256':checksum,'canonical_sha256':digest(encoded(result.manifest)),'warnings':result.warnings}))
                for file in base.rglob('*'):
                    if file.is_file():file.chmod(0o444)
                language=result.manifest['language']
                voice={'voice':'am_michael' if language=='en-US' else 'ef_dora','speed':.95,'pronunciation':{}}
                if language=='en-US' and hasattr(self.repository,'channel_voice'):
                    voice=self.repository.channel_voice(result.manifest['channel_id']) or voice
                self.repository.add_package(project,result.manifest,str(base.relative_to(self.settings.project_root)),checksum,result.warnings,voice)
            return project
        except BaseException:
            if created:shutil.rmtree(base)
            raise
