# Missing Operations in ethereum-types

**Note:** This document describes limitations in the `ethereum-types` library (not `ethereum-ssz`) that prevent full arithmetic compatibility with remerkleable's uint types. These missing operations cause 4 expected test failures in our test suite but do not affect SSZ serialization functionality.

This document lists operations that are present in remerkleable but missing or behave differently in ethereum-types.

## 1. Bitwise Shift Operations

**Missing**: `<<` (left shift) and `>>` (right shift) operators

```python
# In remerkleable:
uint8(0b10101010) << 1  # Returns uint8(0b01010100)
uint8(0b10101010) >> 1  # Returns uint8(0b01010101)

# In ethereum-types:
U8(0b10101010) << 1  # TypeError: unsupported operand type(s)
U8(0b10101010) >> 1  # TypeError: unsupported operand type(s)
```

**Impact**: Cannot perform bit manipulation operations commonly used in cryptographic and low-level operations.

## 2. Power Operator

**Missing**: `**` (power/exponentiation) operator

```python
# In remerkleable:
uint8(2) ** 3  # Returns uint8(8)

# In ethereum-types:
U8(2) ** 3  # TypeError: unsupported operand type(s) for ** or pow()
```

**Impact**: Cannot use power operations directly on uint types.

## 3. Overflow Behavior

**Difference**: Arithmetic overflow handling

```python
# In remerkleable:
uint8(255) + uint8(1)  # Raises ValueError

# In ethereum-types:
U8(255) + U8(1)  # Raises OverflowError (different exception type)

# Also, direct construction with overflow:
U8(256)  # Raises OverflowError, not ValueError
```

**Impact**: Different exception types for the same error condition. Both are correct, just inconsistent.

## 4. Unary Negation

**Difference**: Behavior of unary minus operator

```python
# In remerkleable:
-uint8(1)  # Raises OperationNotSupported

# In ethereum-types:
-U8(1)  # Returns U8(255) - wraps around
-U8(0)  # Returns U8(0)
```

**Impact**: ethereum-types allows negation with wrapping, while remerkleable explicitly forbids it.

## 5. Cross-Type Comparisons

**Difference**: Comparing different uint types

```python
# In remerkleable:
uint8(10) != uint16(10)  # True (different types)

# In ethereum-types:
U8(10) != U16(10)  # False (compares values, not types)
```

**Impact**: Type safety - ethereum-types allows cross-type value comparison which may hide type errors.

## 6. Bitwise NOT Operation

**Status**: Needs verification

```python
# In remerkleable:
~uint8(0)  # Returns uint8(255)

# In ethereum-types:
~U8(0)  # Needs testing
```

## Summary of Required Changes

To achieve full compatibility with remerkleable:

1. **Add shift operators** (`__lshift__`, `__rshift__`, `__rlshift__`, `__rrshift__`)
2. **Add power operator** (`__pow__`, `__rpow__`)
3. **Consider standardizing overflow exceptions** (ValueError vs OverflowError)
4. **Fix unary negation** to raise an error instead of wrapping
5. **Fix type comparisons** to consider type identity, not just value

## Workarounds

For missing operations, use these workarounds:

```python
# Shift operations
def left_shift(value: U8, shift: int) -> U8:
    result = (value._number << shift) & 0xFF
    return U8(result)

def right_shift(value: U8, shift: int) -> U8:
    result = value._number >> shift
    return U8(result)

# Power operation
def power(base: U8, exp: int) -> U8:
    result = base._number ** exp
    if result > 255:
        raise OverflowError()
    return U8(result)
```

## Tests Affected

The following test methods are affected by these missing operations:
- `test_uint8_shifts` - Missing shift operators
- `test_uint16_shifts` - Missing shift operators
- `test_uint32_shifts` - Missing shift operators
- `test_uint_pow` - Missing power operator
- `test_uint_pos_neg_abs` - Different negation behavior
- `test_mixed_comparison` - Different type comparison behavior
- `test_uint_value_bounds` - Different overflow behavior (constructor)