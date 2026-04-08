import bcrypt
from cryptography.fernet import Fernet
import base64
import secrets
from typing import Optional

class CryptoManager:
    def __init__(self, key: str):
        # 确保 key 是 32 字节
        if len(key.encode()) < 32:
            key = key.ljust(32, '0')
        elif len(key.encode()) > 32:
            key = key[:32]

        # 生成 Fernet key
        fernet_key = base64.urlsafe_b64encode(key.encode()[:32])
        self.cipher = Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def generate_token() -> str:
    return secrets.token_urlsafe(32)
