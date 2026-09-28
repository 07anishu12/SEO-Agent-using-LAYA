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
