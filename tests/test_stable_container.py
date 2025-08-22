"""
Test StableContainer implementation.
"""

from typing import Optional

import pytest
from ethereum_types.numeric import U8, U32

from ethereum_ssz import (
    U16,
    StableContainer,
    create_stable_container_class,
    ssz,
)
from ethereum_ssz.composite import List as SSZList


class TestStableContainerBasic:
    """Test basic StableContainer functionality."""

    def test_stable_container_creation(self):
        """Test creating a StableContainer with optional fields."""

        class TestStable(StableContainer):
            a: Optional[U8] = None
            b: Optional[U16] = None
            c: Optional[U32] = None
            _max_fields: int = 4

        # Create with some fields None
        obj = TestStable(a=U8(10), b=None, c=U32(100))

        # Check fields
        assert obj.a == U8(10)
        assert obj.b is None
        assert obj.c == U32(100)

        # Check active fields
        active = obj.active_fields()
        assert active[0] is True  # a is active
        assert active[1] is False  # b is not active
        assert active[2] is True  # c is active

    def test_stable_container_all_none(self):
        """Test StableContainer with all fields None."""

        class TestStable(StableContainer):
            a: Optional[U8] = None
            b: Optional[U16] = None
            _max_fields: int = 4

        obj = TestStable()

        assert obj.a is None
        assert obj.b is None

        active = obj.active_fields()
        assert active[0] is False
        assert active[1] is False

    def test_stable_container_all_set(self):
        """Test StableContainer with all fields set."""

        class TestStable(StableContainer):
            a: Optional[U8] = None
            b: Optional[U16] = None
            _max_fields: int = 4

        obj = TestStable(a=U8(1), b=U16(2))

        assert obj.a == U8(1)
        assert obj.b == U16(2)

        active = obj.active_fields()
        assert active[0] is True
        assert active[1] is True

    def test_stable_container_serialization(self):
        """Test basic serialization of StableContainer."""

        class TestStable(StableContainer):
            a: Optional[U8] = None
            b: Optional[U16] = None
            _max_fields: int = 4

        # Only first field set
        obj1 = TestStable(a=U8(42), b=None)
        data1 = obj1.serialize()

        # Should contain: U8(42) + bitvector with first bit set
        # Bitvector of length 4 with first bit set = 0x01
        assert data1 == b"\x2a\x01"  # 42 + bitvector

        # Both fields set
        obj2 = TestStable(a=U8(42), b=U16(300))
        data2 = obj2.serialize()

        # Should contain: U8(42) + U16(300 little-endian) + bitvector
        # Bitvector with first two bits set = 0x03
        assert data2 == b"\x2a\x2c\x01\x03"  # 42 + 300 (LE) + bitvector

    def test_create_stable_container_class(self):
        """Test creating StableContainer class dynamically."""

        # Create a class dynamically
        TestDynamic = create_stable_container_class(
            "TestDynamic",
            {
                "x": U8,
                "y": U16,
                "z": U32,
            },
            max_fields=8,
        )

        # Create instance
        obj = TestDynamic(x=U8(1), y=None, z=U32(100))

        assert obj.x == U8(1)
        assert obj.y is None
        assert obj.z == U32(100)

        # Check it's a StableContainer
        assert isinstance(obj, StableContainer)

    def test_stable_container_hash_tree_root(self):
        """Test hash_tree_root for StableContainer."""

        class TestStable(StableContainer):
            a: Optional[U8] = None
            b: Optional[U16] = None
            _max_fields: int = 4

        obj = TestStable(a=U8(10), b=U16(20))

        # Should compute hash tree root (even if simplified)
        htr = obj.hash_tree_root()
        assert len(htr) == 32  # Should be 32 bytes

    def test_stable_container_deserialization(self):
        """Test deserialization of StableContainer."""

        class TestStable(StableContainer):
            a: Optional[U8] = None
            b: Optional[U16] = None
            _max_fields: int = 4

        # Test deserializing with only first field set
        # Data: U8(42) = 0x2a, bitvector with first bit set = 0x01
        obj1 = TestStable.deserialize(b"\x2a\x01")
        assert obj1.a == U8(42)
        assert obj1.b is None

        # Test deserializing with both fields set
        # Data: U8(42) = 0x2a, U16(300) = 0x2c 0x01, bitvector with first two bits set = 0x03
        obj2 = TestStable.deserialize(b"\x2a\x2c\x01\x03")
        assert obj2.a == U8(42)
        assert obj2.b == U16(300)

        # Test round-trip serialization/deserialization
        original = TestStable(a=U8(10), b=U16(20))
        serialized = original.serialize()
        deserialized = TestStable.deserialize(serialized)
        assert deserialized.a == original.a
        assert deserialized.b == original.b


class TestStableContainerComplex:
    """Test more complex StableContainer scenarios."""

    def test_stable_container_with_lists(self):
        """Test StableContainer with list fields."""

        class TestStable(StableContainer):
            values: Optional[SSZList] = None
            count: Optional[U32] = None
            _max_fields: int = 4

        lst = SSZList(
            elements=[U8(1), U8(2), U8(3)], max_length=10, element_type=U8
        )
        obj = TestStable(values=lst, count=U32(3))

        assert obj.values == lst
        assert obj.count == U32(3)

        active = obj.active_fields()
        assert active[0] is True
        assert active[1] is True

    def test_stable_container_encode_via_ssz(self):
        """Test encoding StableContainer through ssz.encode."""

        class TestStable(StableContainer):
            a: Optional[U8] = None
            b: Optional[U16] = None
            _max_fields: int = 4

        obj = TestStable(a=U8(5), b=U16(10))

        # Should be able to encode via ssz.encode
        encoded = ssz.encode(obj)

        # Check it matches direct serialization
        assert encoded == obj.serialize()
