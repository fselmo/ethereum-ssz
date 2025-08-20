"""
Test Container implementation adapted from remerkleable.

These tests verify SSZ encoding/decoding of Container types.
"""

import hashlib

from ethereum_types.bytes import Bytes32
from ethereum_types.numeric import U8, U32, U64

from ethereum_ssz import U16, hash_tree_root, ssz
from ethereum_ssz.composite import List as SSZList
from ethereum_ssz.composite import Vector
from ethereum_ssz.container import Container


def sha256(data: bytes) -> bytes:
    """SHA256 hash helper."""
    return hashlib.sha256(data).digest()


def h(a_hex: str, b_hex: str) -> str:
    """Hash two hex strings and return hex."""
    a = bytes.fromhex(a_hex) if isinstance(a_hex, str) else a_hex
    b = bytes.fromhex(b_hex) if isinstance(b_hex, str) else b_hex
    return sha256(a + b).hex()


def chunk(hex_str: str) -> str:
    """Pad hex string to 32 bytes (64 hex chars)."""
    return (hex_str + ("00" * 32))[:64]


# Define test containers following remerkleable's pattern
class SingleFieldTestStruct(Container):
    """Container with a single byte field."""

    A: U8


class SmallTestStruct(Container):
    """Container with two uint16 fields."""

    A: U16
    B: U16


class FixedTestStruct(Container):
    """Container with mixed fixed-size fields."""

    A: U8
    B: U64
    C: U32


class VarTestStruct(Container):
    """Container with variable-size list."""

    A: U16
    B: SSZList  # List[uint16, 1024]
    C: U8


class ComplexTestStruct(Container):
    """Complex nested container."""

    A: U16
    B: SSZList  # List[uint16, 128]
    C: U8
    D: SSZList  # List[byte, 256]
    E: VarTestStruct
    F: Vector  # Vector[FixedTestStruct, 4]
    G: Vector  # Vector[VarTestStruct, 2]


class TestContainerBasics:
    """Test basic Container functionality."""

    def test_single_field_container(self):
        """Test container with single field."""
        s = SingleFieldTestStruct(A=U8(0xAB))

        # Test serialization
        encoded = ssz.encode(s)
        assert encoded == b"\xab"

        # Test hash tree root
        htr = hash_tree_root(s)
        # Should be chunk("ab")
        expected = Bytes32(bytes.fromhex(chunk("ab")))
        assert htr == expected

    def test_small_container(self):
        """Test container with two uint16 fields."""
        s = SmallTestStruct(A=U16(0x4567), B=U16(0x0123))

        # Test serialization - little endian
        encoded = ssz.encode(s)
        assert encoded == b"\x67\x45\x23\x01"

        # Test hash tree root - h(chunk("6745"), chunk("2301"))
        htr = hash_tree_root(s)
        expected_hex = h(chunk("6745"), chunk("2301"))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_fixed_container(self):
        """Test container with mixed fixed-size fields."""
        s = FixedTestStruct(
            A=U8(0xAB), B=U64(0xAABBCCDD00112233), C=U32(0x12345678)
        )

        # Test serialization - all little endian
        encoded = ssz.encode(s)
        expected_bytes = (
            b"\xab"  # A: uint8
            + b"\x33\x22\x11\x00\xdd\xcc\xbb\xaa"  # B: uint64 little-endian
            + b"\x78\x56\x34\x12"  # C: uint32 little-endian
        )
        assert encoded == expected_bytes

        # Test hash tree root
        htr = hash_tree_root(s)
        # h(h(chunk("ab"), chunk("33221100ddccbbaa")), h(chunk("78563412"), chunk("")))
        expected_hex = h(
            h(chunk("ab"), chunk("33221100ddccbbaa")),
            h(chunk("78563412"), chunk("")),
        )
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_container_equality(self):
        """Test container equality."""
        s1 = SmallTestStruct(A=U16(0x4567), B=U16(0x0123))
        s2 = SmallTestStruct(A=U16(0x4567), B=U16(0x0123))
        s3 = SmallTestStruct(A=U16(0x4567), B=U16(0x0124))

        assert s1 == s2
        assert s1 != s3
        assert s2 != s3

    def test_container_repr(self):
        """Test container string representation."""
        s = SmallTestStruct(A=U16(0x4567), B=U16(0x0123))
        repr_str = repr(s)

        assert "SmallTestStruct" in repr_str
        assert "A=" in repr_str
        assert "B=" in repr_str


class TestContainerWithLists:
    """Test containers with variable-size fields."""

    def test_var_container_empty_list(self):
        """Test container with empty list."""
        s = VarTestStruct(
            A=U16(0xABCD),
            B=SSZList([], max_length=1024, element_type=U16),
            C=U8(0xFF),
        )

        # For now, just verify it can be created
        # Full offset encoding will be implemented later
        assert s.A == U16(0xABCD)
        assert len(s.B) == 0
        assert s.C == U8(0xFF)

    def test_var_container_with_list(self):
        """Test container with non-empty list."""
        s = VarTestStruct(
            A=U16(0xABCD),
            B=SSZList(
                [U16(1), U16(2), U16(3)], max_length=1024, element_type=U16
            ),
            C=U8(0xFF),
        )

        # Verify fields
        assert s.A == U16(0xABCD)
        assert len(s.B) == 3
        assert s.B[0] == U16(1)
        assert s.B[1] == U16(2)
        assert s.B[2] == U16(3)
        assert s.C == U8(0xFF)
