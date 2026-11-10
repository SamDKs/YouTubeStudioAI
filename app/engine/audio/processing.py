"""Only narration enters TTS; real PCM measurements drive the visual timeline."""

import io
from pathlib import Path
from uuid import uuid4
import wave

from app.engine.rendering.process import FFmpegProcess


class AudioProcessor(FFmpegProcess):
    def normalize(self,content: bytes,pause_seconds: float,guard) -> tuple[bytes,dict]:
        source=self.working/(uuid4().hex+'.wav');source.write_bytes(content)
        output=self.working/(uuid4().hex+'.normalized.wav')
        self._run(['-i',str(source),'-vn','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ac','1','-ar','24000','-c:a','pcm_s16le',str(output)],guard,lambda _:None,1.)
        probe=self._probe_path(output)
        with wave.open(str(output),'rb') as reader:
            rate=reader.getframerate();params=reader.getparams();frames=reader.readframes(reader.getnframes())
        silence_frames=round(pause_seconds*rate);data=io.BytesIO()
        with wave.open(data,'wb') as writer:
            writer.setparams(params);writer.writeframes(frames+b'\x00\x00'*silence_frames)
        return data.getvalue(),{'narration_seconds':probe['duration'],'pause_seconds':silence_frames/rate,
            'scene_seconds':probe['duration']+silence_frames/rate,'sample_rate':rate,'normalization':'FFmpeg loudnorm one pass; PCM verified with ffprobe'}
