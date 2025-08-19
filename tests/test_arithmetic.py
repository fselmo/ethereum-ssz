"""
Port of remerkleable test_arithmetic.py.

Tests arithmetic operations on SSZ integer types.
"""

import pytest
from ethereum_types.numeric import U8, U32, U64, U256

from ethereum_ssz import U16, U128


class TestUintArithmetic:
    """Test arithmetic operations on unsigned integer types."""

    def test_uint8_arithmetic(self):
        """Test basic arithmetic on U8."""
        a = U8(10)
        b = U8(3)

        # Addition
        assert a + b == U8(13)
        assert b + a == U8(13)

        # Subtraction
        assert a - b == U8(7)

        # Multiplication
        assert a * b == U8(30)
        assert b * a == U8(30)

        # Floor division
        assert a // b == U8(3)

        # Modulo
        assert a % b == U8(1)

        # Bitwise AND
        assert a & b == U8(2)  # 1010 & 0011 = 0010

        # Bitwise OR
        assert a | b == U8(11)  # 1010 | 0011 = 1011

        # Bitwise XOR
        assert a ^ b == U8(9)  # 1010 ^ 0011 = 1001

    def test_uint16_arithmetic(self):
        """Test basic arithmetic on U16."""
        a = U16(1000)
        b = U16(300)

        assert a + b == U16(1300)
        assert a - b == U16(700)
        # Multiplication that doesn't overflow
        c = U16(100)
        d = U16(200)
        assert c * d == U16(20000)
        assert a // b == U16(3)
        assert a % b == U16(100)

        # NOTE: ethereum-types raises OverflowError on overflow,
        # while remerkleable raises ValueError. Both are correct.
        # Testing overflow behavior:
        with pytest.raises(OverflowError):
            # This would overflow U16 bounds
            U16(1000) * U16(300)  # 300000 > 65535

    def test_uint32_arithmetic(self):
        """Test basic arithmetic on U32."""
        a = U32(0x10000000)
        b = U32(0x01000000)

        assert a + b == U32(0x11000000)
        assert a - b == U32(0x0F000000)
        assert a // b == U32(16)
        assert a & b == U32(0)
        assert a | b == U32(0x11000000)

    def test_uint64_arithmetic(self):
        """Test basic arithmetic on U64."""
        a = U64(0x1000000000000000)
        b = U64(0x0100000000000000)

        assert a + b == U64(0x1100000000000000)
        assert a - b == U64(0x0F00000000000000)
        assert a // b == U64(16)

    def test_uint128_arithmetic(self):
        """Test basic arithmetic on U128."""
        a = U128(0x10000000000000000000000000000000)
        b = U128(0x01000000000000000000000000000000)

        assert a + b == U128(0x11000000000000000000000000000000)
        assert a - b == U128(0x0F000000000000000000000000000000)
        assert a // b == U128(16)

    def test_uint256_arithmetic(self):
        """Test basic arithmetic on U256."""
        a = U256(1000)
        b = U256(300)

        assert a + b == U256(1300)
        assert a - b == U256(700)
        assert a * b == U256(300000)
        assert a // b == U256(3)
        assert a % b == U256(100)


class TestUintBounds:
    """Test boundary conditions for unsigned integers.

    NOTE: ethereum-types raises OverflowError on overflow in arithmetic
    operations, which is correct behavior. This differs from some other
    implementations that use wrapping/modulo arithmetic.
    """

    def test_uint8_bounds(self):
        """Test U8 boundary conditions."""
        # Max value
        max_val = U8(255)
        assert max_val == U8.MAX_VALUE

        # Overflow in arithmetic raises OverflowError
        with pytest.raises(OverflowError):
            max_val + U8(1)

        # Min value
        min_val = U8(0)
        # Underflow in arithmetic raises OverflowError
        with pytest.raises(OverflowError):
            min_val - U8(1)

    def test_uint16_bounds(self):
        """Test U16 boundary conditions."""
        max_val = U16(65535)
        assert max_val == U16.MAX_VALUE

        # Overflow raises OverflowError
        with pytest.raises(OverflowError):
            max_val + U16(1)

        min_val = U16(0)
        # Underflow raises OverflowError
        with pytest.raises(OverflowError):
            min_val - U16(1)

    def test_uint32_bounds(self):
        """Test U32 boundary conditions."""
        max_val = U32(0xFFFFFFFF)
        assert max_val == U32.MAX_VALUE

        # Overflow raises OverflowError
        with pytest.raises(OverflowError):
            max_val + U32(1)

    def test_uint64_bounds(self):
        """Test U64 boundary conditions."""
        max_val = U64(0xFFFFFFFFFFFFFFFF)
        assert max_val == U64.MAX_VALUE

        # Overflow raises OverflowError
        with pytest.raises(OverflowError):
            max_val + U64(1)

    def test_uint128_bounds(self):
        """Test U128 boundary conditions."""
        max_val = U128((1 << 128) - 1)
        assert max_val == U128.MAX_VALUE

        # Overflow raises OverflowError
        with pytest.raises(OverflowError):
            max_val + U128(1)

    def test_uint256_bounds(self):
        """Test U256 boundary conditions."""
        max_val = U256((1 << 256) - 1)
        assert max_val == U256.MAX_VALUE

        # Overflow raises OverflowError
        with pytest.raises(OverflowError):
            max_val + U256(1)


class TestUintShifts:
    """Test bit shift operations on unsigned integers.

    NOTE: Shift operators are NOT implemented in ethereum-types.
    These tests are marked as expected failures.
    """

    @pytest.mark.xfail(
        reason="Shift operators not implemented in ethereum-types"
    )
    def test_uint8_shifts(self):
        """Test shift operations on U8."""
        a = U8(0b10101010)

        # Left shift
        assert a << 1 == U8(0b01010100)  # Overflow bits are lost
        assert a << 2 == U8(0b10101000)
        assert a << 4 == U8(0b10100000)

        # Right shift
        assert a >> 1 == U8(0b01010101)
        assert a >> 2 == U8(0b00101010)
        assert a >> 4 == U8(0b00001010)

    @pytest.mark.xfail(
        reason="Shift operators not implemented in ethereum-types"
    )
    def test_uint16_shifts(self):
        """Test shift operations on U16."""
        a = U16(0b1010101010101010)

        assert a << 1 == U16(0b0101010101010100)
        assert a >> 1 == U16(0b0101010101010101)

    @pytest.mark.xfail(
        reason="Shift operators not implemented in ethereum-types"
    )
    def test_uint32_shifts(self):
        """Test shift operations on U32."""
        a = U32(0x80000000)

        assert a >> 1 == U32(0x40000000)
        assert a >> 31 == U32(1)
        assert U32(1) << 31 == a


class TestUintPower:
    """Test power operations on unsigned integers.

    NOTE: Power operator is NOT implemented in ethereum-types.
    These tests are marked as expected failures.
    """

    @pytest.mark.xfail(
        reason="Power operator not implemented in ethereum-types"
    )
    def test_uint_pow(self):
        """Test power operations."""
        assert U8(2) ** 3 == U8(8)
        assert U8(2) ** 7 == U8(128)
        # Overflow raises OverflowError
        with pytest.raises(OverflowError):
            U8(2) ** 8  # Would be 256

        assert U16(2) ** 10 == U16(1024)
        # Overflow raises OverflowError
        with pytest.raises(OverflowError):
            U16(2) ** 16  # Would be 65536

        assert U32(2) ** 20 == U32(1048576)
        assert U64(2) ** 40 == U64(1099511627776)


class TestUintBitwise:
    """Test bitwise operations on unsigned integers."""

    def test_uint_invert(self):
        """Test bitwise NOT operation."""
        assert ~U8(0) == U8(255)
        assert ~U8(255) == U8(0)
        assert ~U8(0b10101010) == U8(0b01010101)

        assert ~U16(0) == U16(65535)
        assert ~U16(0xFF00) == U16(0x00FF)

        assert ~U32(0) == U32(0xFFFFFFFF)
        assert ~U64(0) == U64(0xFFFFFFFFFFFFFFFF)

    def test_uint_bitwise_ops(self):
        """Test various bitwise operations."""
        a = U8(0b11110000)
        b = U8(0b10101010)

        assert a & b == U8(0b10100000)
        assert a | b == U8(0b11111010)
        assert a ^ b == U8(0b01011010)

        # Test with larger types
        x = U32(0xFF00FF00)
        y = U32(0x00FF00FF)

        assert x & y == U32(0)
        assert x | y == U32(0xFFFFFFFF)
        assert x ^ y == U32(0xFFFFFFFF)


class TestMixedOperations:
    """Test operations between different uint types."""

    def test_mixed_arithmetic(self):
        """Test arithmetic between different sized uints."""
        # Operations typically promote to the larger type
        a = U8(10)
        b = U16(1000)

        # Result should be U16
        result = b + U16(a)
        assert result == U16(1010)
        assert isinstance(result, U16)

        # Multiplication
        result = b * U16(a)
        assert result == U16(10000)

    def test_mixed_comparison(self):
        """Test comparisons between different sized uints."""
        assert U8(10) == U8(10)
        assert U8(10) != U8(11)
        assert U8(10) < U8(11)
        assert U8(11) > U8(10)
        assert U8(10) <= U8(10)
        assert U8(10) >= U8(10)

        # NOTE: ethereum-types compares values across types, not type identity
        # This differs from remerkleable which considers type in equality
        # assert U8(10) != U16(10)  # Would fail - they're equal in ethereum-types
        assert U8(10) == U16(10)  # This is the actual behavior


class TestUintIdentity:
    """Test unary operations."""

    def test_uint_pos_neg_abs(self):
        """Test unary +, -, abs operations."""
        a = U8(42)

        # Unary plus (identity)
        assert +a == a

        # Abs (always identity for unsigned)
        assert abs(a) == a

        # NOTE: ethereum-types unary minus returns a regular int, not a uint type
        # This differs from remerkleable which raises OperationNotSupported
        assert -U8(1) == -1  # Returns negative int
        assert -U8(0) == 0
        assert -U8(100) == -100
