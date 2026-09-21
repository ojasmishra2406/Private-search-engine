import hashlib
import struct

def string_to_int64(s: str) -> int:
    """
    Deterministically converts a string (like a SHA-256 ID) into a signed 64-bit integer
    for compatibility with FAISS IndexIDMap.
    """
    # Use blake2b or md5 to get 8 bytes, unpack as signed long long
    h = hashlib.blake2b(s.encode('utf-8'), digest_size=8).digest()
    return struct.unpack('<q', h)[0]
