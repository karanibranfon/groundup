"""
Production-Ready Image Encryption Service

Uses AES-GCM for authenticated encryption and zstandard for compression.
This is the recommended service for medical image encryption.

For legacy data encrypted with DNA-Chaos, use DNACryptoService for decryption
and re-encrypt with this service.
"""

import os
import json
import hashlib
import zstandard
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


KEY_SIZE = 32
NONCE_SIZE = 12
SALT_SIZE = 16
PBKDF2_ITERATIONS = 100000


@dataclass
class CryptoParams:
    nonce: bytes
    salt: bytes
    compressed: bool
    original_size: int
    compressed_size: int


class ProductionCryptoService:
    """
    Production-ready image encryption using AES-GCM and zstandard.
    
    Features:
    - AES-256-GCM: Authenticated encryption (confidentiality + integrity)
    - zstandard compression: High-performance compression for medical images
    - PBKDF2 key derivation: Secure key stretching from master key
    - Nonce-based encryption: Each encryption uses unique nonce
    
    Usage:
        service = ProductionCryptoService(master_key=b"your-256-bit-key")
        encrypted, params = service.encrypt_image(image_data)
        decrypted = service.decrypt_image(encrypted, params)
        
        # With compression (recommended for medical images)
        encrypted, params = service.encrypt_compress_image(image_data)
        decrypted = service.decrypt_decompress_image(encrypted, params)
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize the production crypto service.
        
        Args:
            master_key: 32-byte master key. If not provided, uses environment
                        variable CRYPTO_MASTER_KEY.
                        
        Raises:
            ValueError: If no master key is provided and CRYPTO_MASTER_KEY env var
                        is not set.
        """
        if master_key is None:
            master_key = os.environ.get('CRYPTO_MASTER_KEY', '').encode()
            if not master_key:
                raise ValueError(
                    "CRYPTO_MASTER_KEY environment variable is not set. "
                    "This is required for production environments."
                )
        
        self.master_key = master_key
    
    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derive a 256-bit key from master key using PBKDF2.
        
        Args:
            salt: Random salt for key derivation
            
        Returns:
            32-byte derived key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(self.master_key)
    
    def _generate_salt(self) -> bytes:
        """Generate a random salt for key derivation."""
        return os.urandom(SALT_SIZE)
    
    def _generate_nonce(self) -> bytes:
        """Generate a random nonce for AES-GCM."""
        return os.urandom(NONCE_SIZE)
    
    def encrypt_image(
        self,
        image_data: bytes,
        width: int = 0,
        height: int = 0,
        params: Optional[CryptoParams] = None
    ) -> Tuple[bytes, CryptoParams]:
        """
        Encrypt image data using AES-GCM.
        
        Args:
            image_data: Raw image bytes
            width: Image width (unused, for API compatibility)
            height: Image height (unused, for API compatibility)
            params: Optional pre-computed params (generates new nonce/salt if None)
            
        Returns:
            Tuple of (encrypted bytes, encryption parameters)
        """
        salt = params.salt if params else self._generate_salt()
        nonce = params.nonce if params else self._generate_nonce()
        
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        
        ciphertext = aesgcm.encrypt(nonce, image_data, None)
        
        crypto_params = CryptoParams(
            nonce=nonce,
            salt=salt,
            compressed=False,
            original_size=len(image_data),
            compressed_size=len(ciphertext)
        )
        
        return ciphertext, crypto_params
    
    def decrypt_image(
        self,
        encrypted_data: bytes,
        params: CryptoParams
    ) -> bytes:
        """
        Decrypt image data using AES-GCM.
        
        Args:
            encrypted_data: Encrypted bytes
            params: Encryption parameters (nonce, salt)
            
        Returns:
            Decrypted image bytes
            
        Raises:
            cryptography.exceptions.InvalidTag: If authentication fails
        """
        key = self._derive_key(params.salt)
        aesgcm = AESGCM(key)
        
        return aesgcm.decrypt(params.nonce, encrypted_data, None)
    
    def encrypt_compress_image(
        self,
        image_data: bytes,
        width: int = 0,
        height: int = 0,
        params: Optional[CryptoParams] = None,
        compression_level: int = 3
    ) -> Tuple[bytes, CryptoParams]:
        """
        Compress then encrypt image data (encryption-then-compression).
        
        Args:
            image_data: Raw image bytes
            width: Image width (unused, for API compatibility)
            height: Image height (unused, for API compatibility)
            params: Optional pre-computed params
            compression_level: zstandard compression level (1-22, default 3)
            
        Returns:
            Tuple of (encrypted compressed bytes, parameters)
        """
        cctx = zstandard.ZstdCompressor(level=compression_level)
        compressed_data = cctx.compress(image_data)
        
        salt = params.salt if params else self._generate_salt()
        nonce = params.nonce if params else self._generate_nonce()
        
        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        
        ciphertext = aesgcm.encrypt(nonce, compressed_data, None)
        
        crypto_params = CryptoParams(
            nonce=nonce,
            salt=salt,
            compressed=True,
            original_size=len(image_data),
            compressed_size=len(compressed_data)
        )
        
        return ciphertext, crypto_params
    
    def decrypt_decompress_image(
        self,
        encrypted_data: bytes,
        params: CryptoParams
    ) -> bytes:
        """
        Decrypt then decompress image data.
        
        Args:
            encrypted_data: Encrypted bytes
            params: Encryption parameters
            
        Returns:
            Decrypted and decompressed image bytes
        """
        key = self._derive_key(params.salt)
        aesgcm = AESGCM(key)
        
        decrypted = aesgcm.decrypt(params.nonce, encrypted_data, None)
        
        if params.compressed:
            dctx = zstandard.ZstdDecompressor()
            return dctx.decompress(decrypted)
        
        return decrypted
    
    def params_to_dict(self, params: CryptoParams) -> Dict[str, Any]:
        """Convert CryptoParams to dictionary for storage."""
        return {
            'nonce': params.nonce.hex(),
            'salt': params.salt.hex(),
            'compressed': params.compressed,
            'original_size': params.original_size,
            'compressed_size': params.compressed_size
        }
    
    def dict_to_params(self, data: Dict[str, Any]) -> CryptoParams:
        """Create CryptoParams from dictionary."""
        return CryptoParams(
            nonce=bytes.fromhex(data['nonce']),
            salt=bytes.fromhex(data['salt']),
            compressed=data['compressed'],
            original_size=data['original_size'],
            compressed_size=data['compressed_size']
        )
    
    def params_to_json(self, params: CryptoParams) -> str:
        """Serialize params to JSON string."""
        return json.dumps(self.params_to_dict(params))
    
    def json_to_params(self, json_str: str) -> CryptoParams:
        """Deserialize params from JSON string."""
        return self.dict_to_params(json.loads(json_str))
