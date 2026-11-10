"""Alineación experimental local comprobada contra el texto, sin repartir tiempos."""

import json
import os
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile
from dataclasses import replace

from app.engine.timing.alignment import AlignmentReview,WordTiming,validate_words,normalized_words
from app.domain.package_errors import NeedsReview
from app.engine.domain.languages import LANGUAGES
from app.domain.package_errors import StudioError as CapabilityUnavailable


class WhisperCppAlignment:
    def __init__(self,model: Path,executable: str='whisper-cli') -> None:
        self.model,self.executable=model,executable

    def _model(self, language: str) -> Path:
        if language not in LANGUAGES:raise CapabilityUnavailable('Idioma de alineación no compatible.')
        return self.model if language=='en-US' else self.model.parent.parent/'whisper-multilingual/model.bin'

    def available(self, language: str = 'en-US') -> bool:
        return bool(shutil.which(str(self.executable))) and self._model(language).is_file()

    def fingerprint(self, language: str = "en-US") -> str:
        from app.engine.domain.serialization import digest
        model=self._model(language)
        manifest=model.parent/'manifest.json'
        if not manifest.is_file():raise NeedsReview('Falta el manifiesto del modelo de alineación.')
        data=json.loads(manifest.read_text())
        if digest(model.read_bytes())!=data['sha256']:raise NeedsReview('El modelo de alineación no coincide con su hash.')
        return digest((data['sha256']+':observed-subwords-6-reference-boundaries-local-runtime').encode())

    @staticmethod
    def reference_boundaries(segments: list[dict], text: str, scene_id: str) -> list[WordTiming]:
        """Join observed subwords at exact reference boundaries; never split a timed token."""
        expected=[word for word in text.split() if normalized_words(word)]
        words=[];letters='';start=None;end=None
        for segment in segments:
            raw=segment['text'].strip()
            if not raw or raw.startswith('['):continue
            fragment=''.join(normalized_words(raw))
            if not fragment:continue
            if len(words)>=len(expected):raise NeedsReview('Sobran palabras reconocidas.')
            if start is None:start=segment['offsets']['from']/1000
            end=segment['offsets']['to']/1000;letters+=fragment
            target=''.join(normalized_words(expected[len(words)]))
            if not target.startswith(letters):raise NeedsReview('Un token observado no coincide con un límite del guion; necesita revisión.')
            if target==letters:
                words.append(WordTiming(expected[len(words)],start,end,scene_id));letters='';start=None
        if letters or len(words)!=len(expected):raise NeedsReview('Faltan palabras reconocidas para el guion.')
        return words

    def runtime_environment(self):
        """Resuelve dylibs junto al binario movido en macOS sin modificar el sistema."""
        env=dict(os.environ)
        binary=shutil.which(str(self.executable))
        if sys.platform=='darwin' and binary:
            folder=str(Path(binary).resolve().parent)
            env['DYLD_LIBRARY_PATH']=folder
        return env

    def align(self,audio: bytes,text: str,duration: float,scene_id: str, language: str = "en-US") -> list[WordTiming]:
        binary=shutil.which(str(self.executable))
        model=self._model(language)
        if not binary or not model.is_file():raise NeedsReview('whisper.cpp requiere un ejecutable y modelo local configurados; no se descargan automáticamente.')
        with tempfile.TemporaryDirectory(prefix='studio-alignment-') as folder:
            root=Path(folder);original=root/'source.wav';original.write_bytes(audio);source=root/'audio.wav';output=root/'result'
            try:
                conversion=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(original),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(source)],capture_output=True,timeout=30)
                if conversion.returncode:raise NeedsReview('No se pudo convertir el audio a PCM mono de 16 kHz para alineación.')
                result=subprocess.run([binary,'-m',str(model),'-f',str(source),'-l',LANGUAGES[language][2],'-t','2','-ml','1','-oj','-of',str(output)],capture_output=True,timeout=300,env=self.runtime_environment())
                if result.returncode:raise NeedsReview('whisper.cpp no pudo alinear el audio: '+result.stderr.decode('utf-8','replace')[-1200:])
                data=json.loads(output.with_suffix('.json').read_text())
                words=[]
                for segment in data['transcription']:
                    raw=segment['text'];token=raw.strip()
                    if not token or (token.startswith('[') and token.endswith(']')):continue
                    end=segment['offsets']['to']/1000
                    if not any(c.isalnum() for c in token):
                        # La puntuación no añade voz ni extiende el timestamp de la palabra.
                        if words:words[-1]=replace(words[-1],word=words[-1].word+token)
                        continue
                    if len(token.split())!=1:raise NeedsReview('La salida de whisper.cpp no está segmentada por palabras.')
                    if words and not raw[0].isspace():
                        words[-1]=replace(words[-1],word=words[-1].word+token,end_time=end)
                    else:words.append(WordTiming(token,segment['offsets']['from']/1000,end,scene_id))
                try:
                    exact=self.reference_boundaries(data['transcription'],text,scene_id)
                    return validate_words(exact,text,duration)
                except NeedsReview:
                    try:return validate_words(words,text,duration)
                    except NeedsReview as exc:raise AlignmentReview(str(exc),words) from None
            except NeedsReview:raise
            except (OSError,ValueError,KeyError,subprocess.TimeoutExpired):raise NeedsReview('La alineación local no se pudo verificar. Conserva subtítulos por escena o corrige los tiempos manualmente.') from None
