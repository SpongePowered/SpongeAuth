import hashlib
import hmac
import secrets
import base64
import urllib.parse


class DiscourseSigner:
    def __init__(self, sso_key):
        self.sso_key = sso_key.encode('utf8')

    def _sign(self, payload):
        m = hmac.new(self.sso_key, msg=payload, digestmod=hashlib.sha256)
        return m.hexdigest().encode('utf8')

    def _verify(self, payload, signature):
        good_signature = self._sign(payload)
        if not secrets.compare_digest(good_signature, signature):
            raise SignatureError('invalid signature: got {}, want {}'.format(
                signature, good_signature))

    def unsign(self, payload, signature):
        self._verify(payload.encode('utf8'), signature.encode('utf8'))
        payload_raw = base64.b64decode(payload)
        return urllib.parse.parse_qs(payload_raw)

    def sign(self, payload_data):
        payload_raw = urllib.parse.urlencode(payload_data).encode('utf8')
        payload = base64.b64encode(payload_raw)
        signature = self._sign(payload)
        return payload.decode('utf8'), signature.decode('utf8')


class SignatureError(Exception):
    pass
