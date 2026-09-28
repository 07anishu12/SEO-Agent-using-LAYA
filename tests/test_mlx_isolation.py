import os
import subprocess
import sys


def test_cpu_boundary_does_not_import_mlx():
    code="import scripts.chunk_stage; import sys; assert not any(k == 'mlx' or k.startswith('mlx.') or k == 'laya_mlx' or k.startswith('laya_mlx.') for k in sys.modules)"
    subprocess.run([sys.executable,'-c',code],check=True,env={**os.environ,'SEOJEV_CPU_WORKER':'1'})


def test_backend_rejects_cpu_worker_before_import():
    code="""
import sys
from laya.backends.mlx import MLXBackend
try:
    MLXBackend().initialize()
except RuntimeError as exc:
    assert 'CPU pool workers' in str(exc)
else:
    raise AssertionError('CPU worker loaded model')
assert 'laya_mlx' not in sys.modules
"""
    subprocess.run([sys.executable,'-c',code],check=True,env={**os.environ,'SEOJEV_CPU_WORKER':'1'})


def test_close_releases_model_before_lock_without_loading_mlx(tmp_path):
    from laya.backends.mlx import MLXBackend
    backend=MLXBackend()
    backend._agent=object()  # Ownership sentinel, never a model or inference result.
    handle=open(tmp_path/'owner.lock','a')
    backend._owner_lock=handle
    backend.close()
    assert backend._agent is None and backend._owner_lock is None and handle.closed
    backend.close()  # Idempotent cleanup, including failed startup.
