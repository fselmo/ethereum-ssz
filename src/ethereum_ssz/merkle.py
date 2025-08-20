"""SSZ Merkleization - hash_tree_root implementation."""

import hashlib
from collections.abc import Sequence
from typing import Any, Optional, Union

from ethereum_types.bytes import Bytes, Bytes32, FixedBytes
from ethereum_types.numeric import U8, U32, U64, U256, FixedUnsigned, Uint

from .composite import List as SSZList
from .composite import Vector
from .container import Container
from .types import U16, U128

# Merkle tree constants
BYTES_PER_CHUNK = 32
BITS_PER_BYTE = 8


def hash(data: bytes) -> Bytes32:
    """
    SHA256 hash function returning Bytes32.

    SSZ uses SHA256 for merkleization.
    """
    return Bytes32(hashlib.sha256(data).digest())


def hash_tree_root(value: Any) -> Bytes32:
    """
    Calculate the SSZ hash tree root of a value.

    This is the main entry point for merkleization.
    """
    # Import here to avoid circular dependency
    from .bitfields import Bitlist, Bitvector
    from .union import Union

    if isinstance(value, bool):
        return hash_tree_root_bool(value)
    elif isinstance(value, (Uint, FixedUnsigned)):
        return hash_tree_root_uint(value)
    elif isinstance(value, (bytes, Bytes, FixedBytes)):
        return hash_tree_root_bytes(value)
    elif isinstance(value, Container):
        return value.hash_tree_root()
    elif isinstance(value, Bitvector):
        return hash_tree_root_bitvector(value)
    elif isinstance(value, Bitlist):
        return hash_tree_root_bitlist(value)
    elif isinstance(value, Union):
        return value.hash_tree_root()
    elif isinstance(value, Vector):
        return hash_tree_root_vector(value)
    elif isinstance(value, SSZList):
        return hash_tree_root_list(value)
    else:
        raise NotImplementedError(
            f"hash_tree_root not implemented for {type(value)}"
        )


def hash_tree_root_bool(value: bool) -> Bytes32:
    """
    Hash tree root of a boolean.

    Booleans are packed as a single byte in a 32-byte chunk.
    """
    chunk = bytes([0x01 if value else 0x00]) + b"\x00" * 31
    return Bytes32(chunk)


def hash_tree_root_uint(value: Union[Uint, FixedUnsigned]) -> Bytes32:
    """
    Hash tree root of an unsigned integer.

    Integers are packed little-endian in a 32-byte chunk.
    """
    # Determine byte length
    if isinstance(value, FixedUnsigned):
        bits = value.MAX_VALUE._number.bit_length()
        byte_length = (bits + 7) // 8
    else:
        # For Uint, pack as minimal bytes up to 32
        if value == 0:
            byte_length = 1
        else:
            byte_length = min(32, (value.bit_length() + 7) // 8)

    # Convert to little-endian bytes and pad to 32 bytes
    le_bytes = value.to_bytes(byte_length, byteorder="little")
    if len(le_bytes) < 32:
        le_bytes = le_bytes + b"\x00" * (32 - len(le_bytes))

    return Bytes32(le_bytes)


def hash_tree_root_bytes(value: Union[bytes, Bytes, FixedBytes]) -> Bytes32:
    """
    Hash tree root of bytes.

    For fixed-size bytes <= 32, pack directly.
    For larger or variable-size, merkleize chunks.
    """
    data = bytes(value)

    if len(data) <= 32:
        # Pack directly in a chunk with zero padding
        padded = data + b"\x00" * (32 - len(data))
        return Bytes32(padded)
    else:
        # Split into chunks and merkleize
        chunks = pack_bytes(data)
        return merkleize(chunks)


def hash_tree_root_vector(vector: Vector[Any]) -> Bytes32:
    """
    Hash tree root of a fixed-length vector.

    For vectors of basic types that pack efficiently, pack them first.
    Otherwise, merkleize all elements.
    """
    # Check if this is a packed vector (basic types)
    if is_basic_type(vector.element_type):
        # Pack elements into chunks
        chunks = pack_vector_to_chunks(vector)
        if len(chunks) == 1:
            # Single chunk - return it directly
            return chunks[0]
        else:
            # Multiple chunks - merkleize them
            return merkleize(chunks)
    else:
        # Complex type - merkleize each element separately
        roots = [hash_tree_root(elem) for elem in vector.elements]
        return merkleize(roots)


def hash_tree_root_list(ssz_list: SSZList[Any]) -> Bytes32:
    """
    Hash tree root of a variable-length list.

    Merkleize elements and mix with length.
    """
    # Check if this is a packed list (basic types)
    if is_basic_type(ssz_list.element_type):
        # Pack elements into chunks
        chunks = pack_list_to_chunks(ssz_list)

        # Calculate the limit in chunks
        elem_size = get_basic_type_size(ssz_list.element_type)
        elems_per_chunk = 32 // elem_size
        max_chunks = (
            ssz_list.max_length + elems_per_chunk - 1
        ) // elems_per_chunk

        # Merkleize with proper limit
        elements_root = merkleize(chunks, limit=max_chunks)
    else:
        # Complex type - merkleize each element separately
        roots = [hash_tree_root(elem) for elem in ssz_list.elements]
        elements_root = merkleize(roots, limit=ssz_list.max_length)

    # Mix in the length
    length_bytes = len(ssz_list.elements).to_bytes(32, byteorder="little")
    return hash(elements_root + length_bytes)


def pack_bytes(data: bytes) -> list[Bytes32]:
    """Pack bytes into 32-byte chunks."""
    chunks = []
    for i in range(0, len(data), BYTES_PER_CHUNK):
        chunk = data[i : i + BYTES_PER_CHUNK]
        if len(chunk) < BYTES_PER_CHUNK:
            chunk = chunk + b"\x00" * (BYTES_PER_CHUNK - len(chunk))
        chunks.append(Bytes32(chunk))
    return chunks


def merkleize(
    chunks: Sequence[Bytes32], limit: Optional[int] = None
) -> Bytes32:
    """
    Merkleize a sequence of chunks.

    Build a binary merkle tree and return the root.
    If limit is specified, pad to the next power of 2 up to limit.
    """
    # Calculate the size of the tree
    if limit is not None:
        # Use limit to determine tree size
        size = next_power_of_2(limit)
    else:
        if not chunks:
            # Empty tree with no limit
            return Bytes32(b"\x00" * 32)
        size = next_power_of_2(len(chunks))

    # If empty chunks but with a limit, return the zero hash for that depth
    if not chunks:
        # Calculate the depth of the tree
        depth = 0
        temp_size = size
        while temp_size > 1:
            temp_size //= 2
            depth += 1

        # Return the appropriate zero hash for this depth
        return get_zero_hash(depth)

    # Pad with zero hashes if needed
    padded_chunks = list(chunks)
    while len(padded_chunks) < size:
        padded_chunks.append(Bytes32(b"\x00" * 32))

    # Build merkle tree bottom-up
    layer = padded_chunks
    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = (
                layer[i + 1] if i + 1 < len(layer) else Bytes32(b"\x00" * 32)
            )
            next_layer.append(hash(left + right))
        layer = next_layer

    return layer[0]


# Precompute zero hashes
_zero_hashes_cache = None


def get_zero_hash(depth: int) -> Bytes32:
    """
    Get the zero hash at a given depth.

    Zero hashes are precomputed for efficiency.
    """
    global _zero_hashes_cache

    if _zero_hashes_cache is None:
        # Initialize zero hashes
        _zero_hashes_cache = [Bytes32(b"\x00" * 32)]
        for i in range(1, 64):  # Support up to depth 63
            prev = _zero_hashes_cache[i - 1]
            _zero_hashes_cache.append(hash(prev + prev))

    if depth >= len(_zero_hashes_cache):
        raise ValueError(f"Depth {depth} exceeds maximum supported depth")

    return _zero_hashes_cache[depth]


def next_power_of_2(n: int) -> int:
    """Get the next power of 2 greater than or equal to n."""
    if n <= 1:
        return 1
    power = 1
    while power < n:
        power *= 2
    return power


def is_basic_type(type_: type) -> bool:
    """Check if a type is a basic SSZ type that can be packed."""
    # Check for basic integer types
    basic_types = (bool, U8, U16, U32, U64, U128, U256, FixedUnsigned, Uint)
    return isinstance(type_, type) and issubclass(type_, basic_types)


def get_basic_type_size(type_: type) -> int:
    """Get the byte size of a basic type."""
    if type_ is bool:
        return 1
    elif type_ == U8:
        return 1
    elif type_ == U16:
        return 2
    elif type_ == U32:
        return 4
    elif type_ == U64:
        return 8
    elif type_ == U128:
        return 16
    elif type_ == U256:
        return 32
    elif issubclass(type_, FixedUnsigned):
        # For other FixedUnsigned types, calculate from MAX_VALUE
        bits = type_.MAX_VALUE._number.bit_length()
        return (bits + 7) // 8
    else:
        raise ValueError(f"Unknown basic type size for {type_}")


def pack_vector_to_chunks(vector: Vector[Any]) -> list[Bytes32]:
    """
    Pack a vector of basic types into 32-byte chunks.

    This follows remerkleable's approach: pack multiple small elements
    into single chunks where possible.
    """
    elem_type = vector.element_type
    elem_size = get_basic_type_size(elem_type)
    elems_per_chunk = 32 // elem_size

    chunks = []

    # Group elements into chunks (use .elements for Pydantic)
    for i in range(0, len(vector.elements), elems_per_chunk):
        chunk_data = b""
        for j in range(elems_per_chunk):
            if i + j < len(vector.elements):
                elem = vector.elements[i + j]
                # Convert to little-endian bytes
                if isinstance(elem, bool):
                    chunk_data += b"\x01" if elem else b"\x00"
                elif isinstance(elem, (FixedUnsigned, Uint)):
                    chunk_data += elem.to_bytes(elem_size, byteorder="little")
                else:
                    # Shouldn't happen for basic types
                    raise ValueError(f"Unexpected element type: {type(elem)}")
            else:
                # Pad with zeros
                chunk_data += b"\x00" * elem_size

        # Ensure chunk is exactly 32 bytes
        if len(chunk_data) < 32:
            chunk_data += b"\x00" * (32 - len(chunk_data))

        chunks.append(Bytes32(chunk_data))

    return chunks


def hash_tree_root_bitvector(bitvector) -> Bytes32:
    """
    Hash tree root of a bitvector.

    Bitvectors are packed into chunks and merkleized.
    """
    # Import here to avoid circular dependency

    # Serialize and pack into chunks
    serialized = bitvector.serialize()
    chunks = pack_bytes(serialized)

    # Merkleize the chunks
    if len(chunks) == 1:
        return chunks[0]
    else:
        return merkleize(chunks)


def hash_tree_root_bitlist(bitlist) -> Bytes32:
    """
    Hash tree root of a bitlist.

    Bitlists are merkleized with their length mixed in.
    """
    # Import here to avoid circular dependency

    # Serialize WITHOUT the sentinel bit for merkleization
    # We need to pack the actual bits, not the serialized form
    num_bits = len(bitlist)
    num_bytes = (num_bits + 7) // 8
    data = bytearray(num_bytes)

    for i, bit in enumerate(bitlist):
        if bit:
            byte_index = i // 8
            bit_index = i % 8
            data[byte_index] |= 1 << bit_index

    # Pack into chunks
    chunks = pack_bytes(bytes(data))

    # Calculate the limit in chunks
    max_chunks = (bitlist.max_length + 255) // 256  # 256 bits per chunk

    # Merkleize with limit
    if chunks:
        contents_root = merkleize(chunks, limit=max_chunks)
    else:
        contents_root = merkleize([], limit=max_chunks)

    # Mix in the length
    length_bytes = len(bitlist).to_bytes(32, byteorder="little")
    return hash(contents_root + length_bytes)


def pack_list_to_chunks(ssz_list: SSZList[Any]) -> list[Bytes32]:
    """
    Pack a list of basic types into 32-byte chunks.

    Similar to pack_vector_to_chunks but for lists.
    """
    if len(ssz_list.elements) == 0:
        return []

    elem_type = ssz_list.element_type
    elem_size = get_basic_type_size(elem_type)
    elems_per_chunk = 32 // elem_size

    chunks = []

    # Group elements into chunks (use .elements for Pydantic)
    for i in range(0, len(ssz_list.elements), elems_per_chunk):
        chunk_data = b""
        for j in range(elems_per_chunk):
            if i + j < len(ssz_list.elements):
                elem = ssz_list.elements[i + j]
                # Convert to little-endian bytes
                if isinstance(elem, bool):
                    chunk_data += b"\x01" if elem else b"\x00"
                elif isinstance(elem, (FixedUnsigned, Uint)):
                    chunk_data += elem.to_bytes(elem_size, byteorder="little")
                else:
                    # Shouldn't happen for basic types
                    raise ValueError(f"Unexpected element type: {type(elem)}")
            else:
                # Pad with zeros
                chunk_data += b"\x00" * elem_size

        # Ensure chunk is exactly 32 bytes
        if len(chunk_data) < 32:
            chunk_data += b"\x00" * (32 - len(chunk_data))

        chunks.append(Bytes32(chunk_data))

    return chunks
