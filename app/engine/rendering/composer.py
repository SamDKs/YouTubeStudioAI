"""Typed scene composition: crop → fit → motion → labels/captions → concatenation."""

import math
from pathlib import Path
from uuid import uuid4

from PIL import Image,ImageFilter,ImageOps

from app.domain.package_errors import NeedsReview,StudioError
from app.engine.domain.package import Asset,Crop,Deliverable,Scene
from app.engine.domain.serialization import digest
from app.engine.rendering.overlays import caption_layer,text_layer
from app.engine.rendering.process import FFmpegProcess
from app.engine.timing.subtitles import caption_cues
from app.engine.domain.package import ScreenText


def concat_quote(path: Path) -> str:return "file '"+str(path).replace('\\','\\\\').replace("'","'\\''")+"'"


def crop_image(image: Image.Image,region: Crop) -> Image.Image:
    width,height=image.size
    return image.crop((round(region.left*width),round(region.top*height),round(region.right*width),round(region.bottom*height)))


def prepare_image(path: Path,scene: Scene,size: tuple[int,int]) -> Image.Image:
    with Image.open(path) as source:image=crop_image(source.convert('RGB'),scene.crop)
    if scene.fit=='cover':return ImageOps.fit(image,size,Image.Resampling.LANCZOS,centering=(scene.anchor_x,scene.anchor_y))
    foreground=ImageOps.contain(image,size,Image.Resampling.LANCZOS)
    canvas=ImageOps.fit(image,size,Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(max(4,size[0]/55))) if scene.fit=='contain_blur' else Image.new('RGB',size,'#101722')
    canvas.paste(foreground,(round((size[0]-foreground.width)*scene.anchor_x),round((size[1]-foreground.height)*scene.anchor_y)))
    return canvas


def motion_filter(scene: Scene,size: tuple[int,int],duration: float,fps: int) -> str:
    width,height=size;motion=scene.motion
    if motion.kind=='static':return f'scale={width}:{height},setsar=1,fps={fps}'
    frames=max(2,math.ceil(duration*fps));fraction=f'min(on/{frames-1},1)'
    zoom=f'{motion.start_zoom}+({motion.end_zoom-motion.start_zoom})*{fraction}'
    x,y='(iw-iw/zoom)/2','(ih-ih/zoom)/2'
    if motion.kind=='pan_right':x=f'(iw-iw/zoom)*{fraction}'
    elif motion.kind=='pan_left':x=f'(iw-iw/zoom)*(1-{fraction})'
    elif motion.kind=='pan_down':y=f'(ih-ih/zoom)*{fraction}'
    elif motion.kind=='pan_up':y=f'(ih-ih/zoom)*(1-{fraction})'
    return f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={width}x{height}:fps={fps},setsar=1"


class PackageRenderer(FFmpegProcess):
    # Compone captions observados o aproximados en la zona segura.
    def _captions(self,folder: Path,scene: Scene,size: tuple[int,int],duration: float,timing: dict,mode: str) -> Path:
        blank=folder/'blank.png';caption_layer('',size,blank)
        words=timing.get('words',[]);cues=[]
        if mode=='word' and words:
            for index,word in enumerate(words):
                first=index//4*4
                cues.append((word['start_time'],word['end_time'],' '.join(w['word'] for w in words[first:first+4]),index-first))
        elif mode!='none':
            cues=[(start,end,text,None) for start,end,text in caption_cues(scene,timing)]
        listing=[];cursor=0.
        def append(path,seconds):
            if seconds>0:listing.extend([concat_quote(path),f'option framerate {self.config.fps}',f'duration {seconds:.9f}'])
        for index,(start,end,text,active) in enumerate(cues):
            append(blank,max(0,start-cursor));png=folder/f'caption-{index}.png'
            if len(text.split())>16 and active is None:
                # A provisional scene caption is a compact review notice; full text is in SRT/JSON.
                text='[PROVISIONAL SUBTITLES — REVIEW REQUIRED]'
            caption_layer(text,size,png,active);append(png,end-start);cursor=end
        append(blank,max(0,duration-cursor));listing.append(concat_quote(blank))
        result=folder/'captions.concat';result.write_text('\n'.join(listing)+'\n');return result

    # Normaliza el recurso y combina voz, rótulos, captions y transición.
    def render_scene(self,scene: Scene,asset: Asset,source: Path,audio: Path,timing: dict,deliverable: Deliverable,size: tuple[int,int],key: str,guard,progress) -> Path:
        folder=self.working/key;folder.mkdir(parents=True,exist_ok=True)
        duration=timing['scene_seconds'];width,height=size
        if asset.kind=='image':
            visual=folder/'visual.png';prepare_image(source,scene,(width*2,height*2)).save(visual)
            inputs=['-loop','1','-framerate',str(deliverable.fps),'-i',str(visual)]
            base=motion_filter(scene,size,duration,deliverable.fps)
        else:
            info=self._probe_path(source)
            if info['duration']-scene.video_start_seconds<duration-.025:raise NeedsReview('El clip '+asset.asset_id+' es más corto que el audio real; no se recorta la narración ni se repite el clip.')
            region=scene.crop
            crop=f'crop=iw*{region.right-region.left}:ih*{region.bottom-region.top}:iw*{region.left}:ih*{region.top}'
            if scene.fit=='cover':base=crop+f',scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:(iw-ow)*{scene.anchor_x}:(ih-oh)*{scene.anchor_y}'
            elif scene.fit=='contain':base=crop+f',scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)*{scene.anchor_x}:(oh-ih)*{scene.anchor_y}:black'
            else:raise NeedsReview('contain_blur para clips requiere otra revisión; usa cover/contain o una imagen. No se sustituyó silenciosamente.')
            base+=',setsar=1,fps='+str(deliverable.fps)
            if scene.motion.kind!='static':raise NeedsReview('El movimiento adicional de clips aún no está soportado; configura static.')
            inputs=['-ss',str(scene.video_start_seconds),'-i',str(source)]
        labels=folder/'labels.png'
        texts=scene.texts
        if not timing.get('words') and deliverable.captions_mode!='none':
            texts=texts+(ScreenText('Approximate captions — review required','disclosure','top',True),)
        text_layer(texts,size,labels)
        captions=self._captions(folder,scene,size,duration,timing,deliverable.captions_mode)
        fade=min(scene.transition_seconds,duration/2)
        if scene.transition=='fade':base+=f',fade=t=in:st=0:d={fade},fade=t=out:st={duration-fade}:d={fade}'
        # No temporal overlap between clips: fades stay inside each measured duration.
        filters=f'[0:v]{base}[base];[base][1:v]overlay=0:{round(height*(.70 if height>width else .78))}:eof_action=pass[c];[c][3:v]overlay=0:0,format=yuv420p[v]'
        output=folder/(uuid4().hex+'.mp4')
        self._run(inputs+['-f','concat','-safe','0','-i',str(captions),'-i',str(audio),'-loop','1','-i',str(labels),
            '-filter_complex_threads','1','-filter_complex',filters,'-map','[v]','-map','2:a:0','-t',str(duration),'-r',str(deliverable.fps),
            '-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-c:a','aac','-ar','48000','-movflags','+faststart',str(output)],guard,progress,duration)
        probe=self._probe_path(output)
        if abs(probe['duration']-duration)>.15:raise StudioError('La escena exportada no conserva la duración del audio.')
        return output

    # Concatena escenas y verifica duración y codecs reales.
    def assemble(self,clips: tuple[Path,...],duration: float,target: Path,guard,progress) -> dict:
        listing=self.working/(uuid4().hex+'.concat');listing.write_text('\n'.join(concat_quote(path) for path in clips)+'\n')
        self._run(['-f','concat','-safe','0','-i',str(listing),'-r',str(self.config.fps),'-fps_mode','cfr','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-c:a','copy','-movflags','+faststart',str(target)],guard,progress,duration)
        metadata=self._probe_path(target)
        if abs(metadata['duration']-duration)>.35:raise StudioError('La concatenación perdió o duplicó duración.')
        streams=metadata['streams'];video=next((s for s in streams if s['codec_type']=='video'),{});audio=next((s for s in streams if s['codec_type']=='audio'),{})
        if video.get('codec_name')!='h264' or audio.get('codec_name')!='aac':raise StudioError('La entrega no cumple H.264/AAC.')
        return metadata


    def mix_audio(self, video, package, deliverable, input_root, duration, guard, progress):
        """Mezcla pistas explícitas autorizadas con ducking, fundidos y limitador."""
        tracks=[t for t in package.audio_mix if t['deliverable_id']==deliverable.deliverable_id]
        if not tracks:return video,self._probe_path(video)
        inputs=['-i',str(video)];filters=[];labels=[]
        for index,track in enumerate(tracks,1):
            asset=package.asset(track['asset_id']);path=input_root/asset.path
            if asset.rights_status!='allowed' or not path.resolve().is_relative_to(input_root.resolve()) or digest(path.read_bytes())!=asset.sha256:
                raise NeedsReview('Música/efecto ausente, modificado o sin licencia aprobada.')
            self._probe_path(path)
            inputs+=['-i',str(path)]
            delay=round(track['start_seconds']*1000)
            filters.append(f'[{index}:a]aresample=48000,volume={track["gain"]},afade=t=in:d=0.3,adelay={delay}|{delay},apad,atrim=duration={duration},afade=t=out:st={max(0,duration-1)}:d=1[b{index}]')
            labels.append(f'[b{index}]')
        filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0[bed]')
        filters+=['[0:a]asplit=2[voice][control]','[bed][control]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=300[ducked]',
                  '[voice][ducked]amix=inputs=2:normalize=0,alimiter=limit=0.89:level=false[a]']
        output=self.working/(uuid4().hex+'.mixed.mp4')
        self._run(inputs+['-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-ar','48000','-t',str(duration),'-movflags','+faststart',str(output)],guard,progress,duration)
        return output,self._probe_path(output)
