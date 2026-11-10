"""TTS local CPU: modelo explícito, PCM real, sin descargas ni API implícitas."""

import io
import json
import math
import re
import time
import wave

from app.domain.package_errors import NeedsReview
from app.engine.domain.serialization import digest
from app.engine.domain.languages import LANGUAGES


class KokoroSpeech:
    def __init__(self,root) -> None:
        self.folder=root/'data/models/kokoro'
        self.engine=None

    def _load(self):
        if self.engine is not None:return self.engine
        try:
            import onnxruntime as ort
            from kokoro_onnx import Kokoro
        except ImportError:raise NeedsReview('Kokoro no está instalado. Importa audio local o configura el proveedor.') from None
        if not (self.folder/'manifest.json').is_file():raise NeedsReview('Falta el manifiesto verificable del modelo Kokoro.')
        manifest=json.loads((self.folder/'manifest.json').read_text())
        for item in manifest['files']:
            if item['file'] not in {'model.onnx','voices.bin'}:raise NeedsReview('Archivo de modelo no admitido.')
            path=self.folder/item['file']
            if path.name not in {'model.onnx','voices.bin'} or not path.is_file() or digest(path.read_bytes())!=item['sha256']:
                raise NeedsReview('El modelo o las voces de Kokoro cambiaron; revisa su integridad.')
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        session=ort.InferenceSession(str(self.folder/'model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.engine=Kokoro.from_session(session,str(self.folder/'voices.bin'))
        return self.engine

    def voices(self, language: str = "en-US") -> tuple[str,...]:
        # Abrir configuración no carga el grafo ni ejecuta inferencia.
        if not (self.folder/'voices.bin').is_file():return ()
        import numpy as np
        with np.load(self.folder/'voices.bin',allow_pickle=False) as voices:
            return tuple(sorted(v for v in voices.files if v.startswith(LANGUAGES[language][0])))

    def model_fingerprint(self) -> str:
        path=self.folder/'manifest.json'
        if not path.is_file():raise NeedsReview('Falta configurar el modelo local de voz.')
        return digest(path.read_bytes())

    def speech(self,text: str,voice: str,speed: float=.95,pronunciation: dict | None = None, language: str = "en-US") -> tuple[bytes,dict]:
        if not .7<=speed<=1.2 or not math.isfinite(speed):raise NeedsReview('La velocidad local debe estar entre 0,7 y 1,2.')
        if not text.strip() or len(text)>12000:raise NeedsReview('La narración está vacía o es demasiado extensa para un segmento.')
        if language not in LANGUAGES or voice not in self.voices(language):raise NeedsReview('Selecciona una voz instalada compatible con el idioma.')
        spoken=text
        for name,value in (pronunciation or {}).items():
            spoken=re.sub(r'\b'+re.escape(name)+r'\b',lambda _:value,spoken)
        engine=self._load();start=time.monotonic()
        audio,rate=engine.create(spoken,voice=voice,speed=speed,lang=LANGUAGES[language][1])
        import numpy as np
        samples=np.asarray(audio,dtype=np.float32)
        if not samples.size or not np.all(np.isfinite(samples)):raise NeedsReview('Kokoro no devolvió audio PCM válido.')
        peak=float(np.max(np.abs(samples)))
        if peak<.0001:raise NeedsReview('La narración local está vacía o en silencio.')
        samples=np.clip(samples,-1.,1.)
        output=io.BytesIO()
        with wave.open(output,'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate)
            stream.writeframes((samples*32767).astype('<i2').tobytes())
        return output.getvalue(),{'provider':'kokoro','model':'Kokoro-82M v1.0 INT8','voice':voice,'speed':speed,
            'language':language,'phonemizer_language':LANGUAGES[language][1],'duration':len(samples)/rate,'sample_rate':rate,'elapsed_seconds':time.monotonic()-start,
            'model_sha256':digest((self.folder/'model.onnx').read_bytes()),'synthetic':True,
            'alignment':'none; no word timestamps inferred','quality_review':'pending_human_listening'}
