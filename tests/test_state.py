import struct
import unittest
from unittest.mock import MagicMock, call, patch

import pytest

from wayland.state import WaylandState
from wayland.unixsocket import UnixSocketConnection


class TestWaylandStateGetSocketPath(unittest.TestCase):
    """Tests for the static _get_socket_path method of WaylandState."""

    @patch("os.getenv")
    def test_get_socket_path_success(self, mock_os_getenv):
        """Tests _get_socket_path with environment variables set."""
        mock_os_getenv.side_effect = lambda key, default=None: {
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "WAYLAND_DISPLAY": "wayland-1",
        }.get(key, default)

        path = WaylandState._get_socket_path()
        assert path == "/run/user/1000/wayland-1"
        mock_os_getenv.assert_any_call("XDG_RUNTIME_DIR")
        mock_os_getenv.assert_any_call("WAYLAND_DISPLAY", "wayland-0")

    @patch("os.getenv")
    def test_get_socket_path_default_display(self, mock_os_getenv):
        """Tests _get_socket_path with default WAYLAND_DISPLAY."""
        mock_os_getenv.side_effect = lambda key, default=None: {
            "XDG_RUNTIME_DIR": "/tmp/runtime"
        }.get(key, default)

        path = WaylandState._get_socket_path()
        assert path == "/tmp/runtime/wayland-0"
        mock_os_getenv.assert_any_call("XDG_RUNTIME_DIR")
        mock_os_getenv.assert_any_call("WAYLAND_DISPLAY", "wayland-0")

    @patch("os.getenv")
    def test_get_socket_path_no_xdg_runtime_dir(self, mock_os_getenv):
        """Tests _get_socket_path when XDG_RUNTIME_DIR is not set."""

        def side_effect_no_xdg(key, default=None):
            if key == "XDG_RUNTIME_DIR":
                return None
            if key == "WAYLAND_DISPLAY":
                return "wayland-0"
            return default

        mock_os_getenv.side_effect = side_effect_no_xdg

        with pytest.raises(
            ValueError, match="XDG_RUNTIME_DIR environment variable not set."
        ):
            WaylandState._get_socket_path()

        calls = [call("XDG_RUNTIME_DIR"), call("WAYLAND_DISPLAY", "wayland-0")]
        mock_os_getenv.assert_has_calls(calls, any_order=False)


class TestWaylandState(unittest.TestCase):
    @patch("wayland.state.UnixSocketConnection")
    @patch("wayland.state.WaylandState._get_socket_path")
    def test_wayland_state_init(
        self, mock_get_path_for_init, mock_unix_socket_conn_class
    ):
        """Tests WaylandState.__init__."""
        expected_socket_path = "/test/path/wayland-99"
        mock_get_path_for_init.return_value = expected_socket_path

        mock_socket_instance = MagicMock()
        mock_unix_socket_conn_class.return_value = mock_socket_instance

        state = WaylandState(disable_event_dispatch_thread=True)

        mock_get_path_for_init.assert_called_once()
        mock_unix_socket_conn_class.assert_called_once_with(expected_socket_path)
        assert state._socket == mock_socket_instance
        assert state._next_object_id == 1
        assert state._object_id_to_instance == {}
        assert state._instance_to_object_id == {}

    def setUp(self):
        self.socket_patcher = patch("wayland.state.UnixSocketConnection", autospec=True)
        self.MockUnixSocketConnection = self.socket_patcher.start()
        self.mock_socket_instance = MagicMock(spec=UnixSocketConnection)
        self.MockUnixSocketConnection.return_value = self.mock_socket_instance

        self.instance_path_patcher = patch(
            "wayland.state.WaylandState._get_socket_path",
            return_value="/mock/instance/path",
        )
        self.mock_instance_get_path = self.instance_path_patcher.start()

        self.state = WaylandState(disable_event_dispatch_thread=True)
        self.addCleanup(self.socket_patcher.stop)
        self.addCleanup(self.instance_path_patcher.stop)

    def _create_mock_object_ref(self, object_id=0):
        """Helper to create a mock object reference."""
        ref = MagicMock()
        ref.object_id = object_id
        ref.copy = MagicMock(
            side_effect=lambda: self._create_mock_object_ref(object_id=ref.object_id)
        )
        return ref

    def test_new_object_basic_allocation(self):
        """Tests basic object ID allocation and storage via new_object."""
        mock_ref1 = self._create_mock_object_ref()

        obj_id1, returned_ref1 = self.state.new_object(mock_ref1)

        assert obj_id1 == 1
        assert returned_ref1 is mock_ref1
        assert mock_ref1.object_id == 1
        assert self.state._object_id_to_instance[1] is mock_ref1
        assert self.state._instance_to_object_id[mock_ref1] == 1
        assert self.state._next_object_id == 2

        mock_ref2 = self._create_mock_object_ref()
        obj_id2, _ = self.state.new_object(mock_ref2)
        assert obj_id2 == 2
        assert self.state._next_object_id == 3

    def test_new_object_with_existing_id_copies(self):
        """Tests that new_object calls copy() if the passed reference already has an ID."""
        mock_ref_orig = self._create_mock_object_ref(object_id=555)

        obj_id, returned_ref = self.state.new_object(mock_ref_orig)

        mock_ref_orig.copy.assert_called_once()
        assert returned_ref is not mock_ref_orig
        assert obj_id == 1
        assert returned_ref.object_id == 1
        assert self.state._object_id_to_instance[1] is returned_ref

    def test_add_object_reference_duplicate_id_raises_error(self):
        """
        Tests that add_object_reference raises ValueError for a duplicate ID
        if the exact object_id and object_reference pair already exists.
        """
        mock_ref1 = self._create_mock_object_ref()
        self.state.add_object_reference(10, mock_ref1)

        with pytest.raises(ValueError, match="Duplicate object id"):
            self.state.add_object_reference(10, mock_ref1)

    def test_add_object_reference_conflicting_id_raises_error(self):
        """
        Tests that add_object_reference (via object_exists) raises ValueError
        if ID exists but with a different reference.
        """
        mock_ref1 = self._create_mock_object_ref()
        self.state.add_object_reference(11, mock_ref1)

        mock_ref2 = self._create_mock_object_ref()
        with pytest.raises(
            ValueError, match="Object ID does not match expected object reference"
        ):
            self.state.add_object_reference(11, mock_ref2)

    def test_object_exists(self):
        """Tests the object_exists method."""
        mock_ref = self._create_mock_object_ref()
        self.state.add_object_reference(20, mock_ref)

        assert self.state.object_exists(20, mock_ref)
        assert not self.state.object_exists(21, mock_ref)

        with pytest.raises(
            ValueError, match="Object ID does not match expected object reference"
        ):
            self.state.object_exists(20, self._create_mock_object_ref())

        assert not self.state.object_exists(22, self._create_mock_object_ref())

    def test_object_exists_value_errors_directly(self):
        """More direct tests for ValueError conditions in object_exists."""
        mock_ref_a = self._create_mock_object_ref()
        mock_ref_b = self._create_mock_object_ref()

        self.state.add_object_reference(25, mock_ref_a)
        with pytest.raises(
            ValueError, match="Object ID does not match expected object reference"
        ):
            self.state.object_exists(25, mock_ref_b)
        self.state.delete_object_reference(25, mock_ref_a)

        id_for_test = 30
        ref_for_test = self._create_mock_object_ref()

        # Create an inconsistent state directly for testing this specific branch
        self.state._object_id_to_instance[id_for_test] = ref_for_test
        self.state._instance_to_object_id[ref_for_test] = id_for_test + 1

        with pytest.raises(
            ValueError, match="Object reference does not match expected object id"
        ):
            self.state.object_exists(id_for_test, ref_for_test)

        if id_for_test in self.state._object_id_to_instance:
            del self.state._object_id_to_instance[id_for_test]
        if ref_for_test in self.state._instance_to_object_id:
            del self.state._instance_to_object_id[ref_for_test]

    def test_delete_object_reference(self):
        """Tests deleting object references."""
        mock_ref = self._create_mock_object_ref()
        self.state.add_object_reference(30, mock_ref)
        assert self.state.object_exists(30, mock_ref)

        self.state.delete_object_reference(30, mock_ref)
        assert not self.state.object_exists(30, mock_ref)
        assert 30 not in self.state._object_id_to_instance
        assert mock_ref not in self.state._instance_to_object_id

        # Test deleting non-existent (should not error)
        self.state.delete_object_reference(31, self._create_mock_object_ref())

    def test_object_id_to_object_reference(self):
        """Tests retrieving object reference by ID."""
        mock_ref = self._create_mock_object_ref()
        self.state.add_object_reference(40, mock_ref)

        assert self.state.object_id_to_object_reference(40) is mock_ref
        assert self.state.object_id_to_object_reference(41) is None

    def test_object_reference_to_object_id(self):
        """Tests retrieving object ID by reference."""
        mock_ref = self._create_mock_object_ref()
        self.state.add_object_reference(50, mock_ref)

        assert self.state.object_reference_to_object_id(mock_ref) == 50
        assert (
            self.state.object_reference_to_object_id(self._create_mock_object_ref())
            == 0
        )  # Test non-existent ref

    def test_object_id_to_event(self):
        """Tests retrieving an event callable by object ID and event opcode."""
        mock_proxy = self._create_mock_object_ref()

        mock_event_callable = MagicMock(spec=True)
        mock_event_callable.opcode = 0
        mock_event_callable.event = True
        mock_event_callable.name = "mock_event_name"

        mock_another_event = MagicMock(spec=True)
        mock_another_event.opcode = 1
        mock_another_event.event = True

        mock_non_event_callable = MagicMock(spec=True)
        mock_non_event_callable.opcode = 3
        mock_non_event_callable.event = False

        mock_proxy.events = MagicMock()
        mock_proxy.events.actual_event_op0 = mock_event_callable
        mock_proxy.events.actual_event_op1 = mock_another_event
        mock_proxy.events.not_an_event_op3 = mock_non_event_callable
        mock_proxy.events._internal_thing = MagicMock()

        obj_id, _ = self.state.new_object(mock_proxy)

        found_event_op0 = self.state.object_id_to_event(obj_id, 0)
        assert found_event_op0 is mock_event_callable

        found_event_op1 = self.state.object_id_to_event(obj_id, 1)
        assert found_event_op1 is mock_another_event

        assert self.state.object_id_to_event(obj_id, 2) is None
        assert self.state.object_id_to_event(obj_id, 3) is None

        assert self.state.object_id_to_event(obj_id + 100, 0) is None

        mock_proxy_no_events = self._create_mock_object_ref()
        obj_id_no_events, _ = self.state.new_object(mock_proxy_no_events)
        assert self.state.object_id_to_event(obj_id_no_events, 0) is None

        mock_proxy_no_matching_op = self._create_mock_object_ref()
        mock_proxy_no_matching_op.events = MagicMock()
        mock_proxy_no_matching_op.events.some_other_event = MagicMock(
            opcode=99, event=True
        )
        obj_id_no_match, _ = self.state.new_object(mock_proxy_no_matching_op)
        assert self.state.object_id_to_event(obj_id_no_match, 0) is None

    @patch("wayland.state.log")
    def test_send_wayland_message(self, mock_log_object):
        """Tests send_wayland_message and implicitly _send and _debug_packet."""
        obj_id = 123
        request_opcode = 2

        test_packet_data = b"\x01\x02\x03\x04"
        expected_total_size = len(test_packet_data) + 8
        expected_header = struct.pack(
            "IHH", obj_id, request_opcode, expected_total_size
        )
        expected_full_message = expected_header + test_packet_data

        self.state.send_wayland_message(obj_id, request_opcode, test_packet_data, None)

        self.mock_socket_instance.sendall.assert_called_once_with(expected_full_message)
        self.mock_socket_instance.sendmsg.assert_not_called()
        mock_log_object.protocol.assert_called()

        self.mock_socket_instance.reset_mock()
        mock_log_object.reset_mock()

        ancillary_data = [("ancillary_info",)]
        self.state.send_wayland_message(
            obj_id, request_opcode, test_packet_data, ancillary_data
        )

        self.mock_socket_instance.sendmsg.assert_called_once()
        assert self.mock_socket_instance.sendmsg.call_args[0][0] == [
            expected_full_message
        ]
        assert self.mock_socket_instance.sendmsg.call_args[0][1] == ancillary_data
        self.mock_socket_instance.sendall.assert_not_called()
        mock_log_object.protocol.assert_called()

        with pytest.raises(ValueError, match="NULL object passed as Wayland object"):
            self.state.send_wayland_message(0, request_opcode, test_packet_data, None)

    @patch("wayland.state.log")
    def test_get_next_message(self, mock_log_object_gnm):
        """Tests get_next_message for processing incoming events."""
        self.mock_socket_instance.get_next_message.return_value = None
        assert not self.state.get_next_message()
        self.mock_socket_instance.get_next_message.assert_called()

        self.mock_socket_instance.reset_mock()

        object_id = 10
        event_opcode = 1
        event_data_payload = b"\x01\x02\x03\x04"
        header = struct.pack(
            "IHH", object_id, event_opcode, len(event_data_payload) + 8
        )
        full_packet_from_socket = header + event_data_payload

        self.mock_socket_instance.get_next_message.return_value = (
            full_packet_from_socket
        )

        mock_event_handler = MagicMock(name="mock_event_handler_for_gnm")
        with patch.object(
            self.state, "object_id_to_event", return_value=mock_event_handler
        ) as mock_oid_to_event:
            assert self.state.get_next_message()
            mock_oid_to_event.assert_called_once_with(object_id, event_opcode)
            mock_event_handler.assert_called_once_with(
                event_data_payload, self.mock_socket_instance.get_next_fd
            )

        self.mock_socket_instance.reset_mock()
        mock_log_object_gnm.reset_mock()

        self.mock_socket_instance.get_next_message.return_value = (
            full_packet_from_socket
        )
        with patch.object(
            self.state, "object_id_to_event", return_value=None
        ) as mock_oid_to_event_none:
            assert self.state.get_next_message()
            mock_oid_to_event_none.assert_called_once_with(object_id, event_opcode)
            mock_log_object_gnm.event.assert_called_once_with(
                f"Unhandled event {object_id}#{event_opcode}"
            )


if __name__ == "__main__":
    unittest.main()
