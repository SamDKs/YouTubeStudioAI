"""Local Work-package worker. Historical production jobs remain read-only."""

import argparse
import json
import logging
from pathlib import Path
import signal
from threading import Event,Thread
from uuid import uuid4

from app.bootstrap import create_executor,prepare_storage
from app.config import Settings
from app.domain.package_errors import Canceled,LeaseLost,NeedsReview,StudioError,Paused
from app.engine.pipeline.sqlite_store import SqliteWorkStore


# Mantiene el lease y transforma pausa, cancelación y fallos en estados durables.
def execute_owned(executor,store,lease,shutdown=None) -> str:
    shutdown=shutdown or Event();done=Event();lost=Event()
    def heartbeat():
        while not done.wait(5):
            try:store.heartbeat(lease)
            except Exception:lost.set();return
    def guard():
        if shutdown.is_set():raise InterruptedError('Worker detenido por el usuario.')
        if lost.is_set():raise LeaseLost('Lease perdido.')
        store.guard(lease)
    thread=Thread(target=heartbeat,name='work-heartbeat',daemon=True);thread.start()
    try:
        executor.run(lease,guard)
        try:
            from app.engine.pipeline.delivery import DeliveryAssembler
            DeliveryAssembler(executor.settings,store).refresh(store.run_project_id(lease.job_id))
        except Exception as exc:
            logging.getLogger(__name__).error('La entrega requiere reintentar su empaquetado: %s',type(exc).__name__)
        return next(j['status'] for j in store.jobs(store.run_project_id(lease.job_id)) if j['job_id']==lease.job_id)
    except LeaseLost:return 'lease_lost'
    except Paused as exc:store.finish(lease,'paused',{},str(exc));return 'paused'
    except Canceled as exc:store.finish(lease,'canceled',{},str(exc));return 'canceled'
    except InterruptedError as exc:store.finish(lease,'queued',{},str(exc));return 'queued'
    except NeedsReview as exc:store.finish(lease,'waiting_review',{},str(exc));return 'waiting_review'
    except Exception as exc:
        message=str(exc) if isinstance(exc,StudioError) else 'Fallo local ('+type(exc).__name__+'). Las entradas y etapas verificadas se conservan.'
        logging.getLogger(__name__).error(message)
        store.finish(lease,'failed',{},message);return 'failed'
    finally:done.set();thread.join(timeout=6)


# Atiende la cola fuera de Streamlit y responde a señales de parada.
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job');parser.add_argument('--once',action='store_true');parser.add_argument('--root',type=Path)
    args=parser.parse_args();settings=Settings(args.root) if args.root else Settings()
    store=SqliteWorkStore(prepare_storage(settings));executor=create_executor(settings,store);shutdown=Event()
    signal.signal(signal.SIGINT,lambda *_:shutdown.set());signal.signal(signal.SIGTERM,lambda *_:shutdown.set())
    while not shutdown.is_set():
        lease=store.claim(str(uuid4()),args.job)
        if not lease:
            if args.job:
                with store.database.connection(read_only=True) as c:
                    row=c.execute('SELECT status FROM jobs WHERE job_id=?',(args.job,)).fetchone()
                if row and row[0]=='queued':shutdown.wait(1);continue
                return 0
            if args.once:return 0
            shutdown.wait(1);continue
        state=execute_owned(executor,store,lease,shutdown)
        print(json.dumps({'job_id':lease.job_id,'state':state}),flush=True)
        if args.once or args.job:return 0 if state in {'completed','waiting_review','paused'} else 1
    return 0


if __name__=='__main__':raise SystemExit(main())
