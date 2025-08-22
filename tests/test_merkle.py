"""
Tests for SSZ merkleization (hash_tree_root).
"""

from ethereum_types.bytes import Bytes32
from ethereum_types.numeric import U8, U32, U64, U256

from ethereum_ssz.composite import List as SSZList
from ethereum_ssz.composite import Vector
from ethereum_ssz.merkle import hash_tree_root


def test_hash_tree_root_bool() -> None:
    """Test hash tree root of booleans."""
    # False should be 0x00 followed by 31 zero bytes
    htr_false = hash_tree_root(False)
    assert htr_false == Bytes32(b"\x00" * 32)

    # True should be 0x01 followed by 31 zero bytes
    htr_true = hash_tree_root(True)
    assert htr_true == Bytes32(b"\x01" + b"\x00" * 31)


def test_hash_tree_root_uint8() -> None:
    """Test hash tree root of U8."""
    # U8(0) should be all zeros
    assert hash_tree_root(U8(0)) == Bytes32(b"\x00" * 32)

    # U8(1) should be 0x01 followed by zeros
    assert hash_tree_root(U8(1)) == Bytes32(b"\x01" + b"\x00" * 31)

    # U8(255) should be 0xFF followed by zeros
    assert hash_tree_root(U8(255)) == Bytes32(b"\xff" + b"\x00" * 31)


def test_hash_tree_root_uint32() -> None:
    """Test hash tree root of U32."""
    # U32(0) should be all zeros
    assert hash_tree_root(U32(0)) == Bytes32(b"\x00" * 32)

    # U32(1) should be 0x01 followed by zeros (little-endian)
    assert hash_tree_root(U32(1)) == Bytes32(b"\x01" + b"\x00" * 31)

    # U32(0x12345678) should be little-endian
    expected = Bytes32(b"\x78\x56\x34\x12" + b"\x00" * 28)
    assert hash_tree_root(U32(0x12345678)) == expected


def test_hash_tree_root_uint64() -> None:
    """Test hash tree root of U64."""
    # U64(0) should be all zeros
    assert hash_tree_root(U64(0)) == Bytes32(b"\x00" * 32)

    # U64(1) should be 0x01 followed by zeros
    assert hash_tree_root(U64(1)) == Bytes32(b"\x01" + b"\x00" * 31)

    # U64 with specific value
    value = U64(0x0123456789ABCDEF)
    expected = Bytes32(b"\xef\xcd\xab\x89\x67\x45\x23\x01" + b"\x00" * 24)
    assert hash_tree_root(value) == expected


def test_hash_tree_root_uint256() -> None:
    """Test hash tree root of U256."""
    # U256(0) should be all zeros
    assert hash_tree_root(U256(0)) == Bytes32(b"\x00" * 32)

    # U256(1) should be 0x01 followed by zeros
    assert hash_tree_root(U256(1)) == Bytes32(b"\x01" + b"\x00" * 31)

    # U256 max value should be all 0xFF
    max_u256 = U256(2**256 - 1)
    assert hash_tree_root(max_u256) == Bytes32(b"\xff" * 32)


def test_hash_tree_root_bytes() -> None:
    """Test hash tree root of bytes."""
    # Empty bytes
    assert hash_tree_root(b"") == Bytes32(b"\x00" * 32)

    # Small bytes (< 32)
    data = b"hello"
    expected = Bytes32(data + b"\x00" * (32 - len(data)))
    assert hash_tree_root(data) == expected

    # Exactly 32 bytes
    data32 = b"\x01" * 32
    assert hash_tree_root(data32) == Bytes32(data32)


def test_hash_tree_root_bytes32() -> None:
    """Test hash tree root of Bytes32."""
    # Zero Bytes32
    zero = Bytes32(b"\x00" * 32)
    assert hash_tree_root(zero) == zero

    # Non-zero Bytes32
    data = Bytes32(b"\xff" * 32)
    assert hash_tree_root(data) == data


def test_hash_tree_root_vector() -> None:
    """Test hash tree root of Vector."""
    # Vector of U8 values
    vec = Vector(
        elements=[U8(1), U8(2), U8(3), U8(4)], length=4, element_type=U8
    )

    # Each U8 becomes a 32-byte chunk, then merkleized
    htr = hash_tree_root(vec)
    assert isinstance(htr, Bytes32)
    assert len(htr) == 32

    # The result should be deterministic
    htr2 = hash_tree_root(vec)
    assert htr == htr2


def test_hash_tree_root_empty_vector() -> None:
    """Test hash tree root of empty vector."""
    # This would be a vector of length 0, which isn't typical
    # but we should handle it gracefully
    vec = Vector(elements=[], length=0, element_type=U8)
    htr = hash_tree_root(vec)
    assert isinstance(htr, Bytes32)


def test_hash_tree_root_list() -> None:
    """Test hash tree root of List."""
    # List with some elements
    lst = SSZList(
        elements=[U8(1), U8(2), U8(3)], max_length=10, element_type=U8
    )

    htr = hash_tree_root(lst)
    assert isinstance(htr, Bytes32)
    assert len(htr) == 32

    # Different length should give different root
    lst2 = SSZList(elements=[U8(1), U8(2)], max_length=10, element_type=U8)
    htr2 = hash_tree_root(lst2)
    assert htr != htr2


def test_hash_tree_root_empty_list() -> None:
    """Test hash tree root of empty list."""
    lst = SSZList(elements=[], max_length=10, element_type=U8)
    htr = hash_tree_root(lst)
    assert isinstance(htr, Bytes32)
    assert len(htr) == 32


def test_hash_tree_root_list_same_elements_different_max() -> None:
    """Test that lists with different max_length MAY have different roots.

    Note: Lists with same elements but different max_lengths will have the same
    hash tree root if they fit in the same tree structure (same number of chunks).
    This test verifies the case where different max_lengths lead to different trees.
    """
    # Use max_lengths that result in different tree depths
    # max=32 fits in 1 chunk (32 bytes), max=64 needs 2 chunks -> different tree depths
    lst1 = SSZList(elements=[U8(1), U8(2)], max_length=32, element_type=U8)
    lst2 = SSZList(elements=[U8(1), U8(2)], max_length=64, element_type=U8)

    # Should have different roots due to different tree structure
    htr1 = hash_tree_root(lst1)
    htr2 = hash_tree_root(lst2)
    assert htr1 != htr2
