from __future__ import annotations

import bcrypt
from cryptography.fernet import Fernet
import base64
import hashlib
import secrets
from typing import Optional


class CryptoManager:
    """加密管理器，使用 PBKDF2 从用户密钥派生 Fernet 兼容密钥"""

    def __init__(self, key: str):
        # 使用 PBKDF2-HMAC-SHA256 从任意长度密钥派生 32 字节密钥
        # 固定盐值确保相同密钥产生相同派生密钥（用于加解密一致性）
        salt = b'niuma_crypto_salt_v1'
        key_bytes = key.encode('utf-8')
        derived_key = hashlib.pbkdf2_hmac('sha256', key_bytes, salt, iterations=100000, dklen=32)
        fernet_key = base64.urlsafe_b64encode(derived_key)
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
