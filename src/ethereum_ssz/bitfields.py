"""
SSZ Bitfield types - Bitvector and Bitlist.

Bitvectors are fixed-length bit sequences.
Bitlists are variable-length bit sequences with a maximum length.
"""

from collections.abc import Iterator, Sequence
from typing import Any, Union

from ethereum_types.bytes import Bytes32


class Bitvector:
    """
    Fixed-length sequence of bits.

    In SSZ, bitvectors are packed into bytes, with bits indexed from 0.
    """

    def __init__(
        self, bits: Union[Sequence[bool], Sequence[int]], length: int
    ):
        """
        Initialize a Bitvector with fixed length.

        Args:
            bits: Sequence of booleans or 0/1 integers
            length: Fixed length of the bitvector
        """
        if len(bits) != length:
            raise ValueError(
                f"Bitvector requires exactly {length} bits, got {len(bits)}"
            )

        self.length = length
        self._bits = [bool(bit) for bit in bits]

    def __len__(self) -> int:
        """Return the fixed length."""
        return self.length

    def __getitem__(self, index: int) -> bool:
        """Get bit at index."""
        if index < 0 or index >= self.length:
            raise IndexError(
                f"Index {index} out of range for Bitvector of length "
                f"{self.length}"
            )
        return self._bits[index]

    def __setitem__(self, index: int, value: bool) -> None:
        """Set bit at index."""
        if index < 0 or index >= self.length:
            raise IndexError(
                f"Index {index} out of range for Bitvector of length "
                f"{self.length}"
            )
        self._bits[index] = bool(value)

    def __iter__(self) -> Iterator[bool]:
        """Iterate over bits."""
        return iter(self._bits)

    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Bitvector):
            return False
        return self._bits == other._bits and self.length == other.length

    def __repr__(self) -> str:
        """String representation."""
        bit_str = "".join("1" if bit else "0" for bit in self._bits)
        return f"Bitvector[{self.length}]({bit_str})"

    def serialize(self) -> bytes:
        """
        Serialize to SSZ bytes.

        Bits are packed into bytes, with bit 0 in the LSB of byte 0.
        """
        # Calculate number of bytes needed
        num_bytes = (self.length + 7) // 8
        result = bytearray(num_bytes)

        # Pack bits into bytes
        for i, bit in enumerate(self._bits):
            if bit:
                byte_index = i // 8
                bit_index = i % 8
                result[byte_index] |= 1 << bit_index

        return bytes(result)

    def hash_tree_root(self) -> Bytes32:
        """Calculate SSZ hash tree root."""
        from .merkle import hash_tree_root_bitvector

        return hash_tree_root_bitvector(self)

    @classmethod
    def deserialize(cls, data: bytes, length: int) -> "Bitvector":
        """
        Deserialize from SSZ bytes.

        Args:
            data: Serialized bytes
            length: Expected length of bitvector
        """
        expected_bytes = (length + 7) // 8
        if len(data) != expected_bytes:
            raise ValueError(
                f"Expected {expected_bytes} bytes for Bitvector[{length}], "
                f"got {len(data)}"
            )

        bits = []
        for i in range(length):
            byte_index = i // 8
            bit_index = i % 8
            bit = bool(data[byte_index] & (1 << bit_index))
            bits.append(bit)

        return cls(bits, length)


class Bitlist:
    """
    Variable-length sequence of bits with a maximum length.

    In SSZ, bitlists are serialized with a sentinel bit to mark the length.
    """

    def __init__(
        self, bits: Union[Sequence[bool], Sequence[int]], max_length: int
    ):
        """
        Initialize a Bitlist with maximum length constraint.

        Args:
            bits: Sequence of booleans or 0/1 integers
            max_length: Maximum allowed length
        """
        if len(bits) > max_length:
            raise ValueError(
                f"Bitlist exceeds maximum length {max_length}, got {len(bits)}"
            )

        self.max_length = max_length
        self._bits = [bool(bit) for bit in bits]

    def __len__(self) -> int:
        """Return the current length."""
        return len(self._bits)

    def __getitem__(self, index: int) -> bool:
        """Get bit at index."""
        return self._bits[index]

    def __setitem__(self, index: int, value: bool) -> None:
        """Set bit at index."""
        self._bits[index] = bool(value)

    def __iter__(self) -> Iterator[bool]:
        """Iterate over bits."""
        return iter(self._bits)

    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Bitlist):
            return False
        return (
            self._bits == other._bits and self.max_length == other.max_length
        )

    def __repr__(self) -> str:
        """String representation."""
        bit_str = "".join("1" if bit else "0" for bit in self._bits)
        return f"Bitlist[{self.max_length}]({bit_str})"

    def append(self, bit: bool) -> None:
        """Append a bit."""
        if len(self._bits) >= self.max_length:
            raise ValueError(
                f"Bitlist would exceed maximum length {self.max_length}"
            )
        self._bits.append(bool(bit))

    def extend(self, bits: Sequence[bool]) -> None:
        """Extend with multiple bits."""
        new_length = len(self._bits) + len(bits)
        if new_length > self.max_length:
            raise ValueError(
                f"Bitlist would exceed maximum length {self.max_length}"
            )
        self._bits.extend(bool(bit) for bit in bits)

    def serialize(self) -> bytes:
        """
        Serialize to SSZ bytes.

        Bitlists are serialized with a sentinel bit (1) after the last actual
        bit to mark the length. This sentinel is in the first unused bit
        position.
        """
        if len(self._bits) == 0:
            # Empty bitlist: single byte 0x01 (just the sentinel)
            return b"\x01"

        # Calculate bytes needed (including sentinel bit)
        total_bits = len(self._bits) + 1  # +1 for sentinel
        num_bytes = (total_bits + 7) // 8
        result = bytearray(num_bytes)

        # Pack actual bits
        for i, bit in enumerate(self._bits):
            if bit:
                byte_index = i // 8
                bit_index = i % 8
                result[byte_index] |= 1 << bit_index

        # Add sentinel bit
        sentinel_index = len(self._bits)
        byte_index = sentinel_index // 8
        bit_index = sentinel_index % 8
        result[byte_index] |= 1 << bit_index

        return bytes(result)

    def hash_tree_root(self) -> Bytes32:
        """Calculate SSZ hash tree root."""
        from .merkle import hash_tree_root_bitlist

        return hash_tree_root_bitlist(self)

    @classmethod
    def deserialize(cls, data: bytes, max_length: int) -> "Bitlist":
        """
        Deserialize from SSZ bytes.

        Args:
            data: Serialized bytes (includes sentinel bit)
            max_length: Maximum allowed length
        """
        if len(data) == 0:
            raise ValueError("Cannot deserialize empty bytes as Bitlist")

        # Find the sentinel bit (highest set bit in last byte with any bits)
        # Work backwards to find the last byte with any bits set
        last_byte_index = len(data) - 1
        while last_byte_index >= 0 and data[last_byte_index] == 0:
            last_byte_index -= 1

        if last_byte_index < 0:
            raise ValueError("No sentinel bit found in Bitlist")

        # Find the highest set bit in the last non-zero byte (the sentinel)
        last_byte = data[last_byte_index]
        sentinel_bit_index = 7
        while sentinel_bit_index >= 0 and not (
            last_byte & (1 << sentinel_bit_index)
        ):
            sentinel_bit_index -= 1

        if sentinel_bit_index < 0:
            raise ValueError("No sentinel bit found in Bitlist")

        # Calculate the actual length (excluding sentinel)
        actual_length = last_byte_index * 8 + sentinel_bit_index

        if actual_length > max_length:
            raise ValueError(
                f"Bitlist length {actual_length} exceeds maximum {max_length}"
            )

        # Extract the actual bits (excluding sentinel)
        bits = []
        for i in range(actual_length):
            byte_index = i // 8
            bit_index = i % 8
            bit = bool(data[byte_index] & (1 << bit_index))
            bits.append(bit)

        return cls(bits, max_length)
