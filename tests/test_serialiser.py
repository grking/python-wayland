import json
import time
from enum import Enum

from wayland.serialiser import Message, MessageEncoder, MessageType


class MockEnum(Enum):
    TEST_VALUE = "test_value"


def test_message_encoder_json_serialization():
    """Test that MessageEncoder can serialize complex messages to JSON."""
    mock_object = type("MockObject", (), {"object_id": 42, "__module__": "test"})()

    message = Message(
        timestamp=1234567890.0,
        msgtype=MessageType.REQUEST,
        signature="test_sig",
        interface="wl_test",
        method_name="test_method",
        object_id=1,
        args={
            "enum_arg": MockEnum.TEST_VALUE,
            "bytes_arg": b"binary_data",
            "list_arg": [1, 2, 3],
            "object_arg": mock_object,
            "string_arg": "hello",
            "int_arg": 42,
        },
        opcode=1,
        packet=b"packet_data",
        key=123,
    )

    json_str = json.dumps(message, cls=MessageEncoder)
    parsed = json.loads(json_str)

    assert parsed["timestamp"] == 1234567890.0
    assert parsed["msgtype"] == "req"
    assert parsed["interface"] == "wl_test"
    assert parsed["method_name"] == "test_method"
    assert parsed["object_id"] == 1
    assert parsed["opcode"] == 1
    assert parsed["key"] == 123

    args = parsed["args"]
    assert args["enum_arg"]["value"] == "MockEnum.TEST_VALUE"
    assert args["bytes_arg"]["value"] == "YmluYXJ5X2RhdGE="
    assert args["list_arg"]["value"] == "1,2,3"
    assert args["object_arg"]["value"] == "MockObject@42"
    assert args["string_arg"]["value"] == "hello"
    assert args["int_arg"]["value"] == 42


def test_message_create_with_auto_timestamp():
    """Test Message.create automatically sets timestamp when None."""
    start_time = time.time()

    msg = Message.create(
        timestamp=None,
        msgtype="evt",
        signature="test",
        interface="test",
        method_name="test",
        object_id=1,
        args={},
        opcode=0,
        packet=b"test",
        key=1,
    )

    end_time = time.time()

    assert start_time <= msg.timestamp <= end_time
    assert msg.msgtype == MessageType.EVENT


def test_message_encoder_with_large_packet():
    """Test that large packets are truncated in serialization."""
    large_packet = b"x" * 2000

    message = Message(
        timestamp=time.time(),
        msgtype=MessageType.EVENT,
        signature="test",
        interface="test",
        method_name="test",
        object_id=1,
        args={},
        opcode=0,
        packet=large_packet,
        key=1,
    )

    json_str = json.dumps(message, cls=MessageEncoder)
    parsed = json.loads(json_str)

    import base64

    from wayland.constants import MAX_PROTOCOL_PACKET_DUMP_SIZE

    decoded_packet = base64.b64decode(parsed["packet"])
    assert len(decoded_packet) == MAX_PROTOCOL_PACKET_DUMP_SIZE
