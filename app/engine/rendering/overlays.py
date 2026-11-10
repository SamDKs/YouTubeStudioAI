"""Editorial labels are composed after all crop/fit/motion transforms."""

from pathlib import Path
from PIL import Image,ImageDraw

from app.engine.domain.package import ScreenText
from app.engine.rendering.process import FFmpegProcess


def text_layer(texts: tuple[ScreenText,...],size: tuple[int,int],target: Path) -> None:
    width,height=size;image=Image.new('RGBA',size,(0,0,0,0));draw=ImageDraw.Draw(image)
    margin=round(width*.055);cursors={'top':height*(.10 if height>width else .045),'center':height*.38,'bottom':height*(.55 if height>width else .64)}
    for item in texts:
        font_size=max(14,round(min(size)*(.032 if item.kind in {'disclosure','hypothesis','source'} else .05)))
        font=FFmpegProcess._font(font_size);lines=[];line=''
        for word in item.text.split():
            candidate=(line+' '+word).strip()
            if draw.textlength(candidate,font=font)>width-2*margin and line:lines.append(line);line=word
            else:line=candidate
        if line:lines.append(line)
        y=cursors[item.position];line_height=font_size+10;bottom=y+len(lines)*line_height+12
        draw.rounded_rectangle((margin-10,y-8,width-margin+10,bottom),radius=8,fill=(0,0,0,185))
        for line in lines:draw.text((margin,y),line,font=font,fill='#fff5dd');y+=line_height
        cursors[item.position]=bottom+16
    image.save(target)


def caption_layer(text: str,size: tuple[int,int],target: Path,active_index: int | None=None) -> None:
    width,height=size;image=Image.new('RGBA',(width,round(height*.22)),(0,0,0,0));draw=ImageDraw.Draw(image)
    font_size=max(18,round(min(size)*.049));font=FFmpegProcess._font(font_size)
    lines=[];line=[]
    for word in text.split():
        if draw.textlength(' '.join(line+[word]),font=font)>width*(.74 if height>width else .84) and line:lines.append(line);line=[word]
        else:line.append(word)
    if line:lines.append(line)
    # Provisional phrases must remain readable; show bounded cues, never a giant paragraph.
    for index,words in enumerate(lines[:3]):
        x=(width-draw.textlength(' '.join(words),font=font))/2
        for word in words:
            ordinal=sum(len(part) for part in lines[:index])+words.index(word)
            draw.text((x,8+index*(font_size+8)),word,font=font,fill='#ffd477' if ordinal==active_index else 'white',stroke_width=2,stroke_fill='#05070a')
            x+=draw.textlength(word+' ',font=font)
    image.save(target)
