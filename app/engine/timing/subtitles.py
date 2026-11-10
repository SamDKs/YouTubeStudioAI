"""Final timestamps come from measured audio; provisional subtitles are explicit."""


def srt_time(value: float) -> str:
    seconds,milliseconds=divmod(max(0,round(value*1000)),1000)
    minutes,second=divmod(seconds,60);hour,minute=divmod(minutes,60)
    return f'{hour:02}:{minute:02}:{second:02},{milliseconds:03}'


def caption_cues(scene, timing):
    """Agrupa palabras observadas o estima grupos dentro del audio medido, sin afirmar alineación."""
    words=timing.get('words',[])
    if words:
        return [(words[i]['start_time'],words[min(i+5,len(words)-1)]['end_time'],
                 ' '.join(w['word'] for w in words[i:i+6])) for i in range(0,len(words),6)]
    tokens=scene.narration.split();groups=[' '.join(tokens[i:i+6]) for i in range(0,len(tokens),6)]
    total=sum(len(group) for group in groups) or 1;cursor=0.;cues=[]
    for group in groups:
        end=cursor+timing['narration_seconds']*len(group)/total
        cues.append((cursor,end,group));cursor=end
    return cues


def export_srt(scenes: tuple, timings: tuple[dict,...]) -> tuple[bytes,bool]:
    """Exporta tiempos relativos al audio; marca si algún grupo usa estimación."""
    cues=[];offset=0.;provisional=False
    for scene,timing in zip(scenes,timings):
        cues.extend((offset+start,offset+end,text) for start,end,text in caption_cues(scene,timing))
        provisional=provisional or not bool(timing['words'])
        offset+=timing['scene_seconds']
    content='\n\n'.join(f'{index+1}\n{srt_time(start)} --> {srt_time(end)}\n{text}' for index,(start,end,text) in enumerate(cues))+'\n'
    return content.encode('utf-8'),provisional
