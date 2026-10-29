import tempfile, json
from pathlib import Path
from cache_cleanup import clear_cache, cache_info


def verify(folder):
    with tempfile.TemporaryDirectory(dir=folder) as root:
        base = Path(root)
        cache = base / 'extractor-cache'
        cache.mkdir()
        (cache / 'data.json').write_bytes(b'cache')
        (base / 'cookies.txt').write_bytes(b'KEEP')
        assert cache_info(base)['bytes'] == 5
        result = clear_cache(base)
        assert result['bytes'] == 0 and result['failed'] == 0
        assert (base / 'cookies.txt').read_bytes() == b'KEEP'
        return json.dumps({'success': True})
