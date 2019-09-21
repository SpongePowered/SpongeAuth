import io
import os.path

import pytest
import unittest.mock
import PIL

from .. import models, views

_TESTDATA = os.path.join(os.path.dirname(__file__), "testdata")
_TEST_INPUT_FILE = open(os.path.join(_TESTDATA, "input.png"), "rb").read()

_WRITE_OUT_IMAGES = False


def _create_mocks(size, accept):
    avatar = unittest.mock.MagicMock()
    avatar.source = models.Avatar.UPLOAD
    avatar.image_file.file = io.BytesIO(_TEST_INPUT_FILE)
    user = unittest.mock.MagicMock()
    user.avatar = avatar
    request = unittest.mock.MagicMock()
    request.GET = {"size": size}
    request.META = {"HTTP_ACCEPT": accept}
    return user, request


@pytest.mark.parametrize(
    "size,out_filename",
    [
        ("210x210", "input.png"),
        ("210", "input.png"),
        ("zzrot", "120x120.png"),
        ("100x100", "100x100.png"),
        ("100x50", "100x50.png"),
        ("50x100", "50x100.png"),
        ("1024x1024", "240x240.png"),
        ("2048x1024", "240x120.png"),
        ("1024x2048", "120x240.png"),
    ],
)
def test_avatar_for_user_upload(size, out_filename):
    user, request = _create_mocks(size, "image/png")
    with unittest.mock.patch.object(views, "get_object_or_404") as get_object_or_404:
        get_object_or_404.return_value = user
        resp = views.avatar_for_user(request, "foo")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/png"
    im = PIL.Image.open(io.BytesIO(resp.getvalue()))
    if out_filename is not None:
        if _WRITE_OUT_IMAGES:
            im.save(os.path.join(_TESTDATA, out_filename))
        else:
            want_im = PIL.Image.open(os.path.join(_TESTDATA, out_filename))
            assert PIL.ImageChops.difference(im, want_im).getbbox() is None


def test_avatar_for_user_upload_webp():
    user, request = _create_mocks("210x210", "image/webp")
    with unittest.mock.patch.object(views, "get_object_or_404") as get_object_or_404:
        get_object_or_404.return_value = user
        resp = views.avatar_for_user(request, "foo")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/webp"
    assert PIL.Image.open(io.BytesIO(resp.getvalue()))


def test_avatar_for_user_upload_slowpath():
    user, request = _create_mocks("210x210", "image/png")
    user.avatar.image_file.read = user.avatar.image_file.file.read
    user.avatar.image_file.file = None
    with unittest.mock.patch.object(views, "get_object_or_404") as get_object_or_404:
        get_object_or_404.return_value = user
        resp = views.avatar_for_user(request, "foo")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/png"
    assert PIL.Image.open(io.BytesIO(resp.getvalue()))


@pytest.mark.parametrize(
    "size,out_s",
    [
        ("210x210", "210"),
        ("210", "210"),
        ("zzrot", "120"),
        ("100x100", "100"),
        ("100x50", "100"),
        ("50x100", "100"),
        ("1024x1024", "240"),
        ("2048x1024", "240"),
        ("1024x2048", "240"),
    ],
)
def test_avatar_for_user_gravatar(size, out_s):
    user, request = _create_mocks(size, "")
    user.avatar = models.Avatar(source=models.Avatar.URL, remote_url="https://example.com/foo.png")
    with unittest.mock.patch.object(views, "get_object_or_404") as get_object_or_404:
        get_object_or_404.return_value = user
        resp = views.avatar_for_user(request, "foo")
    assert resp.status_code == 302
    assert resp["Location"] == "https://example.com/foo.png?s=" + out_s
