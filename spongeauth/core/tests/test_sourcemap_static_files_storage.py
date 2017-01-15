from django.core.files.base import ContentFile

import pytest

from ..staticfiles import SourcemapManifestStaticFilesStorage


@pytest.fixture
def smsf_storage(settings):
    settings.STATIC_ROOT = '/static/'

    storage = SourcemapManifestStaticFilesStorage()
    storage._files = {}

    def _open(fn, *args, **kwargs):
        if fn not in storage._files:
            raise ValueError('No such file')
        return ContentFile(storage._files[fn])
    storage.open = _open

    def _save(filename, f):
        f.seek(0)
        storage._files[filename] = f.read()
        return filename
    storage._save = _save

    def _exists(filename):
        return filename in storage._files
    storage.exists = _exists

    def _paths():
        return {k: (storage, k) for k in storage._files}
    storage.paths = _paths

    return storage


def test_js_sourcemap(smsf_storage):
    smsf_storage._files['blah.js'] = br"""
(function() { some js here })();
//# sourceMappingURL=maps/blah2.map
"""
    smsf_storage._files['maps/blah2.map'] = b"sourcemap"

    list(smsf_storage.post_process(smsf_storage.paths()))

    assert 'maps/blah2.ae359e87985b.map' in smsf_storage._files
    assert 'blah.89cb2015a170.js' in smsf_storage._files
    assert (smsf_storage._files['blah.89cb2015a170.js'] ==
            b'\n(function() { some js here })();\n//# sourceMappingURL=maps/blah2.ae359e87985b.map\n')


def test_css_sourcemap(smsf_storage):
    smsf_storage._files['blah.css'] = br"""
somecss { transition: none; }
/*# sourceMappingURL=maps/blah2.map */
"""
    smsf_storage._files['maps/blah2.map'] = b"sourcemap"

    list(smsf_storage.post_process(smsf_storage.paths()))

    assert 'maps/blah2.ae359e87985b.map' in smsf_storage._files
    assert 'blah.99cd30dca034.css' in smsf_storage._files
    assert (smsf_storage._files['blah.99cd30dca034.css'] ==
            b'\nsomecss { transition: none; }\n/*# sourceMappingURL=maps/blah2.ae359e87985b.map */\n')
