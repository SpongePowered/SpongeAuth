import pytest

from .. import discourse_sso

HARDCODED_SIGNING = 'slartibartfast'


class SignerTestCase:
    def setup(self):
        self.signer = discourse_sso.DiscourseSigner(HARDCODED_SIGNING)


class TestSign(SignerTestCase):
    def test_sign_empty(self):
        assert self.signer.sign({}) == ('', '54113943c5acdf489e85786046ea6f8183bcd3be9297397181194e663aba0d02')

    def test_sign_string(self):
        assert self.signer.sign({'nonce': 'number used once'}) == (
            'bm9uY2U9bnVtYmVyK3VzZWQrb25jZQ==', 'a42c444d01993b53fe2f189bc5af05c04f4340306bca30721e049e8417372245')

    def test_sign_boolean(self):
        assert self.signer.sign({'avatar_force_update': True}) == (
            'YXZhdGFyX2ZvcmNlX3VwZGF0ZT10cnVl', '2012b41a566916139c96a3b659013dfb8311274ce2e76988724f4149dca444cc')

    def test_sign_combo(self):
        assert self.signer.sign({'username': 'lukegb', 'avatar_force_update': True}) == (
            'dXNlcm5hbWU9bHVrZWdiJmF2YXRhcl9mb3JjZV91cGRhdGU9dHJ1ZQ==',
            '1c10d05832df8b667414c2602dfda6b11b0bc122ca0cd23cd158622dc96976d3')


class TestUnsign(SignerTestCase):
    def test_unsign_good(self):
        in_pair = ('dXNlcm5hbWU9bHVrZWdiJmF2YXRhcl9mb3JjZV91cGRhdGU9dHJ1ZQ==',
                   '1c10d05832df8b667414c2602dfda6b11b0bc122ca0cd23cd158622dc96976d3')
        payload = self.signer.unsign(*in_pair)
        assert payload == {b'username': b'lukegb', b'avatar_force_update': b'true'}

    def test_unsign_bad(self):
        in_pair = ('dXNlcm5hbWU9bHVrZWdiJmF2YXRhcl9mb3JjZV91cGRhdGU9dHJ1ZQ==',
                   '1c10d05832df8b667414c2602dfda6b11b0bc122ca0cd23cd158622dc96976d4')
        with pytest.raises(discourse_sso.SignatureError):
            self.signer.unsign(*in_pair)


class TestDiscourseSigner(SignerTestCase):
    def test_sign_then_unsign_roundtrip(self):
        input = {'username': 'lukegb', 'avatar_force_update': True}
        output = self.signer.unsign(*self.signer.sign(input))
        assert output == {b'username': b'lukegb', b'avatar_force_update': b'true'}

    def test_unsign_then_sign_roundtrip(self):
        in_pair = ('dXNlcm5hbWU9bHVrZWdiJmF2YXRhcl9mb3JjZV91cGRhdGU9dHJ1ZQ==',
                   '1c10d05832df8b667414c2602dfda6b11b0bc122ca0cd23cd158622dc96976d3')
        out_pair = self.signer.sign(self.signer.unsign(*in_pair))
        assert in_pair == out_pair
