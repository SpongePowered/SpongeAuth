import time

from .. import oath


def test_hotp_rfc4226():
    key = b"12345678901234567890"
    expect_vals = [755_224, 287_082, 359_152, 969_429, 338_314, 254_676, 287_922, 162_583, 399_871, 520_489]
    for n, expect in enumerate(expect_vals):
        got = oath.hotp(key, n)
        assert got == expect


def test_totp_zero_behaviour():
    key = b"12345678901234567890"
    totp = oath.TOTP(key)
    totp.time = 0
    assert totp.t() == 0
    assert totp.token() == 755_224  # same as index 0 for hotp
    assert totp.verify(755_224)
    assert not totp.verify(287_082)


def test_totp_step_size():
    key = b"12345678901234567890"
    totp = oath.TOTP(key)
    totp.time = 30
    assert totp.t() == 1

    totp = oath.TOTP(key, step=60)
    totp.time = 30
    assert totp.t() == 0


def test_totp_verify_uses_drift():
    key = b"12345678901234567890"
    totp = oath.TOTP(key)
    totp.time = 30
    assert totp.verify(287_082)
    assert totp.drift == 0
    assert not totp.verify(359_152)
    assert totp.verify(359_152, tolerance=1)
    assert totp.drift == 1
    assert totp.verify(969_429, tolerance=1)
    assert totp.drift == 2
    assert not totp.verify(287_082, tolerance=1)


def test_totp_verify_respects_min_t():
    key = b"12345678901234567890"
    totp = oath.TOTP(key)
    totp.time = 30
    assert totp.verify(287_082)
    assert totp.verify(287_082, min_t=1)
    assert not totp.verify(287_082, min_t=2)


def test_totp_uses_t0():
    key = b"12345678901234567890"
    totp = oath.TOTP(key)
    totp.t0 = time.time() - 1
    assert totp.t() == 0


def test_totp_time():
    key = b"12345678901234567890"
    totp = oath.TOTP(key)
    totp.time = 13131
    assert totp.time == 13131
    del totp.time
    assert totp.time != 13131
