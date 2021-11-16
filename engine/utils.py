import base64
import hashlib
import logging
import threading

from Crypto import Random
from Crypto.Cipher import AES
from django.conf import settings
from engine.singleton import Singleton


class CryptoUtil(metaclass=Singleton):

    def __init__(self, *args, **kwargs):
        self.block_size = AES.block_size
        self.log = logging.getLogger("db")
        self.key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        super(CryptoUtil, self).__init__(*args, **kwargs)

    def encode(self, value):
        try:
            value = self.pad(value)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return base64.b64encode(iv + cipher.encrypt(value.encode())).decode("utf-8")
        except Exception as e:
            self.log.error("Failed to encrypt", e)
            return None

    def decode(self, value):
        try:
            enc = base64.b64decode(value)
            iv = enc[:AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return self.unpad(cipher.decrypt(enc[AES.block_size:])).decode("utf-8")
        except Exception as e:
            self.log.error("Failed to decrypt ", e)
            return None

    def pad(self, data):
        return data + (self.block_size - len(data) % self.block_size) * chr(
            self.block_size - len(data) % self.block_size)

    def unpad(self, data):
        return data[:-ord(data[len(data) - 1:])]


class ThreadUtil(metaclass=Singleton):

    def __init__(self, *args, **kwargs):
        super(ThreadUtil, self).__init__(*args, **kwargs)

    @staticmethod
    def run_background_process(target, args=()):
        thread = threading.Thread(target=target, args=args)
        thread.setDaemon(True)
        thread.start()
