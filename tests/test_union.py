"""
Test Union types adapted from remerkleable.

These tests verify SSZ encoding and hash tree root of Union types.
"""

import hashlib

from ethereum_types.bytes import Bytes32
from ethereum_types.numeric import U8, U32

from ethereum_ssz import (
    U16,
    Container,
    Union,
    Vector,
    create_union_class,
    hash_tree_root,
    ssz,
)
from ethereum_ssz import (
    List as SSZList,
)


def sha256(data: bytes) -> bytes:
    """SHA256 hash helper."""
    return hashlib.sha256(data).digest()


def h(a: str, b: str) -> str:
    """Hash two hex strings and return hex."""
    a_bytes = bytes.fromhex(a) if isinstance(a, str) else a
    b_bytes = bytes.fromhex(b) if isinstance(b, str) else b
    return sha256(a_bytes + b_bytes).hex()


def chunk(hex_str: str) -> str:
    """Pad hex string to 32 bytes (64 hex chars)."""
    return (hex_str + ("00" * 32))[:64]


# Test container for union tests

class SingleFieldTestStruct(Container):
    """Container with a single byte field."""

    A: U8


class TestUnionBasics:
    """Test basic Union functionality with exact test vectors."""

    def test_single_type_union(self):
        """Test Union[uint16] with single type."""
        # Create a union type with just uint16
        UnionType = create_union_class("UnionType", [U16])
        u = UnionType(selector=0, value=U16(0xAABB))

        # Test serialization: selector (00) + value (bbaa in little-endian)
        encoded = ssz.encode(u)
        assert encoded == b"\x00\xbb\xaa"

        # Test hash tree root: h(chunk("bbaa"), chunk(""))
        htr = hash_tree_root(u)
        expected_hex = h(chunk("bbaa"), chunk(""))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_simple_union(self):
        """Test Union[uint16, uint32] with first type selected."""
        # Create a union type with uint16 and uint32
        UnionType = create_union_class("UnionType", [U16, U32])
        u = UnionType(selector=0, value=U16(0xAABB))

        # Test serialization
        encoded = ssz.encode(u)
        assert encoded == b"\x00\xbb\xaa"

        # Test hash tree root
        htr = hash_tree_root(u)
        expected_hex = h(chunk("bbaa"), chunk(""))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_union_with_none(self):
        """Test Union[None, uint16, uint32] with None selected."""
        # Create a union with None as first option
        UnionType = create_union_class("UnionType", [None, U16, U32])
        u = UnionType(selector=0, value=None)

        # Test serialization: just selector for None
        encoded = ssz.encode(u)
        assert encoded == b"\x00"

        # Test hash tree root: h(chunk(""), chunk(""))
        htr = hash_tree_root(u)
        expected_hex = h(chunk(""), chunk(""))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_union_other_than_none(self):
        """Test Union[None, uint16, uint32] with uint16 selected."""
        UnionType = create_union_class("UnionType", [None, U16, U32])
        u = UnionType(selector=1, value=U16(0xAABB))

        # Selector 01 + value bbaa
        encoded = ssz.encode(u)
        assert encoded == b"\x01\xbb\xaa"

        # Hash tree root: h(chunk("bbaa"), chunk("01"))
        htr = hash_tree_root(u)
        expected_hex = h(chunk("bbaa"), chunk("01"))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_simple_union_other(self):
        """Test Union[uint16, uint32] with second type selected."""
        UnionType = create_union_class("UnionType", [U16, U32])
        u = UnionType(selector=1, value=U32(0xDEADBEEF))

        # Selector 01 + value efbeadde (little-endian)
        encoded = ssz.encode(u)
        assert encoded == b"\x01\xef\xbe\xad\xde"

        # Hash tree root: h(chunk("efbeadde"), chunk("01"))
        htr = hash_tree_root(u)
        expected_hex = h(chunk("efbeadde"), chunk("01"))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_simple_large_union(self):
        """Test Union[uint16, uint32, uint8, List[uint16, 8]] with uint8."""
        # Note: For this test we'll use U8 instead of a list to keep it simple
        UnionType = create_union_class("UnionType", [U16, U32, U8, SSZList])
        u = UnionType(selector=2, value=U8(0xAA))

        # Selector 02 + value aa
        encoded = ssz.encode(u)
        assert encoded == b"\x02\xaa"

        # Hash tree root: h(chunk("aa"), chunk("02"))
        htr = hash_tree_root(u)
        expected_hex = h(chunk("aa"), chunk("02"))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_duplicate_type_union(self):
        """Test Union[SingleFieldTestStruct, SingleFieldTestStruct]."""
        UnionType = create_union_class(
            "UnionType", [SingleFieldTestStruct, SingleFieldTestStruct]
        )
        u = UnionType(selector=1, value=SingleFieldTestStruct(A=U8(0xAB)))

        # Selector 01 + container value
        encoded = ssz.encode(u)
        assert encoded == b"\x01\xab"

        # Hash tree root: h(chunk("ab"), chunk("01"))
        htr = hash_tree_root(u)
        expected_hex = h(chunk("ab"), chunk("01"))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected


class TestComplexUnion:
    """Test Union with complex nested types."""

    def test_union_with_container(self):
        """Test Union containing a Container type."""

        # Simple container for testing
        class TestStruct(Container):
            A: U16
            B: U8

        UnionType = create_union_class("UnionType", [U16, TestStruct])
        s = TestStruct(A=U16(0xABCD), B=U8(0xFF))
        u = UnionType(selector=1, value=s)

        # Selector 01 + container encoding
        encoded = ssz.encode(u)
        # Container encodes as A (cdab little-endian) + B (ff)
        assert encoded == b"\x01\xcd\xab\xff"

        # Hash tree root
        htr = hash_tree_root(u)
        # Container HTR is h(chunk("cdab"), chunk("ff"))
        container_htr = h(chunk("cdab"), chunk("ff"))
        # Union HTR is h(container_htr, chunk("01"))
        expected_hex = h(container_htr, chunk("01"))
        expected = Bytes32(bytes.fromhex(expected_hex))
        assert htr == expected

    def test_union_with_vector(self):
        """Test Union containing a Vector type."""
        UnionType = create_union_class("UnionType", [U8, Vector])
        vec = Vector([U8(1), U8(2), U8(3)], length=3, element_type=U8)
        u = UnionType(selector=1, value=vec)

        # Selector 01 + vector encoding
        encoded = ssz.encode(u)
        assert encoded == b"\x01\x01\x02\x03"

        # Hash tree root
        htr = hash_tree_root(u)
        # Vector HTR for [1,2,3] padded to 32 bytes
        vec_htr = hash_tree_root(vec)
        # Union HTR is h(vec_htr, chunk("01"))
        from ethereum_ssz.merkle import hash as ssz_hash

        expected = ssz_hash(vec_htr + bytes.fromhex(chunk("01")))
        assert htr == expected
