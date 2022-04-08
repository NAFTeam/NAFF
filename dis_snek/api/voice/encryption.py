__all__ = ["Encryption", "Decryption"]

from abc import ABC, abstractmethod

try:
    from nacl import secret, utils

    nacl_imported = True
except ImportError:
    nacl_imported = False


class Crypt(ABC):
    SUPPORTED = (
        "xsalsa20_poly1305_suffix",
        "xsalsa20_poly1305",
    )

    def __init__(self, secret_key) -> None:
        if not nacl_imported:
            raise RuntimeError("Please install dis-snek[voice] to use voice components.")
        self.box: secret.SecretBox = secret.SecretBox(bytes(secret_key))

    @abstractmethod
    def xsalsa20_poly1305_suffix(self, header: bytes, data) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def xsalsa20_poly1305(self, header: bytes, data) -> bytes:
        raise NotImplementedError


class Encryption(Crypt):
    def encrypt(self, mode: str, header: bytes, data) -> bytes:
        match mode:
            case "xsalsa20_poly1305_suffix":
                return self.xsalsa20_poly1305_suffix(header, data)
            case "xsalsa20_poly1305":
                return self.xsalsa20_poly1305(header, data)
            case _:
                raise RuntimeError(f"Unsupported encryption type requested: {mode}")

    def xsalsa20_poly1305_suffix(self, header: bytes, data) -> bytes:
        nonce = utils.random(secret.SecretBox.NONCE_SIZE)
        return header + self.box.encrypt(bytes(data), nonce).ciphertext + nonce

    def xsalsa20_poly1305(self, header: bytes, data) -> bytes:
        nonce = bytearray(24)
        nonce[:12] = header

        return header + self.box.encrypt(bytes(data), bytes(nonce)).ciphertext


class Decryption(Crypt):
    def decrypt(self, mode: str, header: bytes, data) -> bytes:
        match mode:
            case "xsalsa20_poly1305_suffix":
                return self.xsalsa20_poly1305_suffix(header, data)
            case "xsalsa20_poly1305":
                return self.xsalsa20_poly1305(header, data)
            case _:
                raise RuntimeError(f"Unsupported decryption type requested: {mode}")

    def xsalsa20_poly1305_suffix(self, header: bytes, data) -> bytes:
        nonce = data[-24:]

        return self.box.decrypt(bytes(data[:-24]), bytes(nonce))

    def xsalsa20_poly1305(self, header: bytes, data) -> bytes:
        nonce = bytearray(24)
        nonce[:12] = header

        return self.box.decrypt(bytes(data), bytes(nonce))
