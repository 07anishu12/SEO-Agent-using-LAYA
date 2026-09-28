"""Conservative local defaults; production is always an explicit selection."""
import copy
import os

DEFAULTS = dict(max_urls=500, seed=42, memory_budget_mb=4096, max_workers=2,
                batch_size=8, queue_size=16, throttle_seconds=0.05,
                pause_seconds=2.0, min_available_mb=1536)


def resolve_profile(config=None, profile='dev'):
    if profile not in ('dev', 'val', 'prod'):
        raise ValueError('profile must be dev, val, or prod')
    config = copy.deepcopy(config or {})
    limits = {**DEFAULTS, **config.get('profiles', {}).get(profile, {})}
    for key, default in DEFAULTS.items():
        limits[key] = type(default)(os.getenv('SEOJEV_' + key.upper(), limits[key]))
    if any(limits[k] < 1 for k in ('max_urls', 'memory_budget_mb', 'max_workers', 'batch_size', 'queue_size')):
        raise ValueError('Resource limits must be positive')
    if any(limits[k] < 0 for k in ('throttle_seconds', 'pause_seconds', 'min_available_mb')):
        raise ValueError('Throttle and pressure limits cannot be negative')
    if profile == 'dev':
        limits['max_urls'] = min(500, limits['max_urls'])
        limits['max_workers'] = min(2, limits['max_workers'])
    elif profile == 'val':
        limits['max_urls'] = min(1000, limits['max_urls'])
        limits['max_workers'] = min(2, limits['max_workers'])
    config['profile'], config['runtime'] = profile, limits
    config.setdefault('storage', {})['backend'] = os.getenv('SEOJEV_STORAGE_BACKEND', config.get('storage', {}).get('backend', 'sqlite'))
    for key, env in [('db_path', 'SEOJEV_DB_PATH'), ('store_dir', 'SEOJEV_STORE_DIR')]:
        if env in os.environ:
            config['storage'][key] = os.environ[env]
    return config
