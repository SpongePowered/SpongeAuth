import os.path

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# mime.types from Apache HTTPd:
# http://svn.apache.org/repos/asf/httpd/httpd/trunk/docs/conf/mime.types
MIME_FILENAME = os.path.join(BASE_DIR, 'mime.types')

_fwd_cache = None
_rev_cache = None


def _load():
    global _fwd_cache, _rev_cache
    if _fwd_cache and _rev_cache:
        return _fwd_cache, _rev_cache
    _fwd_cache = {}
    _rev_cache = {}
    with open(MIME_FILENAME, 'r') as fh:
        for ln in fh:
            ln = ln.strip()
            if '#' in ln:
                ln = ln[:ln.index('#')].strip()
            if not ln:
                continue
            mime_type, extensions = ln.split(maxsplit=1)
            exts = extensions.split()
            _fwd_cache[mime_type] = exts
            for ext in exts:
                _rev_cache[ext] = mime_type
    return _fwd_cache, _rev_cache


def mime2exts(mime):
    fwd_cache, _ = _load()
    if mime == 'image/jpeg':
        # special case: make jpg come first
        return ['jpg', 'jpeg', 'jpe']
    return fwd_cache.get(mime)


def ext2mime(ext):
    _, rev_cache = _load()
    return rev_cache.get(ext)
