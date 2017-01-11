import spongemime


def test_mime2exts():
    assert spongemime.mime2exts('image/png') == ['png']
    assert set(spongemime.mime2exts('image/jpeg')) == {'jpg', 'jpeg', 'jpe'}
    assert set(spongemime.mime2exts('image/svg+xml')) == {'svg', 'svgz'}


def test_ext2mime():
    assert spongemime.ext2mime('png') == 'image/png'
    assert spongemime.ext2mime('jpg') == 'image/jpeg'
    assert spongemime.ext2mime('jpeg') == 'image/jpeg'
