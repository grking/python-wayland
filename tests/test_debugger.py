import threading
import time
import unittest
from collections import deque
from unittest.mock import MagicMock, patch

import pytest

from wayland.debugger import Debugger, Message, MessageType


class TestMessageType(unittest.TestCase):
    """Tests for the MessageType enum."""

    def test_message_type_values(self):
        """Tests that MessageType enum has expected values."""
        assert MessageType.REQUEST is not None
        assert MessageType.EVENT is not None
        assert MessageType.REQUEST != MessageType.EVENT


class TestMessage(unittest.TestCase):
    """Tests for the Message dataclass."""

    def test_message_creation(self):
        """Tests basic Message creation."""
        timestamp = 1234567890.0
        msgtype = MessageType.REQUEST
        signature = "test_signature"
        interface = "wl_test"
        method_name = "test_method"
        object_id = 1
        args = {"arg1": "val1"}
        opcode = 0
        packet = b"packet_data"

        msg = Message(
            timestamp,
            msgtype,
            signature,
            interface,
            method_name,
            object_id,
            args,
            opcode,
            packet,
            1,
        )

        assert msg.timestamp == timestamp
        assert msg.msgtype == msgtype
        assert msg.signature == signature
        assert msg.interface == interface
        assert msg.method_name == method_name
        assert msg.object_id == object_id
        assert msg.args == args
        assert msg.opcode == opcode
        assert msg.packet == packet

    def test_message_immutable(self):
        """Tests that Message is frozen/immutable."""
        msg = Message(
            time.time(),
            MessageType.EVENT,
            "test_sig",
            "wl_interface",
            "method",
            100,
            {},
            1,
            b"data",
            1,
        )

        with pytest.raises(AttributeError):
            msg.timestamp = 999.0

        with pytest.raises(AttributeError):
            msg.msgtype = MessageType.REQUEST

        with pytest.raises(AttributeError):
            msg.signature = "new_signature"

    @patch("time.time")
    def test_message_create_request(self, mock_time):
        """Tests Message.create with REQUEST type."""
        mock_time.return_value = 1234567890.123
        signature = "wl_display@bind"
        interface = "wl_display"
        method_name = "bind"
        object_id = 1
        args = {"id": 2}
        opcode = 0
        packet = b"bind_packet"

        msg = Message.create(
            None,  # timestamp - will use current time
            MessageType.REQUEST,
            signature,
            interface,
            method_name,
            object_id,
            args,
            opcode,
            packet,
            1,
        )

        assert msg.timestamp == 1234567890.123
        assert msg.msgtype == MessageType.REQUEST
        assert msg.signature == signature
        assert msg.interface == interface
        assert msg.method_name == method_name
        assert msg.object_id == object_id
        assert msg.args == args
        assert msg.opcode == opcode
        assert msg.packet == packet
        mock_time.assert_called_once()

    @patch("time.time")
    def test_message_create_event(self, mock_time):
        """Tests Message.create with EVENT type."""
        mock_time.return_value = 9876543210.456
        signature = "wl_registry@global"
        interface = "wl_registry"
        method_name = "global"
        object_id = 2
        args = {"name": 3, "interface": "wl_compositor", "version": 4}
        opcode = 0
        packet = b"global_event_packet"

        msg = Message.create(
            None,  # timestamp - will use current time
            MessageType.EVENT,
            signature,
            interface,
            method_name,
            object_id,
            args,
            opcode,
            packet,
            1,
        )

        assert msg.timestamp == 9876543210.456
        assert msg.msgtype == MessageType.EVENT
        assert msg.signature == signature
        assert msg.interface == interface
        assert msg.method_name == method_name
        assert msg.object_id == object_id
        assert msg.args == args
        assert msg.opcode == opcode
        assert msg.packet == packet
        mock_time.assert_called_once()


class TestDebugger(unittest.TestCase):
    """Tests for the Debugger class."""

    def test_debug_init_default(self):
        """Tests Debugger initialization with default max_log_size."""
        current_debugger_instance = Debugger()
        current_debugger_instance.set_max_size(10000)
        assert isinstance(current_debugger_instance._msg_lock, type(threading.Lock()))
        assert isinstance(current_debugger_instance._msgdata, deque)
        assert current_debugger_instance._msgdata.maxlen == 10000

    def test_debug_init_custom_max_size(self):
        """Tests Debugger initialization with custom max_log_size."""
        debug = Debugger()  # Instantiates with default
        debug.set_max_size(5000)  # Then set custom size

        assert isinstance(debug._msg_lock, type(threading.Lock()))
        assert isinstance(debug._msgdata, deque)
        assert debug._msgdata.maxlen == 5000

    def test_debug_init_zero_max_size(self):
        """Tests Debugger initialization with zero max_log_size."""
        debug = Debugger()
        debug.set_max_size(0)

        assert debug._msgdata.maxlen == 0

    def test_set_max_size(self):
        """Tests set_max_size method."""
        debug = Debugger()
        debug.clear()  # Ensure clean state for this test
        debug.set_max_size(100)  # Initial size for this test context

        # Add some initial data (using mock messages for simplicity)
        # The _msgdata deque stores Message objects.
        initial_messages = []
        for i in range(5):
            msg = Message(
                time.time(),
                MessageType.EVENT,
                f"sig{i+1}",
                f"iface{i+1}",
                f"meth{i+1}",
                i + 1,
                {},
                0,
                b"",
                i + 1,
            )
            initial_messages.append(msg)
            debug._msgdata.append(msg)

        # Change max size to smaller value
        debug.set_max_size(3)

        assert debug._msgdata.maxlen == 3
        # Should keep the rightmost elements when shrinking
        assert len(debug._msgdata) == 3
        # Compare with the actual Message objects expected
        assert list(debug._msgdata) == initial_messages[2:]

    def test_set_max_size_larger(self):
        """Tests set_max_size with larger value."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(2)
        msg1 = Message(
            time.time(), MessageType.EVENT, "sig1", "iface1", "meth1", 1, {}, 0, b"", 1
        )
        msg2 = Message(
            time.time(),
            MessageType.REQUEST,
            "sig2",
            "iface2",
            "meth2",
            2,
            {},
            0,
            b"",
            2,
        )
        debug._msgdata.extend([msg1, msg2])

        debug.set_max_size(5)

        assert debug._msgdata.maxlen == 5
        assert list(debug._msgdata) == [msg1, msg2]

    @patch("wayland.debugger.Message.create")
    def test_log_event_like(self, mock_message_create):
        """Tests debug.log with an event-like message."""
        created_mock_msg = Message(
            time.time(), MessageType.EVENT, "sig_e", "if_e", "meth_e", 1, {}, 0, b"", 1
        )
        mock_message_create.return_value = created_mock_msg

        debug = Debugger()
        # Mock a Proxy.Event like object
        mock_proxy_event = MagicMock()
        mock_proxy_event.event = True  # Key differentiator for event
        mock_proxy_event.interface = "wl_keyboard"
        mock_proxy_event.name = "key"
        mock_proxy_event.object_id = 123
        mock_proxy_event.kwargs = {"keycode": 1}
        mock_proxy_event.opcode = 2
        mock_proxy_event.packet = b"key_event_packet"

        debug.log(mock_proxy_event)

        mock_message_create.assert_called_once_with(
            None,  # timestamp parameter
            MessageType.EVENT,
            "",  # Signature is empty in the new log method
            "wl_keyboard",
            "key",
            123,
            {"keycode": 1},
            2,
            b"key_event_packet",
            mock_message_create.call_args[0][9],  # Accept any key value
        )
        assert created_mock_msg in debug._msgdata

    @patch("wayland.debugger.Message.create")
    def test_log_request_like(self, mock_message_create):
        """Tests debug.log with a request-like message."""
        created_mock_msg = Message(
            time.time(),
            MessageType.REQUEST,
            "sig_r",
            "if_r",
            "meth_r",
            1,
            {},
            0,
            b"",
            1,
        )
        mock_message_create.return_value = created_mock_msg

        debug = Debugger()
        # Mock a Proxy.Request like object
        mock_proxy_request = MagicMock()
        mock_proxy_request.event = False  # Key differentiator for request
        mock_proxy_request.interface = "wl_surface"
        mock_proxy_request.name = "commit"
        mock_proxy_request.object_id = 456
        mock_proxy_request.kwargs = {}
        mock_proxy_request.opcode = 3
        mock_proxy_request.packet = b"commit_request_packet"

        debug.log(mock_proxy_request)

        mock_message_create.assert_called_once_with(
            None,  # timestamp parameter
            MessageType.REQUEST,
            "",  # Signature is empty
            "wl_surface",
            "commit",
            456,
            {},
            3,
            b"commit_request_packet",
            mock_message_create.call_args[0][9],  # Accept any key value
        )
        assert created_mock_msg in debug._msgdata

    def test_log_thread_safety(self):
        """Tests that logging is thread-safe."""
        debug = Debugger()
        debug.set_max_size(1000)

        def log_messages(thread_id):
            for i in range(100):
                # Mock Proxy.Event
                mock_proxy_event = MagicMock()
                mock_proxy_event.event = True
                mock_proxy_event.interface = f"if_evt_{thread_id}"
                mock_proxy_event.name = f"evt_{i}"
                mock_proxy_event.object_id = i
                mock_proxy_event.kwargs = {}
                mock_proxy_event.opcode = 0
                mock_proxy_event.packet = b""
                debug.log(mock_proxy_event)

                # Mock Proxy.Request
                mock_proxy_request = MagicMock()
                mock_proxy_request.event = False
                mock_proxy_request.interface = f"if_req_{thread_id}"
                mock_proxy_request.name = f"req_{i}"
                mock_proxy_request.object_id = i + 1000
                mock_proxy_request.kwargs = {}
                mock_proxy_request.opcode = 1
                mock_proxy_request.packet = b""
                debug.log(mock_proxy_request)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_messages, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have 5 threads * 100 events * 2 types = 1000 messages
        # But deque maxlen is 1000, so exactly 1000
        assert len(debug._msgdata) == 1000

    def test_deque_max_size_behavior(self):
        """Tests that deque properly limits size."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(3)

        # Helper to create a mock proxy message for logging
        def _create_mock_proxy_msg(name_suffix, *, is_event=True):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = 1
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        debug.log(_create_mock_proxy_msg("1"))
        debug.log(_create_mock_proxy_msg("2"))
        debug.log(_create_mock_proxy_msg("3"))
        assert len(debug._msgdata) == 3

        # Adding fourth should remove first
        debug.log(_create_mock_proxy_msg("4"))
        assert len(debug._msgdata) == 3

        # Check that oldest was removed (based on method_name from mock)
        # The actual Message.create will be called inside debug.log
        # We need to inspect the resulting Message objects in _msgdata
        method_names = [msg.method_name for msg in debug._msgdata]
        assert "method_1" not in method_names
        assert "method_4" in method_names

    def test_private_log_method(self):
        """Tests the private _log method directly."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(2)

        msg1 = Message(
            time.time(),
            MessageType.REQUEST,
            "test1",
            "if1",
            "meth1",
            1,
            {},
            0,
            b"p1",
            1,
        )
        msg2 = Message(
            time.time(), MessageType.EVENT, "test2", "if2", "meth2", 2, {}, 0, b"p2", 2
        )

        debug._log(msg1)  # Call the internal _log which expects a Message object
        assert len(debug._msgdata) == 1
        # msg1 was created with a signature, but Message.create inside debug.log will use ""
        # So we check the object identity.
        assert debug._msgdata[0] is msg1

        debug._log(msg2)
        assert len(debug._msgdata) == 2
        assert debug._msgdata[1] is msg2

    def test_mixed_logging(self):
        """Tests mixing event and request logging."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(10)

        def _create_mock_proxy_msg(name_suffix, *, is_event=True, obj_id_offset=0):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = 1 + obj_id_offset
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        debug.log(_create_mock_proxy_msg("event1", is_event=True, obj_id_offset=0))
        debug.log(_create_mock_proxy_msg("request1", is_event=False, obj_id_offset=1))
        debug.log(_create_mock_proxy_msg("event2", is_event=True, obj_id_offset=2))
        debug.log(_create_mock_proxy_msg("request2", is_event=False, obj_id_offset=3))

        assert len(debug._msgdata) == 4

        # Verify order and types
        messages = list(debug._msgdata)
        assert messages[0].msgtype == MessageType.EVENT
        assert messages[0].method_name == "method_event1"
        assert messages[1].msgtype == MessageType.REQUEST
        assert messages[1].method_name == "method_request1"
        assert messages[2].msgtype == MessageType.EVENT
        assert messages[2].method_name == "method_event2"
        assert messages[3].msgtype == MessageType.REQUEST
        assert messages[3].method_name == "method_request2"

    def test_index_access(self):
        """Tests index access using __getitem__."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(10)

        def _create_mock_proxy_msg(name_suffix, *, is_event=True, obj_id_offset=0):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = 1 + obj_id_offset
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        # Add some messages
        debug.log(_create_mock_proxy_msg("event0", is_event=True, obj_id_offset=0))
        debug.log(_create_mock_proxy_msg("request1", is_event=False, obj_id_offset=1))
        debug.log(_create_mock_proxy_msg("event2", is_event=True, obj_id_offset=2))
        debug.log(_create_mock_proxy_msg("request3", is_event=False, obj_id_offset=3))

        # Test positive indexing
        assert debug[0].method_name == "method_event0"
        assert debug[0].msgtype == MessageType.EVENT
        assert debug[1].method_name == "method_request1"
        assert debug[1].msgtype == MessageType.REQUEST
        assert debug[2].method_name == "method_event2"
        assert debug[2].msgtype == MessageType.EVENT
        assert debug[3].method_name == "method_request3"
        assert debug[3].msgtype == MessageType.REQUEST

        # Test negative indexing
        assert debug[-1].method_name == "method_request3"
        assert debug[-2].method_name == "method_event2"
        assert debug[-3].method_name == "method_request1"
        assert debug[-4].method_name == "method_event0"

    def test_index_access_out_of_bounds(self):
        """Tests that index access raises IndexError for out of bounds."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(10)

        def _create_mock_proxy_msg(name_suffix, *, is_event=True):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = 1
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        debug.log(_create_mock_proxy_msg("event0"))
        debug.log(_create_mock_proxy_msg("request1", is_event=False))

        # Test positive out of bounds
        with pytest.raises(IndexError):
            debug[2]

        with pytest.raises(IndexError):
            debug[10]

        # Test negative out of bounds
        with pytest.raises(IndexError):
            debug[-3]

    def test_index_access_thread_safety(self):
        """Tests that index access is thread-safe."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(100)

        def _create_mock_proxy_msg(name_suffix, *, is_event=True, obj_id=0):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = obj_id
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        # Pre-populate with some data
        for i in range(50):
            debug.log(_create_mock_proxy_msg(f"event_{i}", obj_id=i))

        results = []
        errors = []

        def access_index(index):
            try:
                result = debug[index]
                results.append((index, result.method_name))  # Check method_name
            except IndexError as e:
                errors.append((index, str(e)))

        threads = []
        for i in range(10):
            thread = threading.Thread(target=access_index, args=(i * 5,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have successful results without errors
        assert len(results) == 10
        assert len(errors) == 0

    def test_len(self):
        """Tests __len__ method."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(10)

        assert len(debug) == 0

        def _create_mock_proxy_msg(name_suffix, *, is_event=True):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = 1
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        debug.log(_create_mock_proxy_msg("event1"))
        assert len(debug) == 1

        debug.log(_create_mock_proxy_msg("request1", is_event=False))
        debug.log(_create_mock_proxy_msg("event2"))
        assert len(debug) == 3

    def test_iteration(self):
        """Tests __iter__ method for iteration support."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(10)

        # Test empty iteration
        items = list(debug)
        assert len(items) == 0

        def _create_mock_proxy_msg(name_suffix, *, is_event=True):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = 1
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        # Add some messages
        debug.log(_create_mock_proxy_msg("event1"))
        debug.log(_create_mock_proxy_msg("request1", is_event=False))
        debug.log(_create_mock_proxy_msg("event2"))

        # Test iteration
        items = list(debug)
        assert len(items) == 3
        assert items[0].method_name == "method_event1"
        assert items[0].msgtype == MessageType.EVENT
        assert items[1].method_name == "method_request1"
        assert items[1].msgtype == MessageType.REQUEST
        assert items[2].method_name == "method_event2"
        assert items[2].msgtype == MessageType.EVENT

        # Test iteration with for loop
        method_names = [msg.method_name for msg in debug]

        assert method_names == ["method_event1", "method_request1", "method_event2"]

    def test_iteration_thread_safety(self):
        """Tests that iteration is thread-safe."""
        debug = Debugger()
        debug.clear()
        debug.set_max_size(100)

        def _create_mock_proxy_msg(name_suffix, *, is_event=True, obj_id=0):
            mock_msg = MagicMock()
            mock_msg.event = is_event
            mock_msg.interface = "interface"
            mock_msg.name = f"method_{name_suffix}"
            mock_msg.object_id = obj_id
            mock_msg.kwargs = {}
            mock_msg.opcode = 0
            mock_msg.packet = b""
            return mock_msg

        # Pre-populate with some data
        for i in range(10):
            debug.log(_create_mock_proxy_msg(f"event_{i}", obj_id=i))

        iteration_results = []

        def iterate_debug():
            items = list(debug)  # This should be thread-safe due to _msglock
            iteration_results.append(len(items))

        def add_messages():
            for i in range(10, 20):
                debug.log(_create_mock_proxy_msg(f"event_{i}", obj_id=i))

        # Start iteration and addition concurrently
        iter_thread = threading.Thread(target=iterate_debug)
        add_thread = threading.Thread(target=add_messages)

        iter_thread.start()
        add_thread.start()

        iter_thread.join()
        add_thread.join()

        # The iteration should have captured a consistent snapshot
        assert len(iteration_results) == 1
        # The length should be either 10 (before additions) or some value during additions
        assert iteration_results[0] >= 10


class TestDebuggerCommands(unittest.TestCase):
    """Tests for debugger command functionality."""

    def test_get_range_command(self):
        """Tests the 'get range A,B' command functionality."""
        from wayland.debugger_commands import DebuggerCommandHandler

        debug = Debugger()
        debug.clear()
        handler = DebuggerCommandHandler(debug)

        # Add some test messages with specific keys
        msg1 = Message(
            time.time(), MessageType.REQUEST, "sig1", "if1", "meth1", 1, {}, 0, b"p1", 5
        )
        msg2 = Message(
            time.time(), MessageType.EVENT, "sig2", "if2", "meth2", 2, {}, 0, b"p2", 6
        )
        msg3 = Message(
            time.time(),
            MessageType.REQUEST,
            "sig3",
            "if3",
            "meth3",
            3,
            {},
            0,
            b"p3",
            7,
        )
        msg4 = Message(
            time.time(), MessageType.EVENT, "sig4", "if4", "meth4", 4, {}, 0, b"p4", 8
        )

        debug._log(msg1)
        debug._log(msg2)
        debug._log(msg3)
        debug._log(msg4)

        # Mock socket for testing
        mock_sock = MagicMock()
        debug.send_data = MagicMock(return_value=True)

        # Test range that includes some messages
        result = handler._handle_get_range(mock_sock, 6, 7)
        assert result is True

        # Should have called send_data twice (for messages with keys 6 and 7)
        assert debug.send_data.call_count == 2

        # Test range with no messages
        debug.send_data.reset_mock()
        debug.send_text = MagicMock(return_value=True)
        result = handler._handle_get_range(mock_sock, 25, 30)
        assert result is True

        # Should have sent a "no messages found" text message
        debug.send_text.assert_called_once()

    def test_get_range_command_invalid_range(self):
        """Tests the 'get range A,B' command with invalid range."""
        from wayland.debugger_commands import DebuggerCommandHandler

        debug = Debugger()
        handler = DebuggerCommandHandler(debug)
        mock_sock = MagicMock()
        debug.send_text = MagicMock(return_value=True)

        # Test with start > end
        result = handler._handle_get_range(mock_sock, 20, 10)
        assert result is False

        # Should have sent an error message
        debug.send_text.assert_called_once()


if __name__ == "__main__":
    unittest.main()
