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
