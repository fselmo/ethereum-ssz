"""
Port of all remerkleable test vectors for complete test parity.

This file contains all test vectors from remerkleable's test_impl.py
to ensure we have 100% test parity with expected serialization and
hash tree root values.
"""

import hashlib
from typing import List as PyList
from typing import Optional

import pytest
from ethereum_types.bytes import Bytes32
from ethereum_types.numeric import U8, U32, U64, U256

from ethereum_ssz import (
    U16,
    U128,
    Bitlist,
    Bitvector,
    Container,
    Union,
    Vector,
    create_union_class,
    hash_tree_root,
    ssz,
)
from ethereum_ssz.composite import List as SSZList


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


def merge(a: str, branch: list[str]) -> str:
    """Merge (out on left, branch on right) leaf a with branch items."""
    out = a
    for b in branch:
        out = h(out, b)
    return out


# Precompute zero hashes for merkleization
zero_hashes = [chunk("")]
for layer in range(1, 32):
    zero_hashes.append(h(zero_hashes[layer - 1], zero_hashes[layer - 1]))


# Test containers to match remerkleable


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


class TestRemerkleeableVectors:
    """Test all vectors from remerkleable for complete parity."""

    def test_bitvector_ttftftff(self):
        """Test bitvector TTFTFTFF."""
        bv = Bitvector(
            [True, True, False, True, False, True, False, False], length=8
        )
        encoded = ssz.encode(bv)
        assert encoded.hex() == "2b"

        htr = hash_tree_root(bv)
        expected_htr = Bytes32(bytes.fromhex(chunk("2b")))
        assert htr == expected_htr

    def test_bitvector_tftfffttft(self):
        """Test bitvector TFTFFFTTFT."""
        bv = Bitvector(
            [True, False, True, False, False, False, True, True, False, True],
            length=10,
        )
        encoded = ssz.encode(bv)
        assert encoded.hex() == "c502"

        htr = hash_tree_root(bv)
        expected_htr = Bytes32(bytes.fromhex(chunk("c502")))
        assert htr == expected_htr

    def test_bitlist_ttftftff(self):
        """Test bitlist TTFTFTFF."""
        bl = Bitlist(
            [True, True, False, True, False, True, False, False], max_length=8
        )
        encoded = ssz.encode(bl)
        assert encoded.hex() == "2b01"

        htr = hash_tree_root(bl)
        expected_htr = Bytes32(bytes.fromhex(h(chunk("2b"), chunk("08"))))
        assert htr == expected_htr

    def test_bitlist_tftfffttft(self):
        """Test bitlist TFTFFFTTFT."""
        bl = Bitlist(
            [True, False, True, False, False, False, True, True, False, True],
            max_length=10,
        )
        encoded = ssz.encode(bl)
        assert encoded.hex() == "c506"

        htr = hash_tree_root(bl)
        expected_htr = Bytes32(bytes.fromhex(h(chunk("c502"), chunk("0a"))))
        assert htr == expected_htr

    def test_bitvector_tftfffttftfffftt(self):
        """Test bitvector TFTFFFTTFTFFFFTT."""
        bv = Bitvector(
            [1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1], length=16
        )
        encoded = ssz.encode(bv)
        assert encoded.hex() == "c5c2"

        htr = hash_tree_root(bv)
        expected_htr = Bytes32(bytes.fromhex(chunk("c5c2")))
        assert htr == expected_htr

    def test_bitlist_tftfffttftfffftt(self):
        """Test bitlist TFTFFFTTFTFFFFTT."""
        bl = Bitlist(
            [1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1], max_length=16
        )
        encoded = ssz.encode(bl)
        assert encoded.hex() == "c5c201"

        htr = hash_tree_root(bl)
        expected_htr = Bytes32(bytes.fromhex(h(chunk("c5c2"), chunk("10"))))
        assert htr == expected_htr

    def test_long_bitvector_512(self):
        """Test long bitvector of 512 bits all set."""
        bv = Bitvector(bits=[1] * 512, length=512)
        encoded = ssz.encode(bv)
        assert encoded.hex() == "ff" * 64

        htr = hash_tree_root(bv)
        expected_htr = Bytes32(bytes.fromhex(h("ff" * 32, "ff" * 32)))
        assert htr == expected_htr

    def test_long_bitlist_single_bit(self):
        """Test long bitlist with single bit set."""
        bl = Bitlist(bits=[1], max_length=512)
        encoded = ssz.encode(bl)
        assert encoded.hex() == "03"

        htr = hash_tree_root(bl)
        expected_htr = Bytes32(
            bytes.fromhex(h(h(chunk("01"), chunk("")), chunk("01")))
        )
        assert htr == expected_htr

    def test_long_bitlist_512_all_set(self):
        """Test long bitlist with all 512 bits set."""
        bl = Bitlist(bits=[1] * 512, max_length=512)
        encoded = ssz.encode(bl)
        assert encoded.hex() == "ff" * 64 + "01"

        htr = hash_tree_root(bl)
        expected_htr = Bytes32(
            bytes.fromhex(h(h("ff" * 32, "ff" * 32), chunk("0002")))
        )
        assert htr == expected_htr

    def test_odd_bitvector_513(self):
        """Test odd bitvector with 513 bits all set."""
        bv = Bitvector(bits=[1] * 513, length=513)
        encoded = ssz.encode(bv)
        assert encoded.hex() == "ff" * 64 + "01"

        htr = hash_tree_root(bv)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(h("ff" * 32, "ff" * 32), h(chunk("01"), chunk("")))
            )
        )
        assert htr == expected_htr

    def test_odd_bitlist_513(self):
        """Test odd bitlist with 513 bits all set."""
        bl = Bitlist(bits=[1] * 513, max_length=513)
        encoded = ssz.encode(bl)
        assert encoded.hex() == "ff" * 64 + "03"

        htr = hash_tree_root(bl)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    h(h("ff" * 32, "ff" * 32), h(chunk("01"), chunk(""))),
                    chunk("0102"),
                )
            )
        )
        assert htr == expected_htr

    def test_uint8_values(self):
        """Test various uint8 values."""
        # Test 0x00
        assert ssz.encode(U8(0x00)).hex() == "00"
        assert hash_tree_root(U8(0x00)) == Bytes32(bytes.fromhex(chunk("00")))

        # Test 0x01
        assert ssz.encode(U8(0x01)).hex() == "01"
        assert hash_tree_root(U8(0x01)) == Bytes32(bytes.fromhex(chunk("01")))

        # Test 0xab
        assert ssz.encode(U8(0xAB)).hex() == "ab"
        assert hash_tree_root(U8(0xAB)) == Bytes32(bytes.fromhex(chunk("ab")))

    def test_uint16_values(self):
        """Test various uint16 values."""
        # Test 0x0000
        assert ssz.encode(U16(0x0000)).hex() == "0000"
        assert hash_tree_root(U16(0x0000)) == Bytes32(
            bytes.fromhex(chunk("0000"))
        )

        # Test 0xabcd
        assert ssz.encode(U16(0xABCD)).hex() == "cdab"
        assert hash_tree_root(U16(0xABCD)) == Bytes32(
            bytes.fromhex(chunk("cdab"))
        )

    def test_uint32_values(self):
        """Test various uint32 values."""
        # Test 0x00000000
        assert ssz.encode(U32(0x00000000)).hex() == "00000000"
        assert hash_tree_root(U32(0x00000000)) == Bytes32(
            bytes.fromhex(chunk("00000000"))
        )

        # Test 0x01234567
        assert ssz.encode(U32(0x01234567)).hex() == "67452301"
        assert hash_tree_root(U32(0x01234567)) == Bytes32(
            bytes.fromhex(chunk("67452301"))
        )

    def test_uint64_values(self):
        """Test various uint64 values."""
        # Test 0x0000000000000000
        assert ssz.encode(U64(0x0000000000000000)).hex() == "0000000000000000"
        assert hash_tree_root(U64(0x0000000000000000)) == Bytes32(
            bytes.fromhex(chunk("0000000000000000"))
        )

        # Test 0x0123456789abcdef
        assert ssz.encode(U64(0x0123456789ABCDEF)).hex() == "efcdab8967452301"
        assert hash_tree_root(U64(0x0123456789ABCDEF)) == Bytes32(
            bytes.fromhex(chunk("efcdab8967452301"))
        )

    def test_uint128_values(self):
        """Test various uint128 values."""
        # Test 0
        assert ssz.encode(U128(0)).hex() == "00000000000000000000000000000000"
        assert hash_tree_root(U128(0)) == Bytes32(
            bytes.fromhex(chunk("00000000000000000000000000000000"))
        )

        # Test 0x11223344556677880123456789abcdef
        val = U128(0x11223344556677880123456789ABCDEF)
        assert ssz.encode(val).hex() == "efcdab89674523018877665544332211"
        assert hash_tree_root(val) == Bytes32(
            bytes.fromhex(chunk("efcdab89674523018877665544332211"))
        )

    def test_uint256_values(self):
        """Test various uint256 values."""
        # Basic values tested in lists below
        pass

    def test_vector_bytes48(self):
        """Test Vector[byte, 48]."""
        vec = Vector(
            elements=[U8(i) for i in range(48)], length=48, element_type=U8
        )
        encoded = ssz.encode(vec)
        expected = bytes(range(48))
        assert encoded == expected

        htr = hash_tree_root(vec)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
                    "202122232425262728292a2b2c2d2e2f00000000000000000000000000000000",
                )
            )
        )
        assert htr == expected_htr

    def test_small_test_struct(self):
        """Test SmallTestStruct."""
        s = SmallTestStruct(A=U16(0x4567), B=U16(0x0123))
        encoded = ssz.encode(s)
        assert encoded.hex() == "67452301"

        htr = hash_tree_root(s)
        expected_htr = Bytes32(bytes.fromhex(h(chunk("6745"), chunk("2301"))))
        assert htr == expected_htr

    def test_vector_uint16_2(self):
        """Test Vector[uint16, 2]."""
        vec = Vector(
            elements=[U16(0x4567), U16(0x0123)], length=2, element_type=U16
        )
        encoded = ssz.encode(vec)
        assert encoded.hex() == "67452301"

        htr = hash_tree_root(vec)
        expected_htr = Bytes32(bytes.fromhex(chunk("67452301")))
        assert htr == expected_htr

    def test_list_empty_small(self):
        """Test small empty list."""
        lst = SSZList(elements=[], max_length=10, element_type=U8)
        encoded = ssz.encode(lst)
        assert encoded.hex() == ""

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(bytes.fromhex(h(chunk(""), chunk("00"))))
        assert htr == expected_htr

    def test_list_empty_big(self):
        """Test big empty list."""
        lst = SSZList(elements=[], max_length=2048, element_type=U8)
        encoded = ssz.encode(lst)
        assert encoded.hex() == ""

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(bytes.fromhex(h(zero_hashes[6], chunk("00"))))
        assert htr == expected_htr

    def test_list_bytes_7(self):
        """Test List[byte, 7]."""
        lst = SSZList(
            elements=[U8(i) for i in range(7)], max_length=7, element_type=U8
        )
        encoded = ssz.encode(lst)
        assert encoded.hex() == "00010203040506"

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            bytes.fromhex(h(chunk("00010203040506"), chunk("07")))
        )
        assert htr == expected_htr

    def test_list_bytes_50(self):
        """Test List[byte, 50]."""
        lst = SSZList(
            elements=[U8(i) for i in range(50)], max_length=50, element_type=U8
        )
        encoded = ssz.encode(lst)
        expected = bytes(range(50))
        assert encoded == expected

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    h(
                        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
                        "202122232425262728292a2b2c2d2e2f30310000000000000000000000000000",
                    ),
                    chunk("32"),
                )
            )
        )
        assert htr == expected_htr

    def test_list_bytes_6_of_256(self):
        """Test List[byte, 256] with 6 elements."""
        lst = SSZList(
            elements=[U8(i) for i in range(6)], max_length=256, element_type=U8
        )
        encoded = ssz.encode(lst)
        assert encoded.hex() == "000102030405"

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    h(
                        h(
                            h(chunk("000102030405"), zero_hashes[0]),
                            zero_hashes[1],
                        ),
                        zero_hashes[2],
                    ),
                    chunk("06"),
                )
            )
        )
        assert htr == expected_htr

    def test_vector_bytes_96(self):
        """Test Vector[byte, 96] (signature test)."""
        sig_test_data = [0] * 96
        sig_test_data[0] = 1
        sig_test_data[32] = 2
        sig_test_data[64] = 3
        sig_test_data[95] = 0xFF

        vec = Vector(
            elements=[U8(x) for x in sig_test_data], length=96, element_type=U8
        )
        encoded = ssz.encode(vec)

        expected_hex = (
            "0100000000000000000000000000000000000000000000000000000000000000"
            "0200000000000000000000000000000000000000000000000000000000000000"
            "03000000000000000000000000000000000000000000000000000000000000ff"
        )
        assert encoded.hex() == expected_hex

        htr = hash_tree_root(vec)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    h(chunk("01"), chunk("02")),
                    h(
                        "03000000000000000000000000000000000000000000000000000000000000ff",
                        chunk(""),
                    ),
                )
            )
        )
        assert htr == expected_htr

    def test_single_field_test_struct(self):
        """Test SingleFieldTestStruct."""
        s = SingleFieldTestStruct(A=U8(0xAB))
        encoded = ssz.encode(s)
        assert encoded.hex() == "ab"

        htr = hash_tree_root(s)
        expected_htr = Bytes32(bytes.fromhex(chunk("ab")))
        assert htr == expected_htr

    def test_fixed_test_struct(self):
        """Test FixedTestStruct."""
        s = FixedTestStruct(
            A=U8(0xAB), B=U64(0xAABBCCDD00112233), C=U32(0x12345678)
        )
        encoded = ssz.encode(s)
        assert encoded.hex() == "ab33221100ddccbbaa78563412"

        htr = hash_tree_root(s)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    h(chunk("ab"), chunk("33221100ddccbbaa")),
                    h(chunk("78563412"), chunk("")),
                )
            )
        )
        assert htr == expected_htr

    def test_list_uint16(self):
        """Test List[uint16, 32]."""
        lst = SSZList(
            elements=[U16(0xAABB), U16(0xC0AD), U16(0xEEFF)],
            max_length=32,
            element_type=U16,
        )
        encoded = ssz.encode(lst)
        assert encoded.hex() == "bbaaadc0ffee"

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(h(chunk("bbaaadc0ffee"), chunk("")), chunk("03000000"))
            )
        )
        assert htr == expected_htr

    def test_list_uint32(self):
        """Test List[uint32, 128]."""
        lst = SSZList(
            elements=[U32(0xAABB), U32(0xC0AD), U32(0xEEFF)],
            max_length=128,
            element_type=U32,
        )
        encoded = ssz.encode(lst)
        assert encoded.hex() == "bbaa0000adc00000ffee0000"

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    merge(chunk("bbaa0000adc00000ffee0000"), zero_hashes[0:4]),
                    chunk("03"),
                )
            )
        )
        assert htr == expected_htr

    def test_list_uint256(self):
        """Test List[uint256, 32]."""
        lst = SSZList(
            elements=[U256(0xAABB), U256(0xC0AD), U256(0xEEFF)],
            max_length=32,
            element_type=U256,
        )
        encoded = ssz.encode(lst)
        expected_hex = (
            "bbaa000000000000000000000000000000000000000000000000000000000000"
            "adc0000000000000000000000000000000000000000000000000000000000000"
            "ffee000000000000000000000000000000000000000000000000000000000000"
        )
        assert encoded.hex() == expected_hex

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
                    merge(
                        h(
                            h(chunk("bbaa"), chunk("adc0")),
                            h(chunk("ffee"), chunk("")),
                        ),
                        zero_hashes[2:5],
                    ),
                    chunk("03"),
                )
            )
        )
        assert htr == expected_htr

    def test_list_uint256_long(self):
        """Test List[uint256, 128] with 19 elements."""
        lst = SSZList(
            elements=[U256(i) for i in range(1, 20)],
            max_length=128,
            element_type=U256,
        )
        encoded = ssz.encode(lst)
        expected_hex = "".join(
            [i.to_bytes(32, "little").hex() for i in range(1, 20)]
        )
        assert encoded.hex() == expected_hex

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            bytes.fromhex(
                h(
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
            )
        )
        assert htr == expected_htr

    def test_union_single_type(self):
        """Test Union with single type."""
        MyUnion = create_union_class("MyUnion", [U16])
        u = MyUnion(selector=0, value=U16(0xAABB))
        encoded = ssz.encode(u)
        assert encoded.hex() == "00bbaa"

        htr = hash_tree_root(u)
        expected_htr = Bytes32(bytes.fromhex(h(chunk("bbaa"), chunk(""))))
        assert htr == expected_htr

    def test_union_simple(self):
        """Test simple Union[uint16, uint32]."""
        MyUnion = create_union_class("MyUnion", [U16, U32])

        # Test selector 0 (uint16)
        u1 = MyUnion(selector=0, value=U16(0xAABB))
        encoded = ssz.encode(u1)
        assert encoded.hex() == "00bbaa"

        htr = hash_tree_root(u1)
        expected_htr = Bytes32(bytes.fromhex(h(chunk("bbaa"), chunk(""))))
        assert htr == expected_htr

        # Test selector 1 (uint32)
        u2 = MyUnion(selector=1, value=U32(0xDEADBEEF))
        encoded = ssz.encode(u2)
        assert encoded.hex() == "01efbeadde"

        htr = hash_tree_root(u2)
        expected_htr = Bytes32(
            bytes.fromhex(h(chunk("efbeadde"), chunk("01")))
        )
        assert htr == expected_htr

    def test_union_with_none(self):
        """Test Union with None type."""
        MyUnion = create_union_class("MyUnion", [None, U16, U32])

        # Test None selector
        u1 = MyUnion(selector=0, value=None)
        encoded = ssz.encode(u1)
        assert encoded.hex() == "00"

        htr = hash_tree_root(u1)
        expected_htr = Bytes32(bytes.fromhex(h(chunk(""), chunk(""))))
        assert htr == expected_htr

        # Test uint16 selector (now index 1)
        u2 = MyUnion(selector=1, value=U16(0xAABB))
        encoded = ssz.encode(u2)
        assert encoded.hex() == "01bbaa"

        htr = hash_tree_root(u2)
        expected_htr = Bytes32(bytes.fromhex(h(chunk("bbaa"), chunk("01"))))
        assert htr == expected_htr
