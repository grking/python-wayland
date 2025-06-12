import struct
from enum import Enum

import pytest

from wayland.message import pack_argument, pad_data, unpack_argument


class MockEnum(Enum):
    VALUE_ONE = 1
    VALUE_TWO = 2
    VALUE_LARGE = 0xFFFFFFFF


class MockObject:
    def __init__(self, object_id):
        self.object_id = object_id


class TestHelpers:
    @staticmethod
    def pack_and_assert(arg_type, value, expected_packet, expected_fds=None):
        if expected_fds is None:
            expected_fds = []
        packet, fds = pack_argument(b"", arg_type, value)
        assert packet == expected_packet
        assert fds == expected_fds
        return packet, fds

    @staticmethod
    def unpack_and_assert(
        packet,
        arg_type,
        expected_value,
        expected_remaining=b"",
        get_fd=None,
        enum_type=None,
        int_to_enum_func=None,
    ):
        remaining, value = unpack_argument(
            packet, arg_type, get_fd, enum_type, int_to_enum_func
        )
        assert remaining == expected_remaining
        assert value == expected_value
        return remaining, value

    @staticmethod
    def roundtrip_test(
        arg_type, original_value, get_fd=None, enum_type=None, int_to_enum_func=None
    ):
        packet, fds = pack_argument(b"", arg_type, original_value)
        remaining, unpacked_value = unpack_argument(
            packet, arg_type, get_fd, enum_type, int_to_enum_func
        )
        assert remaining == b""
        assert unpacked_value == original_value
        return packet, fds, remaining, unpacked_value

    @staticmethod
    def create_array_packet(array_data, length):
        padded_length = (length + 3) & ~3
        if length > 0:
            return struct.pack(f"I{padded_length}s", length, array_data)
        return struct.pack("I", 0)


class TestPadData:
    def test_pad_string_no_padding_needed(self):
        result = pad_data("ab")
        expected = b"ab\x00\x00"
        assert result == expected

    def test_pad_string_with_padding(self):
        result = pad_data("a")
        expected = b"a\x00\x00\x00"
        assert result == expected

    def test_pad_string_exact_boundary(self):
        result = pad_data("abc")
        expected = b"abc\x00"
        assert result == expected

    def test_pad_empty_string(self):
        result = pad_data("")
        expected = b"\x00\x00\x00\x00"
        assert result == expected

    def test_pad_bytes_input(self):
        result = pad_data(b"test")
        expected = b"test\x00\x00\x00\x00"
        assert result == expected

    def test_pad_unicode_string(self):
        result = pad_data("café")
        expected = b"caf\xc3\xa9\x00\x00\x00"
        assert result == expected


class TestPackArgument:
    def test_pack_uint_integer(self):
        TestHelpers.pack_and_assert("uint", 42, struct.pack("I", 42))

    def test_pack_uint_enum(self):
        TestHelpers.pack_and_assert("uint", MockEnum.VALUE_ONE, struct.pack("I", 1))

    def test_pack_uint_large_value(self):
        TestHelpers.pack_and_assert("uint", 0xFFFFFFFF, struct.pack("I", 0xFFFFFFFF))

    def test_pack_new_id_integer(self):
        TestHelpers.pack_and_assert("new_id", 123, struct.pack("I", 123))

    def test_pack_new_id_enum(self):
        TestHelpers.pack_and_assert("new_id", MockEnum.VALUE_TWO, struct.pack("I", 2))

    def test_pack_object_with_object_id(self):
        obj = MockObject(456)
        TestHelpers.pack_and_assert("object", obj, struct.pack("I", 456))

    def test_pack_object_without_object_id(self):
        obj = object()
        TestHelpers.pack_and_assert("object", obj, struct.pack("I", 0))

    def test_pack_object_none(self):
        TestHelpers.pack_and_assert("object", None, struct.pack("I", 0))

    def test_pack_int_positive(self):
        TestHelpers.pack_and_assert("int", 42, struct.pack("i", 42))

    def test_pack_int_negative(self):
        TestHelpers.pack_and_assert("int", -42, struct.pack("i", -42))

    def test_pack_int_zero(self):
        TestHelpers.pack_and_assert("int", 0, struct.pack("i", 0))

    def test_pack_enum_value(self):
        TestHelpers.pack_and_assert("enum", MockEnum.VALUE_ONE, struct.pack("I", 1))

    def test_pack_string_simple(self):
        expected_packet = b"\x06\x00\x00\x00hello\x00\x00\x00"
        TestHelpers.pack_and_assert("string", "hello", expected_packet)

    def test_pack_string_empty(self):
        expected_packet = b"\x01\x00\x00\x00\x00\x00\x00\x00"
        TestHelpers.pack_and_assert("string", "", expected_packet)

    def test_pack_string_unicode(self):
        expected_packet = b"\x06\x00\x00\x00caf\xc3\xa9\x00\x00\x00"
        TestHelpers.pack_and_assert("string", "café", expected_packet)

    def test_pack_string_exact_boundary(self):
        expected_packet = b"\x04\x00\x00\x00abc\x00"
        TestHelpers.pack_and_assert("string", "abc", expected_packet)

    def test_pack_fixed_positive_integer(self):
        expected_value = (42 << 8) | 0
        TestHelpers.pack_and_assert("fixed", 42.0, struct.pack("I", expected_value))

    def test_pack_fixed_with_fraction(self):
        expected_value = (42 << 8) | 128
        TestHelpers.pack_and_assert("fixed", 42.5, struct.pack("I", expected_value))

    def test_pack_fixed_negative(self):
        with pytest.raises(struct.error):
            pack_argument(b"", "fixed", -1.0)

    def test_pack_fixed_small_fraction(self):
        expected_value = (0 << 8) | 64
        TestHelpers.pack_and_assert("fixed", 0.25, struct.pack("I", expected_value))

    def test_pack_fixed_zero(self):
        TestHelpers.pack_and_assert("fixed", 0.0, struct.pack("I", 0))

    def test_pack_appends_to_existing_packet(self):
        packet, fds = pack_argument(b"existing", "int", 42)
        assert packet == b"existing" + struct.pack("i", 42)
        assert fds == []

    def test_pack_fd_argument(self):
        TestHelpers.pack_and_assert("fd", 42, b"", [42])


class TestUnpackArgument:
    def test_unpack_uint(self):
        packet = struct.pack("I", 42)
        TestHelpers.unpack_and_assert(packet, "uint", 42)

    def test_unpack_uint_large_value(self):
        packet = struct.pack("I", 0xFFFFFFFF)
        TestHelpers.unpack_and_assert(packet, "uint", 0xFFFFFFFF)

    def test_unpack_new_id(self):
        packet = struct.pack("I", 123)
        TestHelpers.unpack_and_assert(packet, "new_id", 123)

    def test_unpack_object(self):
        packet = struct.pack("I", 456)
        TestHelpers.unpack_and_assert(packet, "object", 456)

    def test_unpack_object_null(self):
        packet = struct.pack("I", 0)
        TestHelpers.unpack_and_assert(packet, "object", 0)

    def test_unpack_int_positive(self):
        packet = struct.pack("i", 42)
        TestHelpers.unpack_and_assert(packet, "int", 42)

    def test_unpack_int_negative(self):
        packet = struct.pack("i", -42)
        TestHelpers.unpack_and_assert(packet, "int", -42)

    def test_unpack_int_zero(self):
        packet = struct.pack("i", 0)
        TestHelpers.unpack_and_assert(packet, "int", 0)

    def test_unpack_enum_with_enum_type(self):
        packet = struct.pack("I", 1)

        def mock_int_to_enum_func(enum_type, value):
            return enum_type(value)

        TestHelpers.unpack_and_assert(
            packet,
            "enum",
            MockEnum.VALUE_ONE,
            b"",
            None,
            MockEnum,
            mock_int_to_enum_func,
        )

    def test_unpack_fd(self):
        def mock_get_fd():
            return 42

        TestHelpers.unpack_and_assert(b"", "fd", 42, b"", mock_get_fd)

    def test_unpack_string_simple(self):
        packet, _ = pack_argument(b"", "string", "hello")
        TestHelpers.unpack_and_assert(packet, "string", "hello")

    def test_unpack_string_empty(self):
        packet, _ = pack_argument(b"", "string", "")
        TestHelpers.unpack_and_assert(packet, "string", "")

    def test_unpack_string_unicode(self):
        packet, _ = pack_argument(b"", "string", "café")
        TestHelpers.unpack_and_assert(packet, "string", "café")

    def test_unpack_string_exact_boundary(self):
        packet, _ = pack_argument(b"", "string", "abc")
        TestHelpers.unpack_and_assert(packet, "string", "abc")

    def test_unpack_string_with_extra_data(self):
        packet, _ = pack_argument(b"", "string", "hello")
        extra_data = b"extra"
        TestHelpers.unpack_and_assert(
            packet + extra_data, "string", "hello", extra_data
        )

    def test_unpack_array_empty(self):
        packet = struct.pack("I", 0)
        TestHelpers.unpack_and_assert(packet, "array", [])

    def test_unpack_array_single_element(self):
        array_data = struct.pack("I", 42)
        packet = TestHelpers.create_array_packet(array_data, 4)
        TestHelpers.unpack_and_assert(packet, "array", [42])

    def test_unpack_array_multiple_elements(self):
        array_data = struct.pack("III", 1, 2, 3)
        packet = TestHelpers.create_array_packet(array_data, 12)
        TestHelpers.unpack_and_assert(packet, "array", [1, 2, 3])

    def test_unpack_array_with_padding(self):
        array_data = struct.pack("II", 100, 200)
        packet = TestHelpers.create_array_packet(array_data, 8)
        TestHelpers.unpack_and_assert(packet, "array", [100, 200])

    def test_unpack_array_with_extra_data(self):
        array_data = struct.pack("I", 42)
        packet = TestHelpers.create_array_packet(array_data, 4)
        extra_data = b"extra"
        TestHelpers.unpack_and_assert(packet + extra_data, "array", [42], extra_data)

    def test_unpack_fixed_positive_integer(self):
        packed_value = 42 << 8
        packet = struct.pack("I", packed_value)
        TestHelpers.unpack_and_assert(packet, "fixed", 42.0)

    def test_unpack_fixed_with_fraction(self):
        packed_value = (42 << 8) | 128
        packet = struct.pack("I", packed_value)
        TestHelpers.unpack_and_assert(packet, "fixed", 42.5)

    def test_unpack_fixed_negative(self):
        packed_value = ((-1) << 8) & 0xFFFFFFFF
        packet = struct.pack("I", packed_value)
        expected = (packed_value >> 8) + (packed_value & 0xFF) / 256.0
        TestHelpers.unpack_and_assert(packet, "fixed", expected)

    def test_unpack_fixed_small_fraction(self):
        packed_value = 64
        packet = struct.pack("I", packed_value)
        TestHelpers.unpack_and_assert(packet, "fixed", 0.25)

    def test_unpack_fixed_zero(self):
        packet = struct.pack("I", 0)
        TestHelpers.unpack_and_assert(packet, "fixed", 0.0)

    def test_unpack_fixed_with_extra_data(self):
        packed_value = (42 << 8) | 128
        extra_data = b"extra"
        packet = struct.pack("I", packed_value) + extra_data
        TestHelpers.unpack_and_assert(packet, "fixed", 42.5, extra_data)

    def test_unpack_unknown_type_raises_error(self):
        packet = b"test"
        with pytest.raises(ValueError, match="Unknown type unknown"):
            unpack_argument(packet, "unknown", None, None, None)


class TestPackUnpackRoundTrip:
    def test_roundtrip_uint(self):
        TestHelpers.roundtrip_test("uint", 42)

    def test_roundtrip_int_positive(self):
        TestHelpers.roundtrip_test("int", 42)

    def test_roundtrip_int_negative(self):
        TestHelpers.roundtrip_test("int", -42)

    def test_roundtrip_string_simple(self):
        TestHelpers.roundtrip_test("string", "hello")

    def test_roundtrip_string_unicode(self):
        TestHelpers.roundtrip_test("string", "café")

    def test_roundtrip_string_empty(self):
        TestHelpers.roundtrip_test("string", "")

    def test_roundtrip_fixed_integer(self):
        TestHelpers.roundtrip_test("fixed", 42.0)

    def test_roundtrip_fixed_with_fraction(self):
        TestHelpers.roundtrip_test("fixed", 42.5)


class TestEdgeCases:
    def test_pack_string_null_terminator_in_middle(self):
        TestHelpers.roundtrip_test("string", "hel\x00lo")

    def test_unpack_string_zero_length(self):
        packet = struct.pack("I", 0)
        TestHelpers.unpack_and_assert(packet, "string", "")

    def test_pack_fixed_precision_limits(self):
        original_value = 1.0 / 256.0
        packet, fds = pack_argument(b"", "fixed", original_value)
        remaining, unpacked_value = unpack_argument(packet, "fixed", None, None, None)
        assert abs(unpacked_value - original_value) < 1e-10

    def test_pack_fixed_large_integer_part(self):
        TestHelpers.roundtrip_test("fixed", 16777215.0)
