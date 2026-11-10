"""Validate the shared contract or import/inspect/queue local editorial packages."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

from app.bootstrap import create_studio
from app.domain.package_errors import StudioError
from app.engine.domain.package import Task
from app.engine.ingestion.contract import SCHEMA_PATH,load_json,validate_manifest
from app.engine.ingestion.zip_reader import ZipReader


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    validate=commands.add_parser('validate',help='Comprobar ZIP sin importarlo ni abrir SQLite');validate.add_argument('zip',type=Path)
    commands.add_parser('contract-check',help='Comprobar esquema y ejemplo nativo sin interfaz ni base')
    load=commands.add_parser('import',help='Importar un ZIP a una entrada independiente');load.add_argument('zip',type=Path)
    inspect=commands.add_parser('inspect');inspect.add_argument('project_id')
    queue=commands.add_parser('enqueue');queue.add_argument('project_id');queue.add_argument('--task',choices=[t.value for t in Task],required=True)
    queue.add_argument('--deliverable',action='append',required=True);queue.add_argument('--scene',action='append',default=[]);queue.add_argument('--confirm',action='store_true');queue.add_argument('--allow-provisional',action='store_true')
    produce=commands.add_parser('produce-long',help='Encolar largo 1080p con vista previa y QC, sin Shorts')
    produce.add_argument('project_id');produce.add_argument('--fps',type=int,choices=[24,25,30],default=30)
    produce.add_argument('--strict-subtitles',action='store_true');produce.add_argument('--require-cleared-rights',action='store_true');produce.add_argument('--confirm',action='store_true')
    args=parser.parse_args()
    try:
        if args.command=='contract-check':
            Draft202012Validator.check_schema(json.loads(SCHEMA_PATH.read_text()))
            root=SCHEMA_PATH.parent/'examples/minimal';package=validate_manifest(load_json(root/'manifest.json'),root)
            print(json.dumps({'contract':package.contract_version,'example':'valid'}));return 0
        if args.command=='validate':
            with ZipReader().inspect(args.zip) as result:
                package=validate_manifest(result.manifest)
                print(json.dumps({'valid':True,'episode_id':package.episode_id,'deliverables':[d.deliverable_id for d in package.deliverables],'warnings':result.warnings},ensure_ascii=False,indent=2))
            return 0
        studio=create_studio()
        if args.command=='produce-long':
            if not args.confirm:raise StudioError('Confirma el procesamiento local con --confirm.')
            job=studio.produce_long(args.project_id,fps=args.fps,allow_provisional=not args.strict_subtitles,review_only=not args.require_cleared_rights)
            print(json.dumps({'job_id':job,'worker_command':'.venv/bin/python -B -m app.worker --job '+job}));return 0
        if args.command=='import':print(json.dumps({'project_id':studio.import_zip(args.zip)}));return 0
        if args.command=='inspect':print(json.dumps(asdict(studio.get(args.project_id)),ensure_ascii=False,indent=2));return 0
        if args.command=='enqueue':
            job=studio.enqueue(args.project_id,Task(args.task),tuple(args.deliverable),tuple(args.scene),confirmed=args.confirm,allow_provisional=args.allow_provisional)
            print(json.dumps({'job_id':job}));return 0
    except (StudioError,OSError,KeyError,TypeError) as exc:
        print(str(exc) if isinstance(exc,(StudioError,OSError)) else 'El paquete contiene campos o tipos no válidos.',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
