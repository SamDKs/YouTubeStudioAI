"""QA técnica verificable; separada de la aprobación editorial y de derechos."""

from fractions import Fraction
import json
import math
from pathlib import Path
import re
import subprocess

from app.domain.package_errors import StudioError
from app.engine.rendering.process import FFmpegProcess


def check_subtitles(path, duration):
    """Exige SRT no vacío con índices, intervalos positivos y orden temporal."""
    text=path.read_text(encoding='utf-8').strip();blocks=re.split(r'\n\s*\n',text)
    previous=0.;count=0
    def seconds(value):
        """Convierte un timestamp SRT validado a segundos."""
        h,m,s=value.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
    for index,block in enumerate(blocks,1):
        lines=block.splitlines()
        if len(lines)<3 or lines[0]!=str(index):raise StudioError('QA: estructura SRT inválida.')
        match=re.fullmatch(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})',lines[1])
        if not match:raise StudioError('QA: timestamps SRT inválidos.')
        start,end=map(seconds,match.groups())
        if start<previous-.001 or not start<end<=duration+.05:raise StudioError('QA: SRT desordenado o fuera del audio.')
        previous=end;count+=1
    if not count:raise StudioError('QA: faltan subtítulos.')
    return count


def inspect_output(settings,working,output,expected_size,fps,scene_timings,guard,progress):
    """Decodifica el MP4 completo y mide negro/silencio/niveles sin fingir revisión humana."""
    path=settings.safe(output['path'])
    if not path.is_file() or path.stat().st_size<1000:raise StudioError('QA: MP4 ausente o truncado.')
    verifier=FFmpegProcess(settings,working,settings.work_root/'render.lock')
    probe=verifier._probe_path(path);video=next((s for s in probe['streams'] if s['codec_type']=='video'),{})
    audio=next((s for s in probe['streams'] if s['codec_type']=='audio'),{})
    if video.get('codec_name')!='h264' or audio.get('codec_name')!='aac':raise StudioError('QA: se requieren H.264 y audio AAC.')
    if (video.get('width'),video.get('height'))!=expected_size:raise StudioError('QA: resolución incorrecta.')
    if Fraction(video.get('avg_frame_rate','0/1'))!=fps:raise StudioError('QA: FPS distintos del perfil.')
    if not math.isfinite(probe['duration']) or probe['duration']<=0:raise StudioError('QA: duración inválida.')
    if not output.get('preview'):
        expected=sum(t['scene_seconds'] for t in scene_timings)
        if not scene_timings or abs(expected-probe['duration'])>.35:raise StudioError('QA: faltan escenas o cambió la duración narrativa.')
        cue_count=check_subtitles(settings.safe(output['subtitles']),probe['duration'])
    else:cue_count=None
    with verifier.render_slot(guard):
        verifier._run(['-xerror','-err_detect','explode','-i',str(path),'-map','0:v:0','-map','0:a:0','-f','null','-'],guard,progress,probe['duration'])
        # El proceso sigue usando el guard para cancelación; stderr queda en un archivo acotado al job.
        log=working/(path.stem[:70]+'-qa-analysis.log')
        with log.open('wb') as errors:
            process=subprocess.Popen([settings.ffmpeg,'-nostdin','-hide_banner','-i',str(path),
                '-vf','blackdetect=d=1:pix_th=0.1:pic_th=0.98',
                '-af','silencedetect=n=-45dB:d=1.2,volumedetect','-f','null','-'],stdout=subprocess.DEVNULL,stderr=errors)
            try:
                while True:
                    guard()
                    try:process.wait(timeout=.25);break
                    except subprocess.TimeoutExpired:continue
                if process.returncode:raise StudioError('QA: falló el análisis de negro/silencio.')
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
        text=log.read_text(errors='replace')
    levels={k:float(v) for k,v in re.findall(r'(mean_volume|max_volume): (-?[\d.]+) dB',text)}
    if levels.get('mean_volume',-100)<-60:raise StudioError('QA: audio ausente o casi silencioso.')
    black=[float(x) for x in re.findall(r'black_duration:([\d.]+)',text)]
    silence=[float(x) for x in re.findall(r'silence_duration: ([\d.]+)',text)]
    permitted_pause=max((t.get('pause_seconds',0) for t in scene_timings),default=0)+.5
    warnings=[]
    if black:warnings.append('Segmentos negros ≥1 s detectados; revisión visual necesaria.')
    if any(x>max(1.2,permitted_pause) for x in silence):warnings.append('Silencios prolongados detectados; escuchar antes de aprobar.')
    if output.get('provisional_subtitles'):warnings.append('Alineación aproximada: revisar subtítulos.')
    anomaly=bool(black) or any(x>max(1.2,permitted_pause) for x in silence)
    return {'technical_state':'QA_REVIEW_REQUIRED' if anomaly else 'QA_PASSED','editorial_state':'EDITORIAL_REVIEW_PENDING',
            'decoded_without_ffmpeg_error':True,'video_codec':video['codec_name'],'audio_codec':audio['codec_name'],
            'width':video['width'],'height':video['height'],'fps':video['avg_frame_rate'],'duration':probe['duration'],
            'narrated_scene_count':len(scene_timings),'srt_cues':cue_count,'audio_levels_db':levels,
            'black_segments_seconds':black,'silence_segments_seconds':silence,'warnings':warnings,
            'approved_for_publication':False}
