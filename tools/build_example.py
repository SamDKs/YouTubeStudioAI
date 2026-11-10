"""Build the small original example that is validated against the canonical schema."""

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw
from app.engine.domain.serialization import digest


def build(root: Path):
    (root/'assets').mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(320,180),'#163c4d');draw=ImageDraw.Draw(image);draw.rectangle((30,30,290,145),outline='#ffc15a',width=3)
    path=root/'assets/scene.png';image.save(path)
    value={'contract_version':'1.0.0','package_version':'1.0.0','episode_id':'EXAMPLE-001','channel_id':'MIS','title':'Evidence needs context','language':'en-US','target_market':'US',
      'assets':[{'asset_id':'image-1','kind':'image','role':'visual','path':'assets/scene.png','sha256':digest(path.read_bytes()),'status':'available','dimensions':{'width':320,'height':180},
        'provenance':{'origin':'user','generation_status':'not_applicable','rights_status':'allowed','author':'YouTube Studio AI test fixture','license':'CC0 original geometric fixture','source_url':None},'constraints':{'required_crop':None}}],
      'deliverables':[{'deliverable_id':'explainer','kind':'custom','title':'Evidence needs context','resolution':{'width':640,'height':360},'fps':24,'target_duration_seconds':{'min':.5,'max':5.},'captions':{'mode':'phrase','on_alignment_failure':'scene_estimates'},'narration_file':None,
        'scenes':[{'scene_id':'scene-1','narration':'Evidence needs context.','asset_id':'image-1','estimated_duration_seconds':2.,'pause_after_seconds':.25,'crop':[0.,0.,1.,1.],'fit':'contain','anchor':{'x':.5,'y':.5},'motion':{'kind':'static','start_zoom':1.,'end_zoom':1.},'transition':{'kind':'fade','duration_seconds':.2},'texts':[{'text':'TEST FIXTURE — NOT A FINISHED EPISODE','kind':'disclosure','position':'top','required':True}],'editorial_references':[]}]}],
      'editorial_references':[],'checksums':{'assets/scene.png':digest(path.read_bytes())}}
    (root/'manifest.json').write_text(json.dumps(value,indent=2,ensure_ascii=False))
    return value


if __name__=='__main__':build(ROOT/'schemas/examples/minimal')
