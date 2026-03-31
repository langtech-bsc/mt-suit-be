"""Encryption service for sensitive data.

This module provides encryption and decryption functionality using Fernet
symmetric encryption for storing sensitive data like API keys in the database.
"""

from cryptography.fernet import Fernet


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, encryption_key: str):
        """Initialize the encryption service.

        Args:
            encryption_key: The Fernet encryption key (must be a valid Fernet key)
        """
        self.cipher = Fernet(encryption_key.encode())

    def encrypt(self, plain_text: str) -> str:
        """Encrypt plain text.

        Args:
            plain_text: The text to encrypt

        Returns:
            The encrypted text as a string
        """
        encrypted_bytes = self.cipher.encrypt(plain_text.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt encrypted text.

        Args:
            encrypted_text: The encrypted text to decrypt

        Returns:
            The decrypted plain text

        Raises:
            cryptography.fernet.InvalidToken: If the encryption key is invalid
                or the text was not encrypted with this key
        """
        decrypted_bytes = self.cipher.decrypt(encrypted_text.encode())
        return decrypted_bytes.decode()
