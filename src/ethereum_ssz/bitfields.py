"""
SSZ Bitfield types - Bitvector and Bitlist.

Bitvectors are fixed-length bit sequences.
Bitlists are variable-length bit sequences with a maximum length.
"""

from collections.abc import Iterator, Sequence
from typing import Any, Union

from ethereum_types.bytes import Bytes32
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Bitvector(BaseModel):
    """
    Fixed-length sequence of bits.

    In SSZ, bitvectors are packed into bytes, with bits indexed from 0.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bits: list[bool]
    length: int

    @field_validator("bits", mode="before")
    @classmethod
    def convert_bits(
        cls, v: Union[Sequence[bool], Sequence[int]]
    ) -> list[bool]:
        """Convert input to list of bools."""
        return [bool(bit) for bit in v]

    @model_validator(mode="after")
    def validate_length(self) -> "Bitvector":
        """Validate that bits match the specified length."""
        if len(self.bits) != self.length:
            raise ValueError(
                f"Bitvector requires exactly {self.length} bits, got {len(self.bits)}"
            )
        return self

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
        return self.bits[index]

    def __setitem__(self, index: int, value: bool) -> None:
        """Set bit at index."""
        if index < 0 or index >= self.length:
            raise IndexError(
                f"Index {index} out of range for Bitvector of length "
                f"{self.length}"
            )
        self.bits[index] = bool(value)

    def __iter__(self) -> Iterator[bool]:
        """Iterate over bits."""
        return iter(self.bits)

    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Bitvector):
            return False
        return self.bits == other.bits and self.length == other.length

    def __repr__(self) -> str:
        """String representation."""
        bit_str = "".join("1" if bit else "0" for bit in self.bits)
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
        for i, bit in enumerate(self.bits):
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

        return cls(bits=bits, length=length)


class Bitlist(BaseModel):
    """
    Variable-length sequence of bits with a maximum length.

    In SSZ, bitlists are serialized with a sentinel bit to mark the length.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bits: list[bool]
    max_length: int

    @field_validator("bits", mode="before")
    @classmethod
    def convert_bits(
        cls, v: Union[Sequence[bool], Sequence[int]]
    ) -> list[bool]:
        """Convert input to list of bools."""
        return [bool(bit) for bit in v]

    @model_validator(mode="after")
    def validate_max_length(self) -> "Bitlist":
        """Validate that bits don't exceed max_length."""
        if len(self.bits) > self.max_length:
            raise ValueError(
                f"Bitlist exceeds maximum length {self.max_length}, got {len(self.bits)}"
            )
        return self

    def __len__(self) -> int:
        """Return the current length."""
        return len(self.bits)

    def __getitem__(self, index: int) -> bool:
        """Get bit at index."""
        return self.bits[index]

    def __setitem__(self, index: int, value: bool) -> None:
        """Set bit at index."""
        self.bits[index] = bool(value)

    def __iter__(self) -> Iterator[bool]:
        """Iterate over bits."""
        return iter(self.bits)

    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Bitlist):
            return False
        return self.bits == other.bits and self.max_length == other.max_length

    def __repr__(self) -> str:
        """String representation."""
        bit_str = "".join("1" if bit else "0" for bit in self.bits)
        return f"Bitlist[{self.max_length}]({bit_str})"

    def append(self, bit: bool) -> None:
        """Append a bit."""
        if len(self.bits) >= self.max_length:
            raise ValueError(
                f"Bitlist would exceed maximum length {self.max_length}"
            )
        self.bits.append(bool(bit))

    def extend(self, bits: Sequence[bool]) -> None:
        """Extend with multiple bits."""
        new_length = len(self.bits) + len(bits)
        if new_length > self.max_length:
            raise ValueError(
                f"Bitlist would exceed maximum length {self.max_length}"
            )
        self.bits.extend(bool(bit) for bit in bits)

    def serialize(self) -> bytes:
        """
        Serialize to SSZ bytes.

        Bitlists are serialized with a sentinel bit (1) after the last actual
        bit to mark the length. This sentinel is in the first unused bit
        position.
        """
        if len(self.bits) == 0:
            # Empty bitlist: single byte 0x01 (just the sentinel)
            return b"\x01"

        # Calculate bytes needed (including sentinel bit)
        total_bits = len(self.bits) + 1  # +1 for sentinel
        num_bytes = (total_bits + 7) // 8
        result = bytearray(num_bytes)

        # Pack actual bits
        for i, bit in enumerate(self.bits):
            if bit:
                byte_index = i // 8
                bit_index = i % 8
                result[byte_index] |= 1 << bit_index

        # Add sentinel bit
        sentinel_index = len(self.bits)
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

        return cls(bits=bits, max_length=max_length)
