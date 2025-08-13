"""
Port of remerkleable test_typing.py.

Tests type system, inheritance, and advanced SSZ type features.
"""

from dataclasses import dataclass
from typing import List as PyList

import pytest
from ethereum_types.bytes import Bytes32
from ethereum_types.numeric import U8, U32, U64

from ethereum_ssz import (
    U16,
    Bitlist,
    Bitvector,
    Container,
    Union,
    Vector,
    create_union_class,
    decode_list,
    decode_vector,
    hash_tree_root,
    ssz,
)
from ethereum_ssz import (
    List as SSZList,
)


class TestBasicInstances:
    """Test basic type instantiation and validation."""

    def test_uint_instances(self):
        """Test creating instances of uint types."""
        # Valid instances
        u8 = U8(255)
        assert u8 == U8.MAX_VALUE

        u16 = U16(65535)
        assert u16 == U16.MAX_VALUE

        u32 = U32(0xffffffff)
        assert u32 == U32.MAX_VALUE

        # Test zero values
        assert U8(0) == U8(0)
        assert U16(0) == U16(0)
        assert U32(0) == U32(0)

    def test_uint_value_bounds(self):
        """Test value boundary validation."""
        # These should work
        U8(0)
        U8(255)
        U16(0)
        U16(65535)
        U32(0)
        U32(0xffffffff)

        # NOTE: ethereum-types raises OverflowError on construction with out-of-bounds values
        # This differs from wrapping behavior
        with pytest.raises(OverflowError):
            U8(256)
        with pytest.raises(OverflowError):
            U8(257)
        with pytest.raises(OverflowError):
            U16(65536)

    def test_bool_instances(self):
        """Test boolean instances."""
        assert True is True
        assert False is False
        assert bool(1) is True
        assert bool(0) is False


class TestContainerTypes:
    """Test container type system."""

    def test_container_definition(self):
        """Test defining container types."""
        @dataclass
        class SimpleContainer(Container):
            a: U8
            b: U16

        # Create instance
        obj = SimpleContainer(a=U8(1), b=U16(2))
        assert obj.a == U8(1)
        assert obj.b == U16(2)

        # Field access
        obj.a = U8(10)
        assert obj.a == U8(10)

        # Field modification
        obj.b = U16(20)
        assert obj.b == U16(20)

    def test_container_equality(self):
        """Test container equality."""
        @dataclass
        class TestContainer(Container):
            x: U32
            y: U32

        obj1 = TestContainer(x=U32(1), y=U32(2))
        obj2 = TestContainer(x=U32(1), y=U32(2))
        obj3 = TestContainer(x=U32(1), y=U32(3))

        assert obj1 == obj2
        assert obj1 != obj3

    def test_container_nested(self):
        """Test nested containers."""
        @dataclass
        class Inner(Container):
            value: U16

        @dataclass
        class Outer(Container):
            inner: Inner
            count: U8

        inner_obj = Inner(value=U16(42))
        outer_obj = Outer(inner=inner_obj, count=U8(1))

        assert outer_obj.inner.value == U16(42)
        assert outer_obj.count == U8(1)

        # Modify nested field
        outer_obj.inner.value = U16(100)
        assert outer_obj.inner.value == U16(100)

    def test_container_inheritance(self):
        """Test container inheritance patterns."""
        @dataclass
        class Base(Container):
            a: U8

        @dataclass
        class Derived(Base):
            b: U16

        obj = Derived(a=U8(1), b=U16(2))
        assert obj.a == U8(1)
        assert obj.b == U16(2)

        # Should have both fields
        fields = obj.get_fields()
        field_names = [name for name, _ in fields]
        assert 'a' in field_names
        assert 'b' in field_names


class TestVectorTypes:
    """Test vector type system."""

    def test_vector_creation(self):
        """Test creating vectors."""
        # Fixed-size vector of uint8
        vec = Vector([U8(i) for i in range(10)], length=10, element_type=U8)
        assert len(vec) == 10
        assert vec[0] == U8(0)
        assert vec[9] == U8(9)

    def test_vector_bounds(self):
        """Test vector length constraints."""
        # Correct length
        vec = Vector([U8(1), U8(2), U8(3)], length=3, element_type=U8)
        assert len(vec) == 3

        # Wrong length should raise
        with pytest.raises(ValueError):
            Vector([U8(1), U8(2)], length=3, element_type=U8)

        with pytest.raises(ValueError):
            Vector([U8(1), U8(2), U8(3), U8(4)], length=3, element_type=U8)

    def test_vector_modification(self):
        """Test modifying vector elements."""
        vec = Vector([U8(0)] * 5, length=5, element_type=U8)

        # Modify element
        vec[2] = U8(42)
        assert vec[2] == U8(42)

        # Cannot append (fixed size)
        with pytest.raises(NotImplementedError):
            vec.append(U8(10))

        # Cannot remove (fixed size)
        with pytest.raises(NotImplementedError):
            vec.pop()

    def test_vector_of_vectors(self):
        """Test nested vectors."""
        inner_vecs = [
            Vector([U8(i+j) for j in range(3)], length=3, element_type=U8)
            for i in range(0, 6, 3)
        ]
        outer_vec = Vector(inner_vecs, length=2, element_type=Vector)

        assert len(outer_vec) == 2
        assert len(outer_vec[0]) == 3
        assert outer_vec[0][0] == U8(0)
        assert outer_vec[1][0] == U8(3)


class TestListTypes:
    """Test list type system."""

    def test_list_creation(self):
        """Test creating lists."""
        # Variable-size list with max length
        lst = SSZList([U8(i) for i in range(5)], max_length=10, element_type=U8)
        assert len(lst) == 5
        assert lst[0] == U8(0)
        assert lst[4] == U8(4)

    def test_list_bounds(self):
        """Test list max length constraints."""
        # Within bounds
        lst = SSZList([U8(1), U8(2), U8(3)], max_length=5, element_type=U8)
        assert len(lst) == 3

        # Exceeds max length
        with pytest.raises(ValueError):
            SSZList([U8(i) for i in range(10)], max_length=5, element_type=U8)

    def test_list_modification(self):
        """Test modifying list elements."""
        lst = SSZList([U8(0), U8(1), U8(2)], max_length=10, element_type=U8)

        # Modify element
        lst[1] = U8(42)
        assert lst[1] == U8(42)

        # Append element
        lst.append(U8(3))
        assert len(lst) == 4
        assert lst[3] == U8(3)

        # Cannot exceed max length
        lst2 = SSZList([U8(i) for i in range(10)], max_length=10, element_type=U8)
        with pytest.raises(ValueError):
            lst2.append(U8(10))

    def test_empty_list(self):
        """Test empty lists."""
        lst = SSZList([], max_length=10, element_type=U8)
        assert len(lst) == 0

        # Can append to empty list
        lst.append(U8(42))
        assert len(lst) == 1
        assert lst[0] == U8(42)


class TestBitvectorTypes:
    """Test bitvector type system."""

    def test_bitvector_sizes(self):
        """Test various bitvector sizes."""
        # Small bitvector
        bv1 = Bitvector([True], length=1)
        assert len(bv1) == 1
        assert bv1[0] is True

        # Medium bitvector
        bv8 = Bitvector([False] * 8, length=8)
        assert len(bv8) == 8
        assert all(not bit for bit in bv8)

        # Large bitvector
        bv256 = Bitvector([True, False] * 128, length=256)
        assert len(bv256) == 256
        assert bv256[0] is True
        assert bv256[1] is False

        # Very large bitvector
        bv1024 = Bitvector([False] * 1024, length=1024)
        assert len(bv1024) == 1024

    def test_bitvector_iteration(self):
        """Test iterating over bitvector."""
        pattern = [True, False, True, True, False, False, True, False]
        bv = Bitvector(pattern, length=8)

        # Iterate and check
        for i, bit in enumerate(bv):
            assert bit == pattern[i]

        # List conversion
        assert list(bv) == pattern

    def test_bitvector_modification(self):
        """Test modifying bitvector bits."""
        bv = Bitvector([False] * 8, length=8)

        # Set individual bits
        bv[0] = True
        bv[3] = True
        bv[7] = True

        assert bv[0] is True
        assert bv[1] is False
        assert bv[3] is True
        assert bv[7] is True

        # Check bounds
        with pytest.raises(IndexError):
            _ = bv[8]

        with pytest.raises(IndexError):
            bv[8] = True


class TestBitlistTypes:
    """Test bitlist type system."""

    def test_bitlist_sizes(self):
        """Test various bitlist sizes."""
        # Empty bitlist
        bl0 = Bitlist([], max_length=10)
        assert len(bl0) == 0

        # Small bitlist
        bl4 = Bitlist([True, False, True, False], max_length=10)
        assert len(bl4) == 4

        # At max length
        bl10 = Bitlist([True] * 10, max_length=10)
        assert len(bl10) == 10

    def test_bitlist_modification(self):
        """Test modifying bitlist."""
        bl = Bitlist([True, False], max_length=10)

        # Append bits
        bl.append(True)
        assert len(bl) == 3
        assert bl[2] is True

        # Extend with multiple bits
        bl.extend([False, True])
        assert len(bl) == 5
        assert bl[3] is False
        assert bl[4] is True

        # Cannot exceed max length
        bl_full = Bitlist([True] * 10, max_length=10)
        with pytest.raises(ValueError):
            bl_full.append(False)

    def test_bitlist_access(self):
        """Test accessing bitlist elements."""
        bl = Bitlist([True, False, True, False, True], max_length=10)

        # Direct access
        assert bl[0] is True
        assert bl[1] is False
        assert bl[4] is True

        # Negative indexing
        assert bl[-1] is True
        assert bl[-2] is False

        # Modification
        bl[2] = False
        assert bl[2] is False


class TestUnionTypes:
    """Test union type system."""

    def test_union_creation(self):
        """Test creating union types."""
        # Simple union
        UnionType = create_union_class(U8, U16, U32)

        # Create with first type
        u1 = UnionType(selector=0, value=U8(42))
        assert u1.selector == 0
        assert u1.value == U8(42)

        # Create with second type
        u2 = UnionType(selector=1, value=U16(1000))
        assert u2.selector == 1
        assert u2.value == U16(1000)

        # Create with third type
        u3 = UnionType(selector=2, value=U32(100000))
        assert u3.selector == 2
        assert u3.value == U32(100000)

    def test_union_with_none(self):
        """Test union with None option."""
        UnionType = create_union_class(None, U16, U32)

        # None variant
        u_none = UnionType(selector=0, value=None)
        assert u_none.selector == 0
        assert u_none.value is None

        # Other variants
        u_u16 = UnionType(selector=1, value=U16(100))
        assert u_u16.selector == 1
        assert u_u16.value == U16(100)

    def test_union_validation(self):
        """Test union validation."""
        UnionType = create_union_class(U8, U16)

        # Valid selectors
        UnionType(selector=0, value=U8(1))
        UnionType(selector=1, value=U16(2))

        # Invalid selector
        with pytest.raises(ValueError):
            UnionType(selector=2, value=U8(1))

        # Mismatched value type
        with pytest.raises(ValueError):
            UnionType(selector=0, value=None)  # Expects U8, got None

    def test_union_with_containers(self):
        """Test union with container types."""
        @dataclass
        class ContainerA(Container):
            x: U8

        @dataclass
        class ContainerB(Container):
            y: U16
            z: U16

        UnionType = create_union_class(ContainerA, ContainerB)

        # Union with first container
        u1 = UnionType(selector=0, value=ContainerA(x=U8(42)))
        assert u1.selector == 0
        assert u1.value.x == U8(42)

        # Union with second container
        u2 = UnionType(selector=1, value=ContainerB(y=U16(100), z=U16(200)))
        assert u2.selector == 1
        assert u2.value.y == U16(100)
        assert u2.value.z == U16(200)


class TestTreeDepth:
    """Test merkle tree depth calculations."""

    def test_container_tree_depth(self):
        """Test tree depth for containers."""
        @dataclass
        class OneField(Container):
            a: U8

        @dataclass
        class TwoFields(Container):
            a: U8
            b: U8

        @dataclass
        class ThreeFields(Container):
            a: U8
            b: U8
            c: U8

        @dataclass
        class FourFields(Container):
            a: U8
            b: U8
            c: U8
            d: U8

        # Tree depth is based on number of fields
        # depth = ceil(log2(num_fields))
        # 1 field -> depth 0
        # 2 fields -> depth 1
        # 3-4 fields -> depth 2
        # This would need to be implemented in our Container class
        pass  # Depth calculation not yet implemented

    def test_vector_tree_depth(self):
        """Test tree depth for vectors."""
        # Tree depth based on number of elements
        # Would need implementation in Vector class
        pass  # Depth calculation not yet implemented


class TestComplexInheritance:
    """Test complex inheritance scenarios."""

    def test_multiple_inheritance(self):
        """Test multiple inheritance with containers."""
        @dataclass
        class Base1(Container):
            a: U8

        @dataclass
        class Base2(Container):
            b: U16

        # Note: Multiple inheritance with Container may not work as expected
        # This is a limitation of the current design
        # In remerkleable, they handle this with metaclasses

    def test_deep_inheritance(self):
        """Test deep inheritance chains."""
        @dataclass
        class Level1(Container):
            a: U8

        @dataclass
        class Level2(Level1):
            b: U16

        @dataclass
        class Level3(Level2):
            c: U32

        obj = Level3(a=U8(1), b=U16(2), c=U32(3))
        assert obj.a == U8(1)
        assert obj.b == U16(2)
        assert obj.c == U32(3)
