import resource
import pytest


@pytest.fixture(scope="session", autouse=True)
def raise_open_file_limit():
    """Raise soft open-file limit (RLIMIT_NOFILE) to prevent file descriptor exhaustion during test suite runs."""
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        target = 10240
        if hard != resource.RLIM_INFINITY:
            target = min(target, hard)
        if target > soft:
            resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    except Exception:
        pass


def pytest_configure(config):
    config.addinivalue_line('markers', 'mlx: requires a real MLX model and a host that passed the memory guard')


def pytest_collection_modifyitems(config, items):
    import json
    import os
    report = os.environ.get('SEOJEV_MLX_BLOCKED_REPORT')
    if not report:
        return
    with open(report) as source:
        result = json.load(source)
    if result.get('safe_batch_size') is not None or not any(r.get('memory_guard_triggered') for r in result.get('results', [])):
        raise pytest.UsageError('MLX resource skip requires a recorded unsafe autotune result')
    blocked = pytest.mark.skip(reason='Real MLX unavailable: batch 8 hit the zero-swap-growth guard; no retry allowed (' + report + ')')
    for item in items:
        if item.get_closest_marker('mlx'):
            item.add_marker(blocked)
