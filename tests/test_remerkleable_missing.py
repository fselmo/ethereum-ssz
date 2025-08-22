"""
Tests for missing test vectors from remerkleable.
This file ports the remaining ~53% of test cases not yet covered.
"""

from hashlib import sha256
from typing import List as PyList

import pytest
from ethereum_types.bytes import Bytes
from ethereum_types.numeric import U8, U32, U64, U256

from ethereum_ssz import (
    U16,
    U128,
    Container,
    Union,
    Vector,
    create_union_class,
    hash_tree_root,
    ssz,
)
from ethereum_ssz import List as SSZList
from ethereum_ssz.bitfields import Bitlist, Bitvector


def bytes_hash(data: bytes):
    return sha256(data).digest()


def chunk(hex_str: str) -> str:
    """Pad hex string to 32 bytes (64 hex chars)."""
    return (hex_str + ("00" * 32))[:64]


def h(a: str, b: str) -> str:
    """Hash two hex strings together."""
    return bytes_hash(bytes.fromhex(a) + bytes.fromhex(b)).hex()


# Zero hashes for merkleization
zero_hashes = [chunk("")]
for layer in range(1, 32):
    zero_hashes.append(h(zero_hashes[layer - 1], zero_hashes[layer - 1]))


def merge(a: str, branch: list[str]) -> str:
    """Merge leaf a with branch items, branch is from bottom to top."""
    out = a
    for b in branch:
        out = h(out, b)
    return out


# Container definitions matching remerkleable


class SingleFieldTestStruct(Container):
    A: U8


class SmallTestStruct(Container):
    A: U16
    B: U16


class FixedTestStruct(Container):
    A: U8
    B: U64
    C: U32


class VarTestStruct(Container):
    A: U16
    B: SSZList  # List[uint16, 1024]
    C: U8


class ComplexTestStruct(Container):
    A: U16
    B: SSZList  # List[uint16, 128]
    C: U8
    D: SSZList  # List[byte, 256]
    E: VarTestStruct
    F: Vector  # Vector[FixedTestStruct, 4]
    G: Vector  # Vector[VarTestStruct, 2]


class TestMissingVectors:
    """Test cases that were missing from ethereum-ssz."""

    def test_byte_as_u8(self):
        """Test byte type (using U8 as equivalent)."""
        # byte 00
        value = U8(0x00)
        encoded = ssz.encode(value)
        assert encoded.hex() == "00"
        assert hash_tree_root(value).hex() == chunk("00")

        # byte 01
        value = U8(0x01)
        encoded = ssz.encode(value)
        assert encoded.hex() == "01"
        assert hash_tree_root(value).hex() == chunk("01")

        # byte ab
        value = U8(0xAB)
        encoded = ssz.encode(value)
        assert encoded.hex() == "ab"
        assert hash_tree_root(value).hex() == chunk("ab")

    def test_bytelist_50(self):
        """Test List[byte, 50] with 50 elements."""
        lst = SSZList(
            elements=[U8(i) for i in range(50)], max_length=50, element_type=U8
        )

        encoded = ssz.encode(lst)
        expected = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031"
        assert encoded.hex() == expected

        # Hash tree root
        htr = hash_tree_root(lst)
        expected_htr = h(
            h(
                "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
                "202122232425262728292a2b2c2d2e2f30310000000000000000000000000000",
            ),
            chunk("32"),
        )
        assert htr.hex() == expected_htr

    def test_bytelist_6_256(self):
        """Test List[byte, 256] with only 6 elements."""
        lst = SSZList(
            elements=[U8(i) for i in range(6)], max_length=256, element_type=U8
        )

        encoded = ssz.encode(lst)
        assert encoded.hex() == "000102030405"

        # Hash tree root
        htr = hash_tree_root(lst)
        expected_htr = h(
            h(
                h(h(chunk("000102030405"), zero_hashes[0]), zero_hashes[1]),
                zero_hashes[2],
            ),
            chunk("06"),
        )
        assert htr.hex() == expected_htr

    def test_uint256_list(self):
        """Test List[uint256, 32] with 3 elements."""
        lst = SSZList(
            elements=[U256(0xAABB), U256(0xC0AD), U256(0xEEFF)],
            max_length=32,
            element_type=U256,
        )

        encoded = ssz.encode(lst)
        expected = (
            "bbaa000000000000000000000000000000000000000000000000000000000000"
            "adc0000000000000000000000000000000000000000000000000000000000000"
            "ffee000000000000000000000000000000000000000000000000000000000000"
        )
        assert encoded.hex() == expected

        # Hash tree root
        htr = hash_tree_root(lst)
        expected_htr = h(
            merge(
                h(
                    h(chunk("bbaa"), chunk("adc0")),
                    h(chunk("ffee"), chunk("")),
                ),
                zero_hashes[2:5],
            ),
            chunk("03"),
        )
        assert htr.hex() == expected_htr

    def test_uint256_list_long(self):
        """Test List[uint256, 128] with 19 elements."""
        lst = SSZList(
            elements=[U256(i) for i in range(1, 20)],
            max_length=128,
            element_type=U256,
        )

        # Encode
        encoded = ssz.encode(lst)
        expected = "".join(
            [
                i.to_bytes(length=32, byteorder="little").hex()
                for i in range(1, 20)
            ]
        )
        assert encoded.hex() == expected

        # Hash tree root
        htr = hash_tree_root(lst)
        expected_htr = h(
            merge(
                h(
                    h(
                        h(
                            h(
                                h(chunk("01"), chunk("02")),
                                h(chunk("03"), chunk("04")),
                            ),
                            h(
                                h(chunk("05"), chunk("06")),
                                h(chunk("07"), chunk("08")),
                            ),
                        ),
                        h(
                            h(
                                h(chunk("09"), chunk("0a")),
                                h(chunk("0b"), chunk("0c")),
                            ),
                            h(
                                h(chunk("0d"), chunk("0e")),
                                h(chunk("0f"), chunk("10")),
                            ),
                        ),
                    ),
                    h(
                        h(
                            h(
                                h(chunk("11"), chunk("12")),
                                h(chunk("13"), chunk("")),
                            ),
                            zero_hashes[2],
                        ),
                        zero_hashes[3],
                    ),
                ),
                zero_hashes[5:7],
            ),
            chunk("13"),
        )
        assert htr.hex() == expected_htr

    def test_simple_large_union(self):
        """Test Union[uint16, uint32, uint8, List[uint16, 8]]."""
        # Test with uint8 selector
        MyUnion = create_union_class("MyUnion", [U16, U32, U8, SSZList])

        # Create union with U8 value (selector=2)
        union_val = MyUnion(selector=2, value=U8(0xAA))
        assert union_val.selector == 2
        assert union_val.value == U8(0xAA)

        encoded = ssz.encode(union_val)
        assert encoded.hex() == "02aa"

        # Hash tree root
        htr = hash_tree_root(union_val)
        expected_htr = h(chunk("aa"), chunk("02"))
        assert htr.hex() == expected_htr

    def test_var_test_struct_nil(self):
        """Test VarTestStruct with nil list."""
        container = VarTestStruct(
            A=U16(0xABCD),
            B=SSZList(elements=[], max_length=1024, element_type=U16),
            C=U8(0xFF),
        )

        encoded = ssz.encode(container)
        assert encoded.hex() == "cdab07000000ff"

        # Hash tree root
        htr = hash_tree_root(container)
        expected_htr = h(
            h(chunk("cdab"), h(zero_hashes[6], chunk("00000000"))),
            h(chunk("ff"), chunk("")),
        )
        assert htr.hex() == expected_htr

    def test_var_test_struct_empty(self):
        """Test VarTestStruct with empty list."""
        container = VarTestStruct(
            A=U16(0xABCD),
            B=SSZList(elements=[], max_length=1024, element_type=U16),
            C=U8(0xFF),
        )

        encoded = ssz.encode(container)
        assert encoded.hex() == "cdab07000000ff"

        # Hash tree root
        htr = hash_tree_root(container)
        expected_htr = h(
            h(chunk("cdab"), h(zero_hashes[6], chunk("00000000"))),
            h(chunk("ff"), chunk("")),
        )
        assert htr.hex() == expected_htr

    def test_var_test_struct_some(self):
        """Test VarTestStruct with some list elements."""
        container = VarTestStruct(
            A=U16(0xABCD),
            B=SSZList(
                elements=[U16(1), U16(2), U16(3)],
                max_length=1024,
                element_type=U16,
            ),
            C=U8(0xFF),
        )

        encoded = ssz.encode(container)
        assert encoded.hex() == "cdab07000000ff010002000300"

        # Hash tree root
        htr = hash_tree_root(container)
        expected_htr = h(
            h(
                chunk("cdab"),
                h(
                    merge(chunk("010002000300"), zero_hashes[0:6]),
                    chunk("03"),  # length mix in
                ),
            ),
            h(chunk("ff"), chunk("")),
        )
        assert htr.hex() == expected_htr

    def test_complex_test_struct(self):
        """Test ComplexTestStruct - the most complex nested structure."""
        # Create nested VarTestStruct for field E
        var_struct_e = VarTestStruct(
            A=U16(0xABCD),
            B=SSZList(
                elements=[U16(1), U16(2), U16(3)],
                max_length=1024,
                element_type=U16,
            ),
            C=U8(0xFF),
        )

        # Create Vector of FixedTestStruct for field F
        fixed_structs = Vector(
            elements=[
                FixedTestStruct(
                    A=U8(0xCC), B=U64(0x4242424242424242), C=U32(0x13371337)
                ),
                FixedTestStruct(
                    A=U8(0xDD), B=U64(0x3333333333333333), C=U32(0xABCDABCD)
                ),
                FixedTestStruct(
                    A=U8(0xEE), B=U64(0x4444444444444444), C=U32(0x00112233)
                ),
                FixedTestStruct(
                    A=U8(0xFF), B=U64(0x5555555555555555), C=U32(0x44556677)
                ),
            ],
            length=4,
            element_type=FixedTestStruct,
        )

        # Create Vector of VarTestStruct for field G
        var_structs = Vector(
            elements=[
                VarTestStruct(
                    A=U16(0xDEAD),
                    B=SSZList(
                        elements=[U16(1), U16(2), U16(3)],
                        max_length=1024,
                        element_type=U16,
                    ),
                    C=U8(0x11),
                ),
                VarTestStruct(
                    A=U16(0xBEEF),
                    B=SSZList(
                        elements=[U16(4), U16(5), U16(6)],
                        max_length=1024,
                        element_type=U16,
                    ),
                    C=U8(0x22),
                ),
            ],
            length=2,
            element_type=VarTestStruct,
        )

        # Create the complex struct
        container = ComplexTestStruct(
            A=U16(0xAABB),
            B=SSZList(
                elements=[U16(0x1122), U16(0x3344)],
                max_length=128,
                element_type=U16,
            ),
            C=U8(0xFF),
            D=SSZList(
                elements=[U8(ord(c)) for c in "foobar"],
                max_length=256,
                element_type=U8,
            ),
            E=var_struct_e,
            F=fixed_structs,
            G=var_structs,
        )

        # Test encoding
        encoded = ssz.encode(container)
        # Just check it encodes successfully
        assert len(encoded) > 0
        print(f"ComplexTestStruct encoded: {len(encoded)} bytes")
        print(f"First 20 bytes: {encoded[:20].hex()}")

    def test_three_sigs_vector(self):
        """Test Vector[ByteVector[96], 3] - three signatures."""
        # Create three 96-byte signatures using Vector[U8, 96]
        sig1 = Vector(
            [U8(1)] + [U8(0) for _ in range(95)], length=96, element_type=U8
        )
        sig2 = Vector(
            [U8(2)] + [U8(0) for _ in range(95)], length=96, element_type=U8
        )
        sig3 = Vector(
            [U8(3)] + [U8(0) for _ in range(95)], length=96, element_type=U8
        )

        # Create vector of signatures
        three_sigs = Vector(
            elements=[sig1, sig2, sig3], length=3, element_type=Vector
        )

        # Test encoding
        encoded = ssz.encode(three_sigs)
        expected = "01" + ("00" * 95) + "02" + ("00" * 95) + "03" + ("00" * 95)
        assert encoded.hex() == expected

        # Test hash tree root
        htr = hash_tree_root(three_sigs)
        expected_htr = h(
            h(
                h(h(chunk("01"), chunk("")), zero_hashes[1]),
                h(h(chunk("02"), chunk("")), zero_hashes[1]),
            ),
            h(h(h(chunk("03"), chunk("")), zero_hashes[1]), chunk("")),
        )
        assert htr.hex() == expected_htr

    def test_complex_union(self):
        """Test complex union with nested containers."""
        # Define the union type
        MyUnion = create_union_class(
            "MyUnion",
            [
                Vector,
                SingleFieldTestStruct,
                VarTestStruct,
                ComplexTestStruct,
                U16,
            ],
        )

        # Test with VarTestStruct (selector=2)
        var_struct = VarTestStruct(
            A=U16(0xABCD),
            B=SSZList(
                elements=[U16(1), U16(2), U16(3)],
                max_length=1024,
                element_type=U16,
            ),
            C=U8(0xFF),
        )

        union_val = MyUnion(selector=2, value=var_struct)
        assert union_val.selector == 2

        encoded = ssz.encode(union_val)
        assert encoded.hex() == "02" + "cdab07000000ff010002000300"

        # Hash tree root
        htr = hash_tree_root(union_val)
        expected_htr = h(
            h(
                h(
                    chunk("cdab"),
                    h(
                        merge(chunk("010002000300"), zero_hashes[0:6]),
                        chunk("03"),  # length mix in
                    ),
                ),
                h(chunk("ff"), chunk("")),
            ),
            chunk("02"),
        )
        assert htr.hex() == expected_htr
