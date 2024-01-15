import binascii
import nacl.signing
import nacl.encoding
import nacl.exceptions
import codecs


class Sign:

    def __init__(self, privkey):
        # Load private key from file
        with open(privkey, 'rb') as private_key_file:
            private_key_bytes = private_key_file.read(64)
            self.signing_key = nacl.signing.SigningKey(private_key_bytes, encoder=nacl.encoding.HexEncoder)

    def key(self):
        return self.signing_key.encode(encoder=nacl.encoding.HexEncoder).decode("utf-8")

    def sign(self, msg):
        try:
            signed_message = self.signing_key.sign(msg.encode("utf-8"))
            return codecs.encode(signed_message.signature, "hex").decode("utf-8")
        except binascii.Error:
            raise


class Verify:

    def __init__(self, pubkey):
        # Load private key from file
        with open(pubkey, 'rb') as public_key_file:
            public_key_bytes = public_key_file.read(64)
            self.verification_key = nacl.signing.VerifyKey(public_key_bytes, encoder=nacl.encoding.HexEncoder)

    def key(self):
        return self.verification_key.encode(encoder=nacl.encoding.HexEncoder).decode("utf-8")

    def verify(self, msg, signature):
        try:
            try:
                self.verification_key.verify(msg.encode("utf-8"), codecs.decode(signature, "hex"))
            except binascii.Error:
                return False
            return True
        except nacl.exceptions.BadSignatureError:
            return False



