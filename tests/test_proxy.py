import json
import struct
import unittest
from enum import Enum, IntFlag
from unittest.mock import MagicMock, patch

import pytest

from wayland.proxy import Proxy
from wayland.state import WaylandState


class TestProxyRequest(unittest.TestCase):
    def setUp(self):
        self.mock_state = MagicMock(spec=WaylandState)
        self.mock_parent_proxy = MagicMock()
        self.mock_parent_proxy._name = "test_interface"
        self.mock_parent_proxy.object_id = 123
        self.mock_parent_proxy._scope = {}

    def test_pack_argument_uint(self):
        """
        Tests the _pack_argument method for a 'uint' type.
        """
        request_args_def = [
            {"name": "count", "type": "uint", "summary": "number of items"}
        ]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="test_request_uint",
            args=request_args_def,
            opcode=0,
            state=self.mock_state,
        )

        packet_accumulator = b""
        test_value = 42
        expected_packed_value = struct.pack("I", test_value)

        result_packet, returned_value = req._pack_argument(
            packet_accumulator, "uint", test_value
        )

        assert (
            result_packet == expected_packed_value
        ), "Packed uint does not match expected value."
        assert (
            returned_value == test_value
        ), "Returned value should be the same as input for uint."

    def test_request_call_with_uint_sends_message(self):
        """
        Tests that calling a Request object with a uint argument
        results in send_wayland_message being called correctly.
        """
        request_args_def = [{"name": "count", "type": "uint"}]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="test_request_uint",
            args=request_args_def,
            opcode=1,
            state=self.mock_state,
        )

        test_uint_value = 100
        req(test_uint_value)

        expected_packed_arg = struct.pack("I", test_uint_value)
        self.mock_state.send_wayland_message.assert_called_once_with(
            self.mock_parent_proxy.object_id, 1, expected_packed_arg, None
        )

    def test_pack_argument_string(self):
        """
        Tests the _pack_argument method for a 'string' type, including padding.
        """
        request_args_def = [{"name": "message", "type": "string"}]
        req = Proxy.Request(
            self.mock_parent_proxy,
            "test_request_string",
            request_args_def,
            2,
            self.mock_state,
        )

        packet_accumulator = b""
        test_value = "hello"

        expected_packed_value = (
            struct.pack("I", len(test_value) + 1) + b"hello\x00\x00\x00"
        )

        result_packet, returned_value = req._pack_argument(
            packet_accumulator, "string", test_value
        )

        assert (
            result_packet == expected_packed_value
        ), "Packed string does not match expected value."
        assert (
            returned_value == b"hello\x00\x00\x00"
        ), "Returned value for string should be the padded byte string."

    def test_request_call_with_string_sends_message(self):
        """
        Tests that calling a Request object with a string argument
        results in send_wayland_message being called correctly.
        """
        request_args_def = [{"name": "title", "type": "string"}]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="test_request_string_call",
            args=request_args_def,
            opcode=3,
            state=self.mock_state,
        )

        test_string_value = "Wayland Test"
        req(test_string_value)

        # Expected: length (uint) + string + null terminator + padding
        expected_data = b"Wayland Test\x00\x00\x00\x00"
        expected_packed_arg = (
            struct.pack("I", len(test_string_value) + 1) + expected_data
        )

        self.mock_state.send_wayland_message.assert_called_once_with(
            self.mock_parent_proxy.object_id, 3, expected_packed_arg, None
        )

    def test_pack_argument_int(self):
        """
        Tests the _pack_argument method for an 'int' type.
        """
        request_args_def = [{"name": "value", "type": "int"}]
        req = Proxy.Request(
            self.mock_parent_proxy,
            "test_request_int",
            request_args_def,
            4,
            self.mock_state,
        )

        packet_accumulator = b""
        test_value = -12345
        expected_packed_value = struct.pack("i", test_value)

        result_packet, returned_value = req._pack_argument(
            packet_accumulator, "int", test_value
        )

        assert (
            result_packet == expected_packed_value
        ), "Packed int does not match expected value."
        assert (
            returned_value == test_value
        ), "Returned value should be the same as input for int."

    def test_request_call_with_int_sends_message(self):
        """
        Tests that calling a Request object with a signed int argument
        results in send_wayland_message being called correctly.
        """
        request_args_def = [{"name": "offset", "type": "int"}]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="test_request_int_call",
            args=request_args_def,
            opcode=5,
            state=self.mock_state,
        )

        test_int_value = -6789
        req(test_int_value)

        expected_packed_arg = struct.pack("i", test_int_value)

        self.mock_state.send_wayland_message.assert_called_once_with(
            self.mock_parent_proxy.object_id, 5, expected_packed_arg, None
        )

    def test_pack_argument_fixed(self):
        """
        Tests the _pack_argument method for a 'fixed' type.
        Wayland fixed is a 24.8 fixed point number.
        """
        request_args_def = [{"name": "amount", "type": "fixed"}]
        req = Proxy.Request(
            self.mock_parent_proxy,
            "test_request_fixed",
            request_args_def,
            6,
            self.mock_state,
        )

        packet_accumulator = b""
        test_value_whole = 123.0
        expected_packed_whole = struct.pack("I", 31488)  # 123 << 8
        result_packet_whole, returned_value_whole = req._pack_argument(
            packet_accumulator, "fixed", test_value_whole
        )
        assert (
            result_packet_whole == expected_packed_whole
        ), "Packed fixed (whole) does not match."
        assert returned_value_whole == 31488

        test_value_frac = 123.75
        expected_packed_frac = struct.pack("I", 31680)  # (123 << 8) | int(0.75 * 256)
        result_packet_frac, returned_value_frac = req._pack_argument(
            packet_accumulator, "fixed", test_value_frac
        )
        assert (
            result_packet_frac == expected_packed_frac
        ), "Packed fixed (fractional) does not match."
        assert returned_value_frac == 31680

        test_value_frac2 = 0.5
        expected_packed_frac2 = struct.pack("I", 128)  # (0 << 8) | int(0.5 * 256)
        result_packet_frac2, returned_value_frac2 = req._pack_argument(
            packet_accumulator, "fixed", test_value_frac2
        )
        assert (
            result_packet_frac2 == expected_packed_frac2
        ), "Packed fixed (0.5) does not match."
        assert returned_value_frac2 == 128

    def test_request_call_with_fixed_sends_message(self):
        """
        Tests that calling a Request object with a fixed argument
        results in send_wayland_message being called correctly.
        """
        request_args_def = [{"name": "scale", "type": "fixed"}]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="test_request_fixed_call",
            args=request_args_def,
            opcode=7,
            state=self.mock_state,
        )

        test_fixed_value = 2.5
        req(test_fixed_value)

        expected_packed_arg = struct.pack(
            "I", 640
        )  # 2.5 fixed is (2 << 8) | int(0.5 * 256) = 512 | 128 = 640
        self.mock_state.send_wayland_message.assert_called_once_with(
            self.mock_parent_proxy.object_id, 7, expected_packed_arg, None
        )

    def test_pack_argument_object(self):
        """
        Tests the _pack_argument method for an 'object' type.
        """
        request_args_def = [{"name": "surface", "type": "object"}]
        req = Proxy.Request(
            self.mock_parent_proxy,
            "test_request_object",
            request_args_def,
            8,
            self.mock_state,
        )

        packet_accumulator = b""
        mock_surface_proxy = MagicMock()
        mock_surface_proxy.object_id = 456
        mock_surface_proxy._name = "wl_surface"

        expected_packed_value = struct.pack("I", mock_surface_proxy.object_id)
        result_packet, returned_value = req._pack_argument(
            packet_accumulator, "object", mock_surface_proxy
        )

        assert (
            result_packet == expected_packed_value
        ), "Packed object ID does not match."
        assert returned_value == mock_surface_proxy

    def test_request_call_with_object_sends_message(self):
        """
        Tests that calling a Request object with an object argument
        results in send_wayland_message being called correctly.
        """
        request_args_def = [{"name": "target_surface", "type": "object"}]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="test_request_object_call",
            args=request_args_def,
            opcode=9,
            state=self.mock_state,
        )

        mock_argument_proxy = MagicMock()
        mock_argument_proxy.object_id = 789
        mock_argument_proxy._name = "wl_buffer"

        req(mock_argument_proxy)

        expected_packed_arg = struct.pack("I", mock_argument_proxy.object_id)
        self.mock_state.send_wayland_message.assert_called_once_with(
            self.mock_parent_proxy.object_id, 9, expected_packed_arg, None
        )

    def test_pack_argument_new_id(self):
        """
        Tests the _pack_argument method for a 'new_id' type.
        It just packs the provided ID.
        """
        request_args_def = [
            {"name": "new_callback", "type": "new_id", "interface": "wl_callback"}
        ]
        req = Proxy.Request(
            self.mock_parent_proxy,
            "get_callback",
            request_args_def,
            10,
            self.mock_state,
        )

        packet_accumulator = b""
        new_object_id_to_pack = 999
        expected_packed_value = struct.pack("I", new_object_id_to_pack)

        result_packet, returned_value = req._pack_argument(
            packet_accumulator, "new_id", new_object_id_to_pack
        )

        assert result_packet == expected_packed_value, "Packed new_id does not match."
        assert returned_value == new_object_id_to_pack

    def test_request_call_with_new_id_creates_and_returns_object(self):
        """
        Tests that calling a Request with a new_id argument:
        1. Calls state.new_object to get a new ID and object.
        2. Packs this new ID into the message.
        3. Calls state.send_wayland_message.
        4. Returns the new object (via state.object_id_to_object_reference).
        """
        mock_wl_registry_class = MagicMock(name="wl_registry_class")
        self.mock_parent_proxy._scope = {"wl_registry": mock_wl_registry_class}

        request_args_def = [
            {"name": "registry", "type": "new_id", "interface": "wl_registry"}
        ]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="get_registry",
            args=request_args_def,
            opcode=11,
            state=self.mock_state,
        )

        new_id_from_state = 1001
        mock_new_registry_instance = MagicMock(name="new_wl_registry_instance")
        mock_new_registry_instance.object_id = new_id_from_state
        self.mock_state.new_object.return_value = (
            new_id_from_state,
            mock_new_registry_instance,
        )
        self.mock_state.object_id_to_object_reference.return_value = (
            mock_new_registry_instance
        )

        returned_object = req()

        self.mock_state.new_object.assert_called_once_with(mock_wl_registry_class)
        expected_packed_arg = struct.pack("I", new_id_from_state)
        self.mock_state.send_wayland_message.assert_called_once_with(
            self.mock_parent_proxy.object_id, 11, expected_packed_arg, None
        )
        self.mock_state.object_id_to_object_reference.assert_called_once_with(
            new_id_from_state
        )
        assert returned_object == mock_new_registry_instance

    def test_pack_argument_fd(self):
        """
        Tests the _pack_argument method for an 'fd' type.
        It does not pack into the main packet.
        """
        request_args_def = [{"name": "pipe_end", "type": "fd"}]
        req = Proxy.Request(
            self.mock_parent_proxy, "send_fd", request_args_def, 12, self.mock_state
        )

        packet_accumulator = b""
        test_fd_value = 5

        result_packet, returned_value = req._pack_argument(
            packet_accumulator, "fd", test_fd_value
        )

        assert (
            result_packet == b""
        ), "Packet should be unchanged by _pack_argument for 'fd'."
        assert returned_value == test_fd_value

    def test_request_call_with_fd_sends_ancillary_data(self):
        """
        Tests that calling a Request with an 'fd' argument
        results in send_wayland_message being called with correct ancillary data.
        """
        request_args_def = [{"name": "shared_mem_fd", "type": "fd"}]
        req = Proxy.Request(
            parent=self.mock_parent_proxy,
            name="share_memory",
            args=request_args_def,
            opcode=13,
            state=self.mock_state,
        )

        test_fd = 7
        import socket  # Required for socket constants

        req(test_fd)

        expected_ancillary_data = [
            (socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("I", test_fd))
        ]
        expected_packed_arg = b""
        self.mock_state.send_wayland_message.assert_called_once_with(
            self.mock_parent_proxy.object_id,
            13,
            expected_packed_arg,
            expected_ancillary_data,
        )


class TestProxyEvent(unittest.TestCase):
    def setUp(self):
        self.mock_parent_proxy = MagicMock(spec=Proxy.DynamicObject)
        self.mock_parent_proxy._name = "test_event_interface"
        self.mock_parent_proxy.object_id = 789

        self.event_args_def_uint = [{"name": "data", "type": "uint"}]
        self.event_opcode = 0
        self.event_name = "test_event_uint"

        self.proxy_event_uint = Proxy.Event(
            parent=self.mock_parent_proxy,
            name=self.event_name,
            args=self.event_args_def_uint,
            opcode=self.event_opcode,
        )

    def test_event_handler_add_and_remove(self):
        """Tests adding and removing event handlers."""
        mock_handler1 = MagicMock(name="handler1")
        mock_handler2 = MagicMock(name="handler2")

        self.proxy_event_uint += mock_handler1
        assert mock_handler1 in self.proxy_event_uint._handlers

        self.proxy_event_uint += mock_handler2
        assert mock_handler2 in self.proxy_event_uint._handlers
        assert len(self.proxy_event_uint._handlers) == 2

        self.proxy_event_uint -= mock_handler1
        assert mock_handler1 not in self.proxy_event_uint._handlers
        assert mock_handler2 in self.proxy_event_uint._handlers
        assert len(self.proxy_event_uint._handlers) == 1

        self.proxy_event_uint -= mock_handler1  # Test removing a non-existent handler
        assert len(self.proxy_event_uint._handlers) == 1

        self.proxy_event_uint -= mock_handler2  # Test removing the last handler
        assert len(self.proxy_event_uint._handlers) == 0

    def test_event_call_invokes_handlers_with_unpacked_uint(self):
        """Tests that calling an event unpacks a uint and invokes handlers."""
        mock_handler = MagicMock(name="event_handler_for_uint")
        self.proxy_event_uint += mock_handler

        test_uint_value = 987
        packet_data = struct.pack("I", test_uint_value)
        mock_get_fd = MagicMock()

        self.proxy_event_uint(packet_data, mock_get_fd)

        mock_handler.assert_called_once_with(data=test_uint_value)
        mock_get_fd.assert_not_called()

    def test_unpack_argument_uint_for_event(self):
        """Directly tests _unpack_argument for uint within Proxy.Event context."""
        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy, "unpack_event", [{"name": "val", "type": "uint"}], 0
        )
        test_uint_value = 12345
        packet = struct.pack("I", test_uint_value) + b"trailing_data"

        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet, "uint", get_fd=None, enum_type=None
        )

        assert unpacked_value == test_uint_value
        assert remaining_packet == b"trailing_data"

    def test_unpack_argument_string_for_event(self):
        """Directly tests _unpack_argument for string within Proxy.Event context."""
        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy,
            "unpack_event_str",
            [{"name": "msg", "type": "string"}],
            1,
        )

        test_string = "hello wayland"
        packed_len = struct.pack("I", len(test_string) + 1)
        packed_str_data = (test_string + "\x00").encode("utf-8")
        padding_len = ((len(packed_str_data) + 3) & ~3) - len(packed_str_data)
        padded_str_data = packed_str_data + (b"\x00" * padding_len)
        packet = packed_len + padded_str_data + b"extra_after_string"

        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet, "string", get_fd=None, enum_type=None
        )

        assert unpacked_value == test_string
        assert remaining_packet == b"extra_after_string"

    def test_event_call_invokes_handlers_with_unpacked_string(self):
        """Tests that calling an event unpacks a string and invokes handlers."""
        event_args_def_str = [{"name": "greeting", "type": "string"}]
        proxy_event_str = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_str",
            args=event_args_def_str,
            opcode=1,  # Different opcode
        )
        mock_handler = MagicMock(name="event_handler_for_string")
        proxy_event_str += mock_handler

        test_string_value = "Welcome!"
        packed_len = struct.pack("I", len(test_string_value) + 1)
        packed_str_data = (test_string_value + "\x00").encode("utf-8")
        padding_len = ((len(packed_str_data) + 3) & ~3) - len(packed_str_data)
        packet_data = packed_len + packed_str_data + (b"\x00" * padding_len)

        mock_get_fd = MagicMock()
        proxy_event_str(packet_data, mock_get_fd)

        mock_handler.assert_called_once_with(greeting=test_string_value)
        mock_get_fd.assert_not_called()

    def test_unpack_argument_int_for_event(self):
        """Directly tests _unpack_argument for int within Proxy.Event context."""
        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy,
            "unpack_event_int",
            [{"name": "val", "type": "int"}],
            2,
        )

        test_int_value = -34567
        packet = (
            struct.pack("i", test_int_value) + b"trailing_data_int"
        )  # 'i' for signed int

        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet, "int", get_fd=None, enum_type=None
        )

        assert unpacked_value == test_int_value
        assert remaining_packet == b"trailing_data_int"

    def test_event_call_invokes_handlers_with_unpacked_int(self):
        """Tests that calling an event unpacks an int and invokes handlers."""
        event_args_def_int = [{"name": "value", "type": "int"}]
        proxy_event_int = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_int",
            args=event_args_def_int,
            opcode=2,  # Different opcode
        )
        mock_handler = MagicMock(name="event_handler_for_int")
        proxy_event_int += mock_handler

        test_int_value = -765
        packet_data = struct.pack("i", test_int_value)

        mock_get_fd = MagicMock()
        proxy_event_int(packet_data, mock_get_fd)

        mock_handler.assert_called_once_with(value=test_int_value)
        mock_get_fd.assert_not_called()

    def test_unpack_argument_fixed_for_event(self):
        """Directly tests _unpack_argument for fixed type within Proxy.Event context."""
        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy,
            "unpack_event_fixed",
            [{"name": "amount", "type": "fixed"}],
            3,
        )

        packed_fixed_whole = struct.pack("I", 123 << 8)
        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packed_fixed_whole + b"trail1", "fixed", get_fd=None, enum_type=None
        )
        assert unpacked_value == 123.0
        assert remaining_packet == b"trail1"

        packed_fixed_frac = struct.pack("I", (123 << 8) | 192)
        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packed_fixed_frac + b"trail2", "fixed", get_fd=None, enum_type=None
        )
        assert unpacked_value == 123.75
        assert remaining_packet == b"trail2"

        packed_fixed_half = struct.pack("I", 128)
        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packed_fixed_half + b"trail3", "fixed", get_fd=None, enum_type=None
        )
        assert unpacked_value == 0.5
        assert remaining_packet == b"trail3"

    def test_event_call_invokes_handlers_with_unpacked_fixed(self):
        """Tests that calling an event unpacks a fixed-point number and invokes handlers."""
        event_args_def_fixed = [{"name": "scale_factor", "type": "fixed"}]
        proxy_event_fixed = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_fixed",
            args=event_args_def_fixed,
            opcode=3,  # Different opcode
        )
        mock_handler = MagicMock(name="event_handler_for_fixed")
        proxy_event_fixed += mock_handler

        packed_fixed_val = struct.pack("I", 640)

        mock_get_fd = MagicMock()
        proxy_event_fixed(packed_fixed_val, mock_get_fd)

        mock_handler.assert_called_once()
        assert "scale_factor" in mock_handler.call_args.kwargs
        assert mock_handler.call_args.kwargs["scale_factor"] == 2.5
        mock_get_fd.assert_not_called()

    def test_unpack_argument_object_for_event(self):
        """Directly tests _unpack_argument for object type (object ID) within Proxy.Event context."""
        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy,
            "unpack_event_object",
            [{"name": "source_obj", "type": "object"}],
            4,
        )

        test_object_id = 777
        packet = struct.pack("I", test_object_id) + b"trailing_obj_data"

        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet, "object", get_fd=None, enum_type=None
        )

        assert unpacked_value == test_object_id
        assert remaining_packet == b"trailing_obj_data"

    def test_event_call_invokes_handlers_with_unpacked_object_id(self):
        """Tests that calling an event unpacks an object ID and invokes handlers."""
        event_args_def_object = [{"name": "target", "type": "object"}]
        proxy_event_object = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_object",
            args=event_args_def_object,
            opcode=4,  # Different opcode
        )
        mock_handler = MagicMock(name="event_handler_for_object")
        proxy_event_object += mock_handler

        test_obj_id_val = 888
        packet_data = struct.pack("I", test_obj_id_val)

        mock_get_fd = MagicMock()
        proxy_event_object(packet_data, mock_get_fd)

        mock_handler.assert_called_once_with(target=test_obj_id_val)
        mock_get_fd.assert_not_called()

    def test_unpack_argument_fd_for_event(self):
        """Directly tests _unpack_argument for fd type within Proxy.Event context."""
        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy,
            "unpack_event_fd",
            [{"name": "received_fd", "type": "fd"}],
            5,
        )

        mock_get_fd_func = MagicMock(return_value=123)
        packet = b"any_remaining_packet_data"

        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet, "fd", get_fd=mock_get_fd_func, enum_type=None
        )

        mock_get_fd_func.assert_called_once()
        assert unpacked_value == 123
        assert remaining_packet == packet, "Packet should be unchanged for fd unpack"

    def test_event_call_invokes_handlers_with_unpacked_fd(self):
        """Tests that calling an event unpacks an fd and invokes handlers."""
        event_args_def_fd = [{"name": "mem_fd", "type": "fd"}]
        proxy_event_fd = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_fd",
            args=event_args_def_fd,
            opcode=5,  # Different opcode
        )
        mock_handler = MagicMock(name="event_handler_for_fd")
        proxy_event_fd += mock_handler

        test_fd_val = 456
        mock_get_fd_func = MagicMock(return_value=test_fd_val)
        packet_data = b""

        proxy_event_fd(packet_data, mock_get_fd_func)

        mock_get_fd_func.assert_called_once()
        mock_handler.assert_called_once_with(mem_fd=test_fd_val)

    def test_unpack_argument_array_for_event(self):
        """Directly tests _unpack_argument for array type within Proxy.Event context."""
        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy,
            "unpack_event_array",
            [{"name": "data_chunk", "type": "array"}],
            6,
        )

        test_array_data = b"\x01\x02\x03\x04\x05"
        packed_len = struct.pack("I", len(test_array_data))
        padding_len = ((len(test_array_data) + 3) & ~3) - len(test_array_data)
        padded_array_data = test_array_data + (b"\x00" * padding_len)

        packet = packed_len + padded_array_data + b"trailing_array_data"

        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet, "array", get_fd=None, enum_type=None
        )

        assert unpacked_value == (
            test_array_data[:-1] if len(test_array_data) > 0 else b""
        )
        assert remaining_packet == b"trailing_array_data"

    def test_event_call_invokes_handlers_with_unpacked_array(self):
        """Tests that calling an event unpacks an array and invokes handlers."""
        event_args_def_array = [{"name": "serial_data", "type": "array"}]
        proxy_event_array = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_array",
            args=event_args_def_array,
            opcode=6,  # Different opcode
        )
        mock_handler = MagicMock(name="event_handler_for_array")
        proxy_event_array += mock_handler

        test_byte_array = b"\xde\xad\xbe\xef"
        packed_len = struct.pack("I", len(test_byte_array))
        padding_len = ((len(test_byte_array) + 3) & ~3) - len(test_byte_array)
        packet_data = packed_len + test_byte_array + (b"\x00" * padding_len)

        mock_get_fd = MagicMock()
        proxy_event_array(packet_data, mock_get_fd)

        expected_unpacked_array = (
            test_byte_array[:-1] if len(test_byte_array) > 0 else b""
        )
        mock_handler.assert_called_once_with(serial_data=expected_unpacked_array)
        mock_get_fd.assert_not_called()

    def test_unpack_argument_enum_for_event(self):
        """Directly tests _unpack_argument for enum type within Proxy.Event context."""

        class TestEnum(Enum):
            OPTION_A = 0
            OPTION_B = 1
            OPTION_C = 256

        self.mock_parent_proxy.__dict__["MockColorEnum"] = TestEnum

        event_for_unpack_test = Proxy.Event(
            self.mock_parent_proxy,
            "unpack_event_enum",
            [{"name": "color", "type": "uint", "enum": "MockColorEnum"}],
            7,
        )

        packet_b = struct.pack("I", TestEnum.OPTION_B.value) + b"trailing_enum_b"
        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet_b, "uint", get_fd=None, enum_type="MockColorEnum"
        )
        assert unpacked_value == TestEnum.OPTION_B
        assert remaining_packet == b"trailing_enum_b"

        packet_c = struct.pack("I", TestEnum.OPTION_C.value) + b"trailing_enum_c"
        remaining_packet, unpacked_value = event_for_unpack_test._unpack_argument(
            packet_c, "uint", get_fd=None, enum_type="MockColorEnum"
        )
        assert unpacked_value == TestEnum.OPTION_C
        assert remaining_packet == b"trailing_enum_c"

        del self.mock_parent_proxy.__dict__["MockColorEnum"]

    def test_event_call_invokes_handlers_with_unpacked_enum(self):
        """Tests that calling an event unpacks an enum and invokes handlers."""

        class EventReasonEnum(Enum):
            REASON_ONE = 10
            REASON_TWO = 20

        self.mock_parent_proxy.__dict__["ReasonEnum"] = EventReasonEnum

        event_args_def_enum = [{"name": "reason", "type": "uint", "enum": "ReasonEnum"}]
        proxy_event_enum = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_enum",
            args=event_args_def_enum,
            opcode=7,  # Different opcode
        )
        mock_handler = MagicMock(name="event_handler_for_enum")
        proxy_event_enum += mock_handler

        test_enum_val = EventReasonEnum.REASON_TWO
        packet_data = struct.pack("I", test_enum_val.value)

        mock_get_fd = MagicMock()
        proxy_event_enum(packet_data, mock_get_fd)

        mock_handler.assert_called_once_with(reason=test_enum_val)
        mock_get_fd.assert_not_called()

        del self.mock_parent_proxy.__dict__["ReasonEnum"]

    def test_event_call_new_id_with_interface_raises_not_implemented(self):
        """
        Tests that calling an event with a 'new_id' type arg that also has an 'interface'
        raises NotImplementedError as per current proxy.py implementation.
        """
        event_args_def_new_id_interface = [
            {"name": "new_object", "type": "new_id", "interface": "wl_compositor"}
        ]
        proxy_event_ni = Proxy.Event(
            parent=self.mock_parent_proxy,
            name="test_event_new_id_interface",
            args=event_args_def_new_id_interface,
            opcode=8,
        )
        mock_handler = MagicMock(name="handler_for_new_id_event")
        proxy_event_ni += mock_handler

        # Packet for a new_id (uint)
        packet_data = struct.pack("I", 12345)  # Dummy object ID
        mock_get_fd = MagicMock()

        with pytest.raises(
            NotImplementedError, match="No events like this to test yet"
        ):
            proxy_event_ni(packet_data, mock_get_fd)

        mock_handler.assert_not_called()

    def test_int_to_enum_fallback_for_event(self):
        """
        Tests Proxy.Event._int_to_enum when the specified enum_type is not found
        on the parent proxy, expecting it to return the original integer value.
        """
        event_for_enum_fallback = Proxy.Event(
            self.mock_parent_proxy,
            "enum_fallback_event",
            [{"name": "status", "type": "uint", "enum": "NonExistentEnum"}],
            9,
        )

        if "NonExistentEnum" in self.mock_parent_proxy.__dict__:
            del self.mock_parent_proxy.__dict__["NonExistentEnum"]

        test_integer_value = 42

        packet = struct.pack("I", test_integer_value)
        _, unpacked_value = event_for_enum_fallback._unpack_argument(
            packet, "uint", get_fd=None, enum_type="NonExistentEnum"
        )

        assert (
            unpacked_value == test_integer_value
        ), "Should return original int when enum_type is not found."


class TestProxyDynamicObject(unittest.TestCase):
    def setUp(self):
        self.mock_state = MagicMock(spec=WaylandState)
        self.mock_scope = {}

        self.requests_def = [
            {"name": "get_foo", "args": [], "opcode": 0},
            {"name": "do_bar", "args": [{"name": "val", "type": "uint"}], "opcode": 1},
            {"name": "import", "args": [], "opcode": 2},
        ]
        self.events_def = [
            {"name": "on_baz", "args": [], "opcode": 0},
            {"name": "global", "args": [{"name": "id", "type": "uint"}], "opcode": 1},
        ]
        self.enums_def = [
            {
                "name": "capability",
                "args": [
                    {"name": "CAP_READ", "value": "1"},
                    {"name": "CAP_WRITE", "value": "2"},
                ],
                "bitfield": "true",
            },
            {
                "name": "error_code",
                "args": [
                    {"name": "BAD_THING", "value": "100"},
                    {"name": "WORSE_THING", "value": "101"},
                ],
            },
        ]

    def test_dynamic_object_initialization_and_binding(self):
        """
        Tests that requests, events, and enums are correctly bound
        during DynamicObject initialization.
        """
        obj_name = "test_dynamic_interface"
        dynamic_obj = Proxy.DynamicObject(
            name=obj_name,
            scope=self.mock_scope,
            requests=self.requests_def,
            events=self.events_def,
            enums=self.enums_def,
            state=self.mock_state,
        )

        assert dynamic_obj._name == obj_name
        assert dynamic_obj._state == self.mock_state
        assert dynamic_obj._object_id == 0

        assert hasattr(dynamic_obj, "get_foo")
        assert isinstance(dynamic_obj.get_foo, Proxy.Request)
        assert dynamic_obj.get_foo.name == "get_foo"
        assert dynamic_obj.get_foo.opcode == 0

        assert hasattr(dynamic_obj, "do_bar")
        assert isinstance(dynamic_obj.do_bar, Proxy.Request)

        assert hasattr(dynamic_obj, "import_")
        assert isinstance(dynamic_obj.import_, Proxy.Request)
        assert dynamic_obj.import_.name == "import_"

        assert hasattr(dynamic_obj.events, "on_baz")
        assert isinstance(dynamic_obj.events.on_baz, Proxy.Event)
        assert dynamic_obj.events.on_baz.name == "on_baz"
        assert dynamic_obj.events.on_baz.opcode == 0

        assert hasattr(dynamic_obj.events, "global_")
        assert isinstance(dynamic_obj.events.global_, Proxy.Event)
        assert dynamic_obj.events.global_.name == "global_"

        assert hasattr(dynamic_obj, "capability")
        assert issubclass(dynamic_obj.capability, IntFlag)
        assert dynamic_obj.capability.CAP_READ.value == 1
        assert dynamic_obj.capability.CAP_WRITE.value == 2

        assert hasattr(dynamic_obj, "error_code")
        assert issubclass(dynamic_obj.error_code, Enum)
        assert not issubclass(dynamic_obj.error_code, IntFlag)
        assert dynamic_obj.error_code.BAD_THING.value == 100
        assert dynamic_obj.error_code.WORSE_THING.value == 101

    def test_dynamic_object_wl_display_special_case(self):
        """
        Tests that if the DynamicObject is 'wl_display', its object_id is
        initialized by calling state.new_object.
        """
        mock_wl_display_instance = MagicMock(name="wl_display_instance_from_state")
        self.mock_state.new_object.return_value = (1, mock_wl_display_instance)

        dynamic_display_obj = Proxy.DynamicObject(
            name="wl_display",
            scope=self.mock_scope,
            requests=[],
            events=[],
            enums=[],
            state=self.mock_state,
        )
        self.mock_state.new_object.assert_called_once_with(dynamic_display_obj)
        assert dynamic_display_obj.object_id == 1

    def test_dynamic_object_copy(self):
        """Tests the copy() method of DynamicObject."""
        obj_name = "copy_test_interface"
        original_obj = Proxy.DynamicObject(
            name=obj_name,
            scope=self.mock_scope,
            requests=self.requests_def,
            events=self.events_def,
            enums=self.enums_def,
            state=self.mock_state,
        )
        original_obj.object_id = 555

        copied_obj = original_obj.copy()

        assert copied_obj is not original_obj, "Copied object should be a new instance."
        assert copied_obj._name == original_obj._name
        assert copied_obj._scope == original_obj._scope
        assert copied_obj._state == original_obj._state

        assert copied_obj.object_id == 0, "Copied object should have object_id 0."

        assert hasattr(copied_obj, "get_foo")
        assert isinstance(copied_obj.get_foo, Proxy.Request)
        assert hasattr(copied_obj.events, "on_baz")
        assert isinstance(copied_obj.events.on_baz, Proxy.Event)
        assert hasattr(copied_obj, "capability")
        assert issubclass(copied_obj.capability, IntFlag)

    def test_dynamic_object_bool_evaluation(self):
        """Tests the __bool__ method of DynamicObject."""
        obj_name = "bool_test_interface"
        dynamic_obj = Proxy.DynamicObject(
            name=obj_name,
            scope=self.mock_scope,
            requests=[],
            events=[],
            enums=[],
            state=self.mock_state,
        )

        assert not bool(dynamic_obj), "Object with ID 0 should be False."

        dynamic_obj.object_id = 123
        assert bool(dynamic_obj), "Object with non-zero ID should be True."

        dynamic_obj.object_id = -5
        assert not bool(
            dynamic_obj
        ), "Object with negative ID should be False (as it's not > 0)."


class TestProxyMainClass(unittest.TestCase):
    def setUp(self):
        self.mock_state_for_proxy = MagicMock(spec=WaylandState)
        self.patcher = patch(
            "wayland.proxy.WaylandState", return_value=self.mock_state_for_proxy
        )
        self.MockWaylandStateClass = self.patcher.start()

        self.mock_display_instance_from_state = MagicMock(
            name="mock_display_from_state"
        )
        self.mock_state_for_proxy.new_object.return_value = (
            1,
            self.mock_display_instance_from_state,
        )

        self.addCleanup(self.patcher.stop)

        self.proxy_main = Proxy()

        self.sample_protocol_json_content = {
            "wl_display": {
                "requests": [
                    {
                        "name": "sync",
                        "args": [
                            {
                                "name": "callback",
                                "type": "new_id",
                                "interface": "wl_callback",
                            }
                        ],
                        "opcode": 0,
                    }
                ],
                "events": [
                    {
                        "name": "error",
                        "args": [
                            {"name": "object_id", "type": "object"},
                            {"name": "code", "type": "uint"},
                            {"name": "message", "type": "string"},
                        ],
                        "opcode": 0,
                    }
                ],
                "enums": [],
            },
            "wl_callback": {
                "requests": [],
                "events": [
                    {
                        "name": "done",
                        "args": [{"name": "callback_data", "type": "uint"}],
                        "opcode": 0,
                    }
                ],
                "enums": [],
            },
        }

    @patch("builtins.open")
    @patch("json.load")
    def test_proxy_initialise_dict_scope(self, mock_json_load, mock_open):
        """
        Tests Proxy.initialise with a dictionary scope.
        """
        mock_json_load.return_value = self.sample_protocol_json_content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        test_scope = {}
        protocol_file_path = "/fake/path"

        self.proxy_main.initialise(test_scope, protocol_file_path)

        mock_open.assert_called_once_with(
            f"{protocol_file_path}/protocols.json", encoding="utf-8"
        )
        mock_json_load.assert_called_once_with(mock_file)

        assert "wl_display" in test_scope
        assert isinstance(test_scope["wl_display"], Proxy.DynamicObject)
        assert test_scope["wl_display"]._name == "wl_display"
        self.mock_state_for_proxy.new_object.assert_any_call(test_scope["wl_display"])

        assert "wl_callback" in test_scope
        assert isinstance(test_scope["wl_callback"], Proxy.DynamicObject)
        assert test_scope["wl_callback"]._name == "wl_callback"

        assert "process_messages" in test_scope
        assert (
            test_scope["process_messages"] == self.mock_state_for_proxy.process_messages
        )

        found_wl_display_call = False
        for call_args in self.mock_state_for_proxy.new_object.call_args_list:
            if call_args[0][0] == test_scope["wl_display"]:
                found_wl_display_call = True
                break
        assert (
            found_wl_display_call
        ), "state.new_object was not called with the wl_display instance"

    @patch("builtins.open")
    @patch("json.load")
    def test_proxy_initialise_object_scope(self, mock_json_load, mock_open):
        """
        Tests Proxy.initialise with an object (module-like) scope.
        """
        mock_json_load.return_value = self.sample_protocol_json_content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        class MockScopeModule:
            pass

        test_scope_obj = MockScopeModule()
        protocol_file_path = "/another/fake/path"

        self.proxy_main.initialise(test_scope_obj, protocol_file_path)

        assert hasattr(test_scope_obj, "wl_display")
        assert isinstance(test_scope_obj.wl_display, Proxy.DynamicObject)
        assert test_scope_obj.wl_display._name == "wl_display"

        assert hasattr(test_scope_obj, "process_messages")
        assert (
            test_scope_obj.process_messages
            == self.mock_state_for_proxy.process_messages
        )

    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    def test_proxy_initialise_file_not_found(self, mock_open):
        """Tests FileNotFoundError during initialise."""
        with pytest.raises(
            FileNotFoundError, match="Error loading structure: File not found"
        ):
            self.proxy_main.initialise({}, "/nonexistent/path")

    @patch("builtins.open")
    @patch("json.load", side_effect=json.JSONDecodeError("Decode error", "doc", 0))
    def test_proxy_initialise_json_decode_error(self, mock_json_load, mock_open):
        """Tests JSONDecodeError during initialise."""
        mock_open.return_value.__enter__.return_value = MagicMock()
        with pytest.raises(
            FileNotFoundError, match="Error loading structure: Decode error"
        ):
            self.proxy_main.initialise({}, "/some/path")

    def test_proxy_getitem(self):
        """Tests the __getitem__ method of the main Proxy class."""
        self.proxy_main.some_attribute = "test_value"
        assert self.proxy_main["some_attribute"] == "test_value"

        mock_callable = MagicMock(return_value="called_value")
        self.proxy_main.some_callable_attr = mock_callable

        result = self.proxy_main["some_callable_attr"]

        mock_callable.assert_called_once()
        assert result == "called_value"

        with pytest.raises(KeyError, match="'non_existent_key' not found"):
            _ = self.proxy_main["non_existent_key"]


if __name__ == "__main__":
    unittest.main()
