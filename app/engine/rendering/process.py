"""Reused bounded FFmpeg process supervision and one global render slot."""

from contextlib import contextmanager
import fcntl
import io
import json
import math
import os
from pathlib import Path
import signal
import selectors
import subprocess
import tempfile
import time
from uuid import uuid4
from PIL import Image,ImageFont

from app.domain.package_errors import StudioError

class FFmpegProcess:
    def __init__(self,config,working: Path,lock_path: Path) -> None:
        self.config=config
        self.working=working
        self.lock_path=lock_path
        self.working.mkdir(parents=True,exist_ok=True)

    def probe_image(self,data: bytes) -> dict:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                if min(image.size)<128:
                    raise StudioError('La imagen es demasiado pequeña para el piloto.')
                return {'width':image.width,'height':image.height,'format':image.format}
        except (OSError,ValueError):
            raise StudioError('El proveedor no devolvió una imagen utilizable.') from None

    def probe(self,data: bytes,suffix: str) -> dict:
        with tempfile.TemporaryDirectory(prefix='studio-probe-') as temp:
            path=Path(temp)/('input'+suffix)
            path.write_bytes(data)
            return self._probe_path(path)

    def _probe_path(self,path: Path) -> dict:
        """Mide duración, streams y contenedor en una única llamada acotada."""
        try:
            process=subprocess.run([self.config.ffprobe,'-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,timeout=30)
            if process.returncode:raise StudioError('ffprobe rechazó un archivo audiovisual.')
            data=json.loads(process.stdout)
            duration=float(data['format']['duration'])
            if not math.isfinite(duration) or duration<=0:raise StudioError('El medio no tiene una duración válida.')
            return {'duration':duration,'size_bytes':path.stat().st_size,'streams':data['streams'],'container':data['format'].get('format_name','')}
        except (OSError,ValueError,KeyError,subprocess.TimeoutExpired):
            raise StudioError('No se pudo comprobar el archivo con ffprobe.') from None

    @contextmanager
    def render_slot(self,guard):
        self.lock_path.parent.mkdir(parents=True,exist_ok=True)
        with self.lock_path.open('a') as lock:
            while True:
                guard()
                try:
                    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except BlockingIOError:time.sleep(.2)
            try:yield
            finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

    def _run(self,args: list[str],guard,progress,total: float,offset: float = 0.) -> None:
        command=[self.config.ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y',*args,'-progress','pipe:1','-nostats']
        log_path=self.working/('ffmpeg-'+uuid4().hex+'.json')
        log_path.write_text(json.dumps({'command':command,'state':'started'}))
        with tempfile.TemporaryFile() as errors:
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors,start_new_session=True)
            selector=selectors.DefaultSelector()
            selector.register(process.stdout,selectors.EVENT_READ)
            last_report=-1.0
            pending=''
            try:
                while True:
                    guard()
                    if not selector.select(timeout=.25):
                        continue
                    chunk=os.read(process.stdout.fileno(),65536)
                    if not chunk:
                        break
                    pending+=chunk.decode('utf-8','replace')
                    while '\n' in pending:
                        line,pending=pending.split('\n',1)
                        key,_,value=line.strip().partition('=')
                        if key=='out_time_us' and value.lstrip('-').isdigit():
                            seconds=offset+max(0,int(value))/1_000_000
                            if seconds-last_report>=2 or seconds>=total:
                                progress({'encoded_seconds':min(seconds,total),'total_seconds':total,'percent':min(100,round(seconds/total*100,1))})
                                last_report=seconds
                process.wait(timeout=30)
                errors.seek(0)
                log_path.write_text(json.dumps({'command':command,'returncode':process.returncode,'stderr':errors.read().decode('utf-8','replace')[-4000:]}))
                if process.returncode:
                    errors.seek(0)
                    # stderr permanece local; no contiene headers de proveedores ni comandos de shell.
                    log=errors.read().decode('utf-8','replace')[-4000:]
                    (self.working/('ffmpeg-error-'+uuid4().hex+'.log')).write_text(log)
                    raise StudioError('FFmpeg no pudo terminar. Diagnóstico conservado en '+str(log_path))
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL)
                        process.wait()
                raise
            finally:
                selector.close()
                process.stdout.close()

    @staticmethod
    def _font(size: int):
        for path in ('/System/Library/Fonts/Supplemental/Arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
            if Path(path).is_file():return ImageFont.truetype(path,size)
        return ImageFont.load_default(size=size)



def probe_path(path: Path, ffprobe: str = 'ffprobe') -> dict:
    from types import SimpleNamespace
    return FFmpegProcess(SimpleNamespace(ffprobe=ffprobe),path.parent,path.parent/'unused.lock')._probe_path(path)
