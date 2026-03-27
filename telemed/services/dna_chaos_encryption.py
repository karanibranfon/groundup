"""
DNA-Chaos Image Encryption Service

DEPRECATED: This implementation is based on an academic paper and is NOT recommended
for production use with sensitive medical data.

For production, use ProductionCryptoService which uses:
- AES-256-GCM for authenticated encryption
- zstandard for compression

This class is kept for backward compatibility with existing encrypted data.
To migrate: decrypt with DNACryptoService and re-encrypt with ProductionCryptoService.

Reference: "Robust Medical Image Encryption and Compression Using a DNA-Chaos Cryptosystem"
Ahmed et al., The Journal of Engineering, 2025
"""

import hashlib
import struct
import warnings
import numpy as np
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass


DNA_BASES = ['A', 'T', 'G', 'C']

DNA_RULES = {
    1: {'00': 'A', '01': 'T', '10': 'G', '11': 'C'},
    2: {'00': 'A', '01': 'T', '10': 'C', '11': 'G'},
    3: {'00': 'G', '01': 'C', '10': 'A', '11': 'T'},
    4: {'00': 'G', '01': 'T', '10': 'A', '11': 'C'},
    5: {'00': 'C', '01': 'A', '10': 'G', '11': 'T'},
    6: {'00': 'C', '01': 'T', '10': 'A', '11': 'G'},
    7: {'00': 'T', '01': 'A', '10': 'C', '11': 'G'},
    8: {'00': 'T', '01': 'C', '10': 'A', '11': 'G'},
}

DNA_COMPLEMENT = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}


@dataclass
class EncryptionParams:
    """Parameters used for DNA-Chaos encryption."""
    dna_rule: int
    pwlc_p: float
    pwlc_x0: float
    sha256_hash: str
    image_width: int
    image_height: int


class PWLCMChaoticMap:
    """
    Piecewise Linear Chaotic Map (PWLCM) implementation.
    
    The PWLCM is defined as:
        x_{n+1} = f(x_n, p) where:
        - 0 < x_n < p:     x_{n+1} = x_n / p
        - p <= x_n < 0.5:  x_{n+1} = (x_n - p) / (0.5 - p)
        - 0.5 <= x_n < 1: x_{n+1} = f_p(1 - x_n)
    """
    
    def __init__(self, x0: float, p: float):
        if not (0 < x0 < 1):
            raise ValueError("Initial value x0 must be in (0, 1)")
        if not (0 < p < 0.5):
            raise ValueError("Control parameter p must be in (0, 0.5)")
        
        self.x = x0
        self.p = p
    
    def iterate(self, n: int = 1) -> np.ndarray:
        """
        Perform n iterations of the PWLCM.
        
        Args:
            n: Number of iterations
            
        Returns:
            Array of n random values in [0, 1]
        """
        values = np.zeros(n)
        x = self.x
        
        for i in range(n):
            if 0 < x < self.p:
                x = x / self.p
            elif self.p <= x < 0.5:
                x = (x - self.p) / (0.5 - self.p)
            else:
                x = self._fp(1 - x)
            
            values[i] = x
        
        self.x = x
        return values
    
    def _fp(self, x: float) -> float:
        """Helper function for PWLCM."""
        if 0 < x < self.p:
            return x / self.p
        elif self.p <= x < 0.5:
            return (x - self.p) / (0.5 - self.p)
        else:
            return (1 - x) / (1 - 0.5)
    
    def reset(self, x0: float):
        """Reset the map to a new initial value."""
        self.x = x0


class ArithmeticCoder:
    """
    Arithmetic coding for lossless compression of DNA sequences.
    
    Uses a simple frequency-based model for the four DNA bases.
    """
    
    def __init__(self):
        self.precision = 32
        self.integer_bits = 16
        self.full_range = 1 << self.integer_bits
        self.half_range = self.full_range >> 1
        self.quarter_range = self.half_range >> 1
    
    def encode(self, data: str) -> Tuple[bytes, Dict[str, float]]:
        """
        Encode a DNA sequence.
        
        Args:
            data: DNA sequence string (A, T, G, C)
            
        Returns:
            Tuple of (compressed bytes, frequency table)
        """
        if not data:
            return b'', {}
        
        freq = self._calculate_frequencies(data)
        total = len(data)
        
        low = 0
        high = self.full_range - 1
        scale = 0
        result = []
        
        for symbol in data:
            range_size = high - low + 1
            symbol_low, symbol_high = self._get_symbol_range(symbol, freq, total)
            
            high = low + int((range_size * symbol_high) / total) - 1
            low = low + int((range_size * symbol_low) / total)
            
            self._normalize(low, high, result, lambda: scale)
        
        final_value = (low + high) >> 1
        result.append(final_value)
        
        return struct.pack(f'<{len(result)}I', *result), freq
    
    def decode(self, encoded: bytes, freq: Dict[str, float], length: int) -> str:
        """
        Decode an arithmetic encoded DNA sequence.
        
        Args:
            encoded: Compressed bytes
            freq: Frequency table used during encoding
            length: Original sequence length
            
        Returns:
            Decoded DNA sequence
        """
        if not encoded:
            return ""
        
        values = struct.unpack(f'<{len(encoded) // 4}I', encoded)
        value = values[0]
        
        low = 0
        high = self.full_range - 1
        total = sum(freq.values())
        result = []
        
        for _ in range(length):
            range_size = high - low + 1
            scaled_value = ((value - low + 1) * total - 1) // range_size
            
            symbol = self._find_symbol(scaled_value, freq, total)
            result.append(symbol)
            
            symbol_low, symbol_high = self._get_symbol_range(symbol, freq, total)
            high = low + int((range_size * symbol_high) / total) - 1
            low = low + int((range_size * symbol_low) / total)
            
            self._denormalize(value, low, high)
        
        return ''.join(result)
    
    def _calculate_frequencies(self, data: str) -> Dict[str, float]:
        """Calculate symbol frequencies."""
        freq = {base: 0 for base in DNA_BASES}
        for char in data:
            if char in freq:
                freq[char] += 1
        return freq
    
    def _get_symbol_range(self, symbol: str, freq: Dict[str, float], total: int) -> Tuple[int, int]:
        """Get the range for a symbol."""
        cumsum = 0
        for base in DNA_BASES:
            if base == symbol:
                return cumsum, cumsum + int(freq[base])
            cumsum += int(freq[base])
        return 0, 0
    
    def _find_symbol(self, value: int, freq: Dict[str, float], total: int) -> str:
        """Find the symbol for a given value."""
        cumsum = 0
        for base in DNA_BASES:
            cumsum += int(freq[base])
            if value < cumsum:
                return base
        return DNA_BASES[-1]
    
    def _normalize(self, low: int, high: int, result: list, get_scale: callable):
        """Normalize the interval during encoding."""
        while True:
            if high < self.half_range:
                result.append(0)
                get_scale()  # scale
            elif low >= self.half_range:
                result.append(1)
                low -= self.half_range
                high -= self.half_range
                get_scale()  # scale
            elif low >= self.quarter_range and high < 3 * self.quarter_range:
                get_scale()  # scale
                low -= self.quarter_range
                high -= self.quarter_range
            else:
                break
    
    def _denormalize(self, value: int, low: int, high: int):
        """Denormalize during decoding."""
        pass


class DNACryptoService:
    """
    DNA-Chaos Image Encryption Service.
    
    DEPRECATED: This implementation is based on an academic paper and is NOT
    recommended for production use with sensitive medical data.
    
    Implements the ITIEDC algorithm for secure medical image encryption
    using DNA encoding, chaotic maps, and one-time pad.
    
    Use ProductionCryptoService for new encryptions.
    This class is kept for backward compatibility with existing encrypted data.
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize the DNA encryption service.
        
        Args:
            master_key: Optional master key for encrypting OTP keys in storage.
                       If not provided, OTP keys are stored as-is (not recommended for production).
        """
        warnings.warn(
            "DNACryptoService is deprecated. It uses academic cryptography that is "
            "not suitable for production medical image encryption. "
            "Use ProductionCryptoService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.master_key = master_key or b'default_master_key_change_in_production'
        self.arithmetic_coder = ArithmeticCoder()
    
    def sha256_to_initial_values(self, data: bytes) -> Dict[str, Any]:
        """
        Derive encryption parameters from SHA-256 hash.
        
        Args:
            data: Input data to hash
            
        Returns:
            Dictionary with derived values (dna_rule, pwlc_p, pwlc_x0, hash_bytes)
        """
        hash_bytes = hashlib.sha256(data).digest()
        hash_hex = hashlib.sha256(data).hexdigest()
        
        d1 = hash_bytes[0] / 255.0
        d2 = hash_bytes[1] / 255.0
        d3 = hash_bytes[2] / 255.0
        d4 = hash_bytes[3] / 255.0
        
        dna_rule = (hash_bytes[4] % 8) + 1
        
        pwlc_p = 0.1 + (d1 * 0.39)
        
        pwlc_x0 = d2
        
        return {
            'dna_rule': dna_rule,
            'pwlc_p': pwlc_p,
            'pwlc_x0': pwlc_x0,
            'sha256_hash': hash_hex,
            'hash_bytes': hash_bytes
        }
    
    def pwlc_map(self, x0: float, p: float, iterations: int) -> np.ndarray:
        """
        Generate chaotic sequence using PWLCM.
        
        Args:
            x0: Initial value in (0, 1)
            p: Control parameter in (0, 0.5)
            iterations: Number of iterations
            
        Returns:
            Array of chaotic values in [0, 1]
        """
        pwlc = PWLCMChaoticMap(x0, p)
        return pwlc.iterate(iterations)
    
    def dna_encode_byte(self, byte_value: int, rule: int) -> str:
        """
        Encode a single byte (0-255) to 4 DNA bases.
        
        Args:
            byte_value: Byte value (0-255)
            rule: DNA encoding rule (1-8)
            
        Returns:
            String of 4 DNA bases (e.g., "ATGC")
        """
        binary = format(byte_value, '08b')
        pairs = [binary[i:i+2] for i in range(0, 8, 2)]
        mapping = DNA_RULES[rule]
        return ''.join(mapping.get(pair, 'A') for pair in pairs)
    
    def dna_decode_byte(self, dna_bases: str, rule: int) -> int:
        """
        Decode 4 DNA bases back to a byte.
        
        Args:
            dna_bases: String of 4 DNA bases
            rule: DNA encoding rule (1-8)
            
        Returns:
            Decoded byte value (0-255)
        """
        reverse_mapping = {v: k for k, v in DNA_RULES[rule].items()}
        binary = ''.join(reverse_mapping.get(base, '00') for base in dna_bases)
        return int(binary, 2)
    
    def dna_encode_image(self, image_data: bytes, rule: int) -> str:
        """
        Encode entire image bytes to DNA sequence.
        
        Args:
            image_data: Raw image bytes
            rule: DNA encoding rule (1-8)
            
        Returns:
            DNA sequence string
        """
        return ''.join(
            self.dna_encode_byte(byte, rule) 
            for byte in image_data
        )
    
    def dna_decode_image(self, dna_sequence: str, rule: int, length: int) -> bytes:
        """
        Decode DNA sequence back to image bytes.
        
        Args:
            dna_sequence: DNA sequence string
            rule: DNA encoding rule (1-8)
            length: Expected number of bytes
            
        Returns:
            Raw image bytes
        """
        result = []
        for i in range(length):
            dna_bases = dna_sequence[i*4:(i+1)*4]
            if len(dna_bases) == 4:
                result.append(self.dna_decode_byte(dna_bases, rule))
        return bytes(result)
    
    def dna_xor_operation(self, dna1: str, dna2: str, rule: int) -> str:
        """
        Perform DNA XOR operation between two DNA sequences.
        
        The DNA XOR follows the rule: result = DNA_XOR(seq1, seq2)
        using the DNA encoding table.
        
        Args:
            dna1: First DNA sequence
            dna2: Second DNA sequence (same length)
            rule: DNA encoding rule (1-8)
            
        Returns:
            XOR result as DNA sequence
        """
        if len(dna1) != len(dna2):
            raise ValueError("DNA sequences must have same length")
        
        xor_mapping = self._build_dna_xor_table(rule)
        
        result = []
        for base1, base2 in zip(dna1, dna2):
            result.append(xor_mapping.get((base1, base2), 'A'))
        
        return ''.join(result)
    
    def _build_dna_xor_table(self, rule: int) -> Dict[Tuple[str, str], str]:
        """
        Build XOR mapping table for DNA bases based on encoding rule.
        
        The XOR operation is defined using binary representation:
        A=00, C=01, G=10, T=11 (adapted per rule)
        """
        rule_mapping = DNA_RULES[rule]
        
        reverse_map = {v: k for k, v in rule_mapping.items()}
        
        xor_table = {}
        for base1 in DNA_BASES:
            for base2 in DNA_BASES:
                code1 = reverse_map.get(base1, '00')
                code2 = reverse_map.get(base2, '00')
                
                xor_code = format(int(code1, 2) ^ int(code2, 2), '02b')
                
                xor_table[(base1, base2)] = rule_mapping.get(xor_code, 'A')
        
        return xor_table
    
    def generate_otp_key(self, chaotic_seq: np.ndarray, length: int) -> str:
        """
        Generate One-Time Pad key from chaotic sequence.
        
        Args:
            chaotic_seq: Chaotic values from PWLCM
            length: Required length of OTP key (in DNA bases)
            
        Returns:
            OTP key as DNA sequence
        """
        otp = []
        for i in range(length):
            idx = int(chaotic_seq[i % len(chaotic_seq)] * 4) % 4
            otp.append(DNA_BASES[idx])
        return ''.join(otp)
    
    def encrypt_image(
        self, 
        image_data: bytes, 
        width: int, 
        height: int,
        params: Optional[EncryptionParams] = None
    ) -> Tuple[bytes, EncryptionParams]:
        """
        Encrypt image using ITIED algorithm.
        
        Steps:
        1. SHA-256 hash → derive DNA rule and PWLCM params
        2. PWLCM → generate chaotic sequence
        3. DNA encode image
        4. Generate OTP key from chaotic sequence
        5. DNA XOR: encoded_image ⊕ OTP_key
        
        Args:
            image_data: Raw image bytes
            width: Image width
            height: Image height
            params: Optional pre-computed encryption params
            
        Returns:
            Tuple of (encrypted bytes, encryption parameters)
        """
        if params is None:
            derived = self.sha256_to_initial_values(image_data)
            params = EncryptionParams(
                dna_rule=derived['dna_rule'],
                pwlc_p=derived['pwlc_p'],
                pwlc_x0=derived['pwlc_x0'],
                sha256_hash=derived['sha256_hash'],
                image_width=width,
                image_height=height
            )
        
        dna_encoded = self.dna_encode_image(image_data, params.dna_rule)
        
        num_otp_chars = len(dna_encoded)
        chaotic_seq = self.pwlc_map(params.pwlc_x0, params.pwlc_p, num_otp_chars)
        
        otp_key = self.generate_otp_key(chaotic_seq, num_otp_chars)
        
        encrypted_dna = self.dna_xor_operation(dna_encoded, otp_key, params.dna_rule)
        
        encrypted_bytes = encrypted_dna.encode('utf-8')
        
        return encrypted_bytes, params
    
    def decrypt_image(
        self,
        encrypted_data: bytes,
        params: EncryptionParams
    ) -> bytes:
        """
        Decrypt image using ITIED algorithm (reverse of encryption).
        
        Args:
            encrypted_data: Encrypted image bytes
            params: Encryption parameters used for encryption
            
        Returns:
            Decrypted image bytes
        """
        encrypted_dna = encrypted_data.decode('utf-8')
        
        num_chars = len(encrypted_dna)
        chaotic_seq = self.pwlc_map(params.pwlc_x0, params.pwlc_p, num_chars)
        
        otp_key = self.generate_otp_key(chaotic_seq, num_chars)
        
        decrypted_dna = self.dna_xor_operation(encrypted_dna, otp_key, params.dna_rule)
        
        original_bytes = self.dna_decode_image(
            decrypted_dna, 
            params.dna_rule, 
            num_chars // 4
        )
        
        return original_bytes
    
    def encrypt_compress_image(
        self,
        image_data: bytes,
        width: int,
        height: int,
        params: Optional[EncryptionParams] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Encrypt and compress image using ITIEDC algorithm.
        
        Steps:
        1. SHA-256 hash → derive params
        2. DNA encode image
        3. Arithmetic coding compression
        4. PWLCM → generate chaotic sequence
        5. DNA encode OTP key
        6. DNA XOR compression ⊕ OTP_key
        
        Args:
            image_data: Raw image bytes
            width: Image width
            height: Image height
            params: Optional pre-computed encryption params
            
        Returns:
            Tuple of (encrypted+compressed bytes, metadata)
        """
        if params is None:
            derived = self.sha256_to_initial_values(image_data)
            params = EncryptionParams(
                dna_rule=derived['dna_rule'],
                pwlc_p=derived['pwlc_p'],
                pwlc_x0=derived['pwlc_x0'],
                sha256_hash=derived['sha256_hash'],
                image_width=width,
                image_height=height
            )
        
        dna_encoded = self.dna_encode_image(image_data, params.dna_rule)
        
        compressed_data, freq = self.arithmetic_coder.encode(dna_encoded)
        
        compressed_dna = compressed_data.decode('utf-8') if compressed_data else dna_encoded
        
        num_otp_chars = len(compressed_dna)
        chaotic_seq = self.pwlc_map(params.pwlc_x0, params.pwlc_p, num_otp_chars)
        
        otp_key = self.generate_otp_key(chaotic_seq, num_otp_chars)
        
        encrypted_dna = self.dna_xor_operation(compressed_dna, otp_key, params.dna_rule)
        
        metadata = {
            'params': params,
            'frequency': freq,
            'original_length': len(image_data),
            'dna_length': len(dna_encoded),
            'compressed_length': len(compressed_data) if compressed_data else 0
        }
        
        return encrypted_dna.encode('utf-8'), metadata
    
    def decrypt_decompress_image(
        self,
        encrypted_data: bytes,
        metadata: Dict[str, Any]
    ) -> bytes:
        """
        Decrypt and decompress image.
        
        Args:
            encrypted_data: Encrypted+compressed bytes
            metadata: Encryption metadata including params and frequency
            
        Returns:
            Decrypted image bytes
        """
        params = metadata['params']
        freq = metadata['frequency']
        original_length = metadata['original_length']
        dna_length = metadata['dna_length']
        
        encrypted_dna = encrypted_data.decode('utf-8')
        
        num_chars = len(encrypted_dna)
        chaotic_seq = self.pwlc_map(params.pwlc_x0, params.pwlc_p, num_chars)
        
        otp_key = self.generate_otp_key(chaotic_seq, num_chars)
        
        decrypted_dna = self.dna_xor_operation(encrypted_dna, otp_key, params.dna_rule)
        
        if metadata['compressed_length'] > 0:
            decompressed_dna = self.arithmetic_coder.decode(
                decrypted_dna.encode('utf-8'),
                freq,
                dna_length
            )
        else:
            decompressed_dna = decrypted_dna
        
        original_bytes = self.dna_decode_image(
            decompressed_dna,
            params.dna_rule,
            original_length
        )
        
        return original_bytes
    
    def encrypt_otp_key(self, otp_key: bytes) -> bytes:
        """
        Encrypt OTP key using master key for secure storage.
        
        Uses simple XOR encryption with SHA-256 derived key.
        For production, use proper authenticated encryption (e.g., AES-GCM).
        
        Args:
            otp_key: Raw OTP key bytes
            
        Returns:
            Encrypted OTP key
        """
        key_hash = hashlib.sha256(self.master_key).digest()
        
        encrypted = bytearray(otp_key)
        for i in range(len(encrypted)):
            encrypted[i] ^= key_hash[i % len(key_hash)]
        
        return bytes(encrypted)
    
    def decrypt_otp_key(self, encrypted_otp: bytes) -> bytes:
        """
        Decrypt OTP key using master key.
        
        Args:
            encrypted_otp: Encrypted OTP key
            
        Returns:
            Decrypted OTP key
        """
        return self.encrypt_otp_key(encrypted_otp)
    
    def params_to_dict(self, params: EncryptionParams) -> Dict[str, Any]:
        """Convert EncryptionParams to dictionary for storage."""
        return {
            'dna_rule': params.dna_rule,
            'pwlc_p': params.pwlc_p,
            'pwlc_x0': params.pwlc_x0,
            'sha256_hash': params.sha256_hash,
            'image_width': params.image_width,
            'image_height': params.image_height
        }
    
    def dict_to_params(self, data: Dict[str, Any]) -> EncryptionParams:
        """Create EncryptionParams from dictionary."""
        return EncryptionParams(
            dna_rule=data['dna_rule'],
            pwlc_p=data['pwlc_p'],
            pwlc_x0=data['pwlc_x0'],
            sha256_hash=data['sha256_hash'],
            image_width=data['image_width'],
            image_height=data['image_height']
        )


def calculate_npcr(original: bytes, encrypted: bytes) -> float:
    """
    Calculate Number of Pixel Changing Rate (NPCR).
    
    Measures percentage of different pixels between two images.
    Higher value indicates better diffusion.
    
    Args:
        original: Original image bytes
        encrypted: Encrypted image bytes
        
    Returns:
        NPCR percentage (0-100)
    """
    if len(original) != len(encrypted):
        return 100.0
    
    diff = sum(1 for a, b in zip(original, encrypted) if a != b)
    return (diff / len(original)) * 100


def calculate_uaci(original: bytes, encrypted: bytes) -> float:
    """
    Calculate Unified Average Changing Intensity (UACI).
    
    Measures average intensity difference between two images.
    
    Args:
        original: Original image bytes
        encrypted: Encrypted image bytes
        
    Returns:
        UACI percentage (0-100)
    """
    if len(original) != len(encrypted):
        return 50.0
    
    total = sum(abs(a - b) for a, b in zip(original, encrypted))
    max_diff = 255 * len(original)
    
    return (total / max_diff) * 100


def calculate_entropy(data: bytes) -> float:
    """
    Calculate Shannon entropy of data.
    
    Higher entropy (close to 8 for bytes) indicates better randomness.
    
    Args:
        data: Data bytes
        
    Returns:
        Entropy value (0-8 for byte data)
    """
    if not data:
        return 0.0
    
    frequency = [0] * 256
    for byte in data:
        frequency[byte] += 1
    
    entropy = 0.0
    length = len(data)
    
    for freq in frequency:
        if freq > 0:
            p = freq / length
            entropy -= p * (p.bit_length() - 1 + (1 / length if freq == 1 else 0))
    
    return entropy
