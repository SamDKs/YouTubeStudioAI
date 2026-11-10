"""Timestamps de palabras independientes del proveedor; sin tiempos interpolados."""

from dataclasses import asdict, dataclass
import math
import re

from app.domain.package_errors import NeedsReview


def normalized_words(text: str) -> list[str]:
    return [re.sub(r'[^\w]+', '', word.casefold()) for word in text.split() if re.sub(r'[^\w]+', '', word)]


@dataclass(frozen=True)
class WordTiming:
    word: str
    start_time: float
    end_time: float
    segment_id: str
    confidence: float | None = None


class AlignmentReview(NeedsReview):
    """Tiempos observados que no deben presentarse como alineación validada."""
    def __init__(self,message: str,candidates: list[WordTiming]) -> None:
        super().__init__(message)
        self.candidates=candidates


def validate_words(words: list[WordTiming], text: str, duration: float) -> list[WordTiming]:
    if not words or not math.isfinite(duration) or duration <= 0:
        raise NeedsReview('Faltan timestamps reales de la narración; no se inventará una alineación.')
    previous = 0.
    for word in words:
        if len(word.word.split())!=1:raise NeedsReview('Cada timestamp por palabra debe contener una única palabra.')
        if not word.word.strip() or not all(math.isfinite(t) for t in (word.start_time, word.end_time)):
            raise NeedsReview('La alineación contiene palabras o tiempos inválidos.')
        if word.start_time < previous - .001 or not 0 <= word.start_time < word.end_time <= duration + .025:
            raise NeedsReview('La alineación contiene solapamientos, desorden o tiempos fuera del audio.')
        previous = word.end_time
    if normalized_words(' '.join(w.word for w in words)) != normalized_words(text):
        raise NeedsReview('Las palabras alineadas no corresponden al guion de referencia. Revisa pronunciación o normalización del proveedor.')
    return words


def character_alignment(alignment: dict | None, text: str, duration: float, segment_id: str) -> list[WordTiming]:
    if not alignment:
        raise NeedsReview('El proveedor no entregó timestamps. Se necesita alineación real antes de renderizar.')
    chars = alignment.get('characters', [])
    starts = alignment.get('character_start_times_seconds', [])
    ends = alignment.get('character_end_times_seconds', [])
    if not chars or not len(chars) == len(starts) == len(ends):
        raise NeedsReview('Los timestamps por caracteres están incompletos.')
    if any(not isinstance(c, str) or len(c) != 1 for c in chars):
        raise NeedsReview('El proveedor devolvió una estructura de caracteres incompatible.')
    previous = 0.
    for start, end in zip(starts, ends):
        if not all(isinstance(v, (float, int)) and math.isfinite(v) for v in (start, end)) or start < previous - .001 or not 0 <= start <= end <= duration + .025:
            raise NeedsReview('Los timestamps de caracteres no son temporalmente válidos.')
        previous = start
    joined = ''.join(chars)
    words = [WordTiming(match.group(), float(starts[match.start()]), float(ends[match.end()-1]), segment_id)
             for match in re.finditer(r'\S+', joined) if normalized_words(match.group())]
    return validate_words(words, text, duration)


def forced_alignment(data: dict, text: str, duration: float, segment_id: str) -> list[WordTiming]:
    words = [WordTiming(w['text'], float(w['start']), float(w['end']), segment_id) for w in data.get('words', [])]
    return validate_words(words, text, duration)


def segment_words(words: list[WordTiming], scenes: list[dict], duration: float) -> list[dict]:
    segments = []
    cursor = 0
    for index, scene in enumerate(scenes):
        count = len(normalized_words(scene['narration']))
        selected = words[cursor:cursor + count]
        if len(selected) != count or normalized_words(' '.join(w.word for w in selected)) != normalized_words(scene['narration']):
            raise NeedsReview('No se puede asociar la alineación a las escenas aprobadas.')
        start = 0. if index == 0 else words[cursor].start_time
        cursor += count
        end = duration if index == len(scenes)-1 else words[cursor].start_time
        if end <= start:
            raise NeedsReview('Una escena no tiene duración real positiva.')
        shifted = [WordTiming(w.word, w.start_time-start, w.end_time-start, scene['scene_id'], w.confidence) for w in selected]
        validate_words(shifted, scene['narration'], end-start)
        segments.append({'start': start, 'end': end, 'words': [asdict(w) for w in shifted]})
    if cursor != len(words):
        raise NeedsReview('Quedaron palabras sin escena; revisa el storyboard.')
    return segments
