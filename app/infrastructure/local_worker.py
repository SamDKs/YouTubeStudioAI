"""Lanza procesos independientes de los reruns; la cola limita la concurrencia."""

import os
import subprocess
import sys


def launch_worker(settings,job_id):
    """Inicia un worker por job, con log local y sin shell ni descargas."""
    from uuid import UUID
    UUID(job_id)
    folder=settings.work_root/'logs';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(job_id+'.log')
    env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2')
    with path.open('ab') as log:
        process=subprocess.Popen([sys.executable,'-B','-m','app.worker','--root',str(settings.project_root),'--job',job_id],
                                 cwd=settings.project_root,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                                 start_new_session=True,env=env)
    return process.pid
