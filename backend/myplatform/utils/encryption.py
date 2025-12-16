"""
Encryption utilities for MyPlatform.
Provides AES encryption/decryption for sensitive data.
Ported from ee/esa/utils/encryption.py
"""
from functools import lru_cache
from os import urandom

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import modes

from esa.configs.app_configs import ENCRYPTION_KEY_SECRET
from esa.utils.logger import setup_logger
from esa.utils.variable_functionality import fetch_versioned_implementation

logger = setup_logger()


@lru_cache(maxsize=1)
def _get_trimmed_key(key: str) -> bytes:
    """
    Get a properly sized encryption key.
    
    AES requires keys of 16, 24, or 32 bytes.
    This function trims the key to the appropriate length.
    
    Args:
        key: The encryption key string
        
    Returns:
        Properly sized key as bytes
        
    Raises:
        RuntimeError: If the key is too short
    """
    encoded_key = key.encode()
    key_length = len(encoded_key)
    if key_length < 16:
        raise RuntimeError("Invalid ENCRYPTION_KEY_SECRET - too short (minimum 16 characters)")
    elif key_length > 32:
        key = key[:32]
    elif key_length not in (16, 24, 32):
        valid_lengths = [16, 24, 32]
        key = key[: min(valid_lengths, key=lambda x: abs(x - key_length))]

    return encoded_key


def _encrypt_string(input_str: str) -> bytes:
    """
    Encrypt a string using AES encryption.
    
    Args:
        input_str: The string to encrypt
        
    Returns:
        Encrypted bytes (IV + ciphertext)
    """
    if not ENCRYPTION_KEY_SECRET:
        return input_str.encode()

    key = _get_trimmed_key(ENCRYPTION_KEY_SECRET)
    iv = urandom(16)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(input_str.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    return iv + encrypted_data


def _decrypt_bytes(input_bytes: bytes) -> str:
    """
    Decrypt bytes using AES decryption.
    
    Args:
        input_bytes: The encrypted bytes (IV + ciphertext)
        
    Returns:
        Decrypted string
    """
    if not ENCRYPTION_KEY_SECRET:
        return input_bytes.decode()

    key = _get_trimmed_key(ENCRYPTION_KEY_SECRET)
    iv = input_bytes[:16]
    encrypted_data = input_bytes[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

    return decrypted_data.decode()


def encrypt_string_to_bytes(input_str: str) -> bytes:
    """
    Public API for encrypting a string.
    Uses versioned implementation for compatibility.
    
    Args:
        input_str: The string to encrypt
        
    Returns:
        Encrypted bytes
    """
    versioned_encryption_fn = fetch_versioned_implementation(
        "esa.utils.encryption", "_encrypt_string"
    )
    return versioned_encryption_fn(input_str)


def decrypt_bytes_to_string(input_bytes: bytes) -> str:
    """
    Public API for decrypting bytes.
    Uses versioned implementation for compatibility.
    
    Args:
        input_bytes: The encrypted bytes
        
    Returns:
        Decrypted string
    """
    versioned_decryption_fn = fetch_versioned_implementation(
        "esa.utils.encryption", "_decrypt_bytes"
    )
    return versioned_decryption_fn(input_bytes)


def test_encryption() -> None:
    """
    Test that encryption/decryption is working correctly.
    Should be called during application startup.
    
    Raises:
        RuntimeError: If encryption test fails
    """
    test_string = "MyPlatform encryption test!"
    encrypted_bytes = encrypt_string_to_bytes(test_string)
    decrypted_string = decrypt_bytes_to_string(encrypted_bytes)
    if test_string != decrypted_string:
        raise RuntimeError("Encryption decryption test failed")
    logger.debug("Encryption test passed")
