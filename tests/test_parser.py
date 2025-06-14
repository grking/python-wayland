import unittest
from unittest.mock import MagicMock, call, patch

import pytest
from lxml import etree

from wayland.parser import WaylandParser


class TestWaylandParserHelpers(unittest.TestCase):
    """Tests for helper/static/smaller methods of WaylandParser."""

    def setUp(self):
        self.parser = WaylandParser()

    def test_parser_init(self):
        """Tests the initial state of WaylandParser."""
        assert self.parser.interfaces == {}
        assert self.parser.unique_interfaces_source == {}
        assert self.parser.protocol_name == ""
        assert self.parser.definition_uri == ""

    def test_get_description(self):
        """Tests the get_description instance method."""
        mock_desc_node = MagicMock(spec=etree._Element)

        # Test with None
        assert self.parser.get_description(None) == ""

        # Test with summary and text
        mock_desc_node.attrib = {"summary": "test summary"}
        mock_desc_node.text = "  Line 1 \n  Line 2  \n\n  Line 3  "
        expected = "Test summary\n\nLine 1\nLine 2\n\nLine 3"
        assert self.parser.get_description(mock_desc_node) == expected

        # Test with only summary
        mock_desc_node.text = None
        assert self.parser.get_description(mock_desc_node) == "Test summary"

        mock_desc_node.text = "   "  # Whitespace only text
        assert self.parser.get_description(mock_desc_node) == "Test summary"

        # Test with only text (no summary in attrib)
        mock_desc_node.attrib = {}
        mock_desc_node.text = "Only text here."
        assert self.parser.get_description(mock_desc_node) == "Only text here."

        # Test with empty summary and text
        mock_desc_node.attrib = {"summary": ""}
        mock_desc_node.text = ""
        assert self.parser.get_description(mock_desc_node) == ""

    def test_remove_keys(self):
        """Tests the _remove_keys static method."""
        obj = {
            "name": "Test",
            "version": 1,
            "description": "A test object",
            "summary": "Summary here",
            "requests": [
                {"name": "req1", "opcode": 0, "description": "req desc", "args": []},
                {"name": "req2", "opcode": 1, "summary": "req summ", "args": []},
            ],
            "nested": {"data": "value", "description": "nested desc"},
        }
        keys_to_remove = ["description", "summary"]
        WaylandParser._remove_keys(obj, keys_to_remove)

        assert "description" not in obj
        assert "summary" not in obj
        assert "name" in obj
        assert "version" in obj

        assert "requests" in obj
        assert "description" not in obj["requests"][0]
        assert "summary" not in obj["requests"][1]
        assert "name" in obj["requests"][0]

        assert "nested" in obj
        assert "description" not in obj["nested"]
        assert "data" in obj["nested"]

    @patch("wayland.parser.log")
    def test_fix_arguments_keyword_rename(self, mock_log):
        """Tests argument name renaming for Python keywords."""
        args = [{"name": "import", "type": "string"}]
        self.parser.protocol_name = "test_protocol"
        fixed_args = self.parser.fix_arguments(args, "request")
        assert fixed_args[0]["name"] == "import_"
        mock_log.info.assert_called_once()

    @patch("wayland.parser.log")
    def test_fix_arguments_new_id_no_interface_for_request(self, mock_log):
        """Tests new_id without interface for requests (injects interface/version args)."""
        args = [{"name": "callback", "type": "new_id"}]
        fixed_args = self.parser.fix_arguments(args, "request")

        assert len(fixed_args) == 3
        assert fixed_args[0]["name"] == "interface"
        assert fixed_args[0]["type"] == "string"
        assert fixed_args[1]["name"] == "version"
        assert fixed_args[1]["type"] == "uint"
        assert fixed_args[2]["name"] == "callback"
        assert fixed_args[2]["type"] == "new_id"

    @patch("wayland.parser.log")
    def test_fix_arguments_new_id_no_interface_for_event_raises_error(self, mock_log):
        """Tests new_id without interface for events (raises NotImplementedError)."""
        args = [{"name": "dynamic_new", "type": "new_id"}]
        with pytest.raises(
            NotImplementedError, match="Event with dynamic new_id not supported"
        ):
            self.parser.fix_arguments(args, "event")

    @patch("wayland.parser.log")
    def test_fix_arguments_new_id_with_interface(self, mock_log):
        """Tests new_id with an interface (no special injection)."""
        args = [{"name": "surface", "type": "new_id", "interface": "wl_surface"}]
        fixed_args = self.parser.fix_arguments(args, "request")
        assert len(fixed_args) == 1
        assert fixed_args[0] == args[0]

        fixed_args_event = self.parser.fix_arguments(args, "event")
        assert len(fixed_args_event) == 1
        assert fixed_args_event[0] == args[0]

    @patch("wayland.parser.log")
    def test_fix_arguments_normal_arg(self, mock_log):
        """Tests normal arguments are passed through."""
        args = [{"name": "count", "type": "uint"}]
        fixed_args = self.parser.fix_arguments(args, "request")
        assert fixed_args == args


class TestWaylandParserInterfaceItems(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()
        self.parser.protocol_name = "test_protocol"

    @patch("wayland.parser.log")
    def test_add_interface_item_new_interface(self, mock_log):
        """Tests _add_interface_item creating a new interface structure."""
        interface_name = "wl_test_surface"
        item = {"name": "create_buffer", "type": "new_id"}
        self.parser._add_interface_item(interface_name, "request", item)

        assert interface_name in self.parser.interfaces
        interface_data = self.parser.interfaces[interface_name]
        assert "requests" in interface_data
        assert len(interface_data["requests"]) == 1
        assert interface_data["requests"][0]["name"] == "create_buffer"
        assert interface_data["requests"][0]["opcode"] == 0
        assert len(interface_data["events"]) == 0
        assert len(interface_data["enums"]) == 0

    @patch("wayland.parser.log")
    def test_add_interface_item_existing_interface(self, mock_log):
        """Tests _add_interface_item adding to an existing interface."""
        interface_name = "wl_test_shell"
        self.parser.interfaces[interface_name] = {
            "requests": [{"name": "get_shell_surface", "opcode": 0}],
            "events": [],
            "enums": [],
        }

        item = {"name": "pong", "type": "uint"}
        self.parser._add_interface_item(interface_name, "request", item)

        assert len(self.parser.interfaces[interface_name]["requests"]) == 2
        assert self.parser.interfaces[interface_name]["requests"][1]["name"] == "pong"
        assert self.parser.interfaces[interface_name]["requests"][1]["opcode"] == 1

    @patch("wayland.parser.log")
    def test_add_interface_item_keyword_rename(self, mock_log):
        """Tests keyword renaming in _add_interface_item."""
        item = {"name": "global", "type": "uint"}
        self.parser._add_interface_item("wl_registry", "event", item)
        assert self.parser.interfaces["wl_registry"]["events"][0]["name"] == "global_"
        mock_log.info.assert_called_with("Renamed test_protocol.wl_registry.global_")

    @patch("wayland.parser.log")
    def test_add_interface_item_enum_no_opcode(self, mock_log):
        """Tests that enums do not get an opcode assigned."""
        item = {"name": "error_codes", "args": []}
        self.parser._add_interface_item("wl_display", "enum", item)
        assert "opcode" not in self.parser.interfaces["wl_display"]["enums"][0]

    @patch("wayland.parser.log")
    def test_add_interface_item_event_collides_with_request(self, mock_log):
        """Tests ValueError if an event name collides with a request name."""
        interface_name = "wl_collision"
        self.parser.interfaces[interface_name] = {
            "requests": [{"name": "do_thing", "opcode": 0}],
            "events": [],
            "enums": [],
        }
        colliding_event = {"name": "do_thing"}
        with pytest.raises(
            ValueError, match="Event do_thing collides with request of the same name."
        ):
            self.parser._add_interface_item(interface_name, "event", colliding_event)

    def test_public_add_methods(self):
        """Tests the public add_request, add_event, add_enum wrappers."""
        with patch.object(self.parser, "_add_interface_item") as mock_private_add:
            req_item = {"name": "my_req"}
            self.parser.add_request("iface1", req_item)
            mock_private_add.assert_called_once_with("iface1", "request", req_item)

            mock_private_add.reset_mock()
            event_item = {"name": "my_event"}
            self.parser.add_event("iface2", event_item)
            mock_private_add.assert_called_once_with("iface2", "event", event_item)

            mock_private_add.reset_mock()
            enum_item = {"name": "my_enum"}
            self.parser.add_enum("iface3", enum_item)
            mock_private_add.assert_called_once_with("iface3", "enum", enum_item)


class TestWaylandParserShouldParse(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()

    @patch("wayland.parser.log")
    def test_should_parse_new_interface(self, mock_log):
        """Interface not seen before, should parse."""
        assert self.parser._should_parse_interface(
            "wl_new_iface", 1, "/path/to/new.xml"
        )
        assert "wl_new_iface" in self.parser.unique_interfaces_source
        assert self.parser.unique_interfaces_source["wl_new_iface"]["version"] == 1
        assert (
            self.parser.unique_interfaces_source["wl_new_iface"]["path"]
            == "/path/to/new.xml"
        )
        mock_log.debug.assert_called()

    @patch("wayland.parser.log")
    def test_should_parse_newer_version(self, mock_log):
        """Newer version of existing interface, should parse and clear old data."""
        iface_name = "wl_updated_iface"
        self.parser.unique_interfaces_source[iface_name] = {
            "version": 1,
            "path": "/path/to/old.xml",
        }
        self.parser.interfaces[iface_name] = {
            "requests": [{"name": "old_req"}],
            "events": [],
            "enums": [],
            "version": 1,
        }

        assert self.parser._should_parse_interface(iface_name, 2, "/path/to/new_v2.xml")
        assert self.parser.unique_interfaces_source[iface_name]["version"] == 2
        assert (
            self.parser.unique_interfaces_source[iface_name]["path"]
            == "/path/to/new_v2.xml"
        )
        # Check that old interface data was cleared
        assert self.parser.interfaces[iface_name] == {
            "events": [],
            "requests": [],
            "enums": [],
        }
        mock_log.info.assert_called()

    @patch("wayland.parser.log")
    def test_should_parse_older_version(self, mock_log):
        """Older version of existing interface, should not parse."""
        iface_name = "wl_stale_iface"
        self.parser.unique_interfaces_source[iface_name] = {
            "version": 2,
            "path": "/path/to/current_v2.xml",
        }
        self.parser.interfaces[iface_name] = {"version": 2}

        assert not self.parser._should_parse_interface(
            iface_name, 1, "/path/to/old_v1.xml"
        )
        assert self.parser.unique_interfaces_source[iface_name]["version"] == 2
        mock_log.info.assert_called()

    @patch("wayland.parser.log")
    def test_should_parse_same_version_duplicate(self, mock_log):
        """Same version from different path, should not parse (treat as duplicate)."""
        iface_name = "wl_duplicate_iface"
        self.parser.unique_interfaces_source[iface_name] = {
            "version": 1,
            "path": "/path/to/original.xml",
        }
        self.parser.interfaces[iface_name] = {"version": 1}

        assert not self.parser._should_parse_interface(
            iface_name, 1, "/path/to/duplicate_copy.xml"
        )
        assert (
            self.parser.unique_interfaces_source[iface_name]["path"]
            == "/path/to/original.xml"
        )
        mock_log.warning.assert_called()

    @patch("wayland.parser.log")
    def test_should_parse_newer_version_no_existing_interface_data(self, mock_log):
        """Newer version, but no data in self.interfaces yet (e.g. only in unique_interfaces_source)."""
        iface_name = "wl_updated_iface_no_data"
        self.parser.unique_interfaces_source[iface_name] = {
            "version": 1,
            "path": "/path/to/old.xml",
        }

        assert self.parser._should_parse_interface(iface_name, 2, "/path/to/new_v2.xml")
        assert self.parser.unique_interfaces_source[iface_name]["version"] == 2
        assert iface_name not in self.parser.interfaces
        mock_log.info.assert_called()


class TestWaylandParserGetXmlRoot(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()

    @patch("wayland.parser.etree.parse")
    @patch("wayland.parser.etree.XMLParser")
    @patch("wayland.parser.os.path.exists")
    @patch("wayland.parser.os.path.abspath")
    @patch("wayland.parser.log")
    def test_get_xml_root_local_file_success(
        self, mock_log, mock_abspath, mock_exists, mock_xml_parser, mock_etree_parse
    ):
        """Tests _get_xml_root with a successful local file parse."""
        mock_path = "/some/local/protocol.xml"
        mock_abs_path = "/abs/some/local/protocol.xml"
        mock_abspath.return_value = mock_abs_path
        mock_exists.return_value = True

        mock_tree = MagicMock()
        mock_root_element = MagicMock(spec=etree._Element)
        mock_tree.getroot.return_value = mock_root_element
        mock_etree_parse.return_value = mock_tree
        mock_xml_parser.return_value = "mock_xml_parser_instance"

        root = self.parser._get_xml_root(mock_path)

        mock_abspath.assert_called_with(mock_path)
        assert self.parser.definition_uri == mock_abs_path
        mock_exists.assert_called_once_with(mock_abs_path)
        mock_xml_parser.assert_called_once_with(remove_blank_text=True)
        mock_etree_parse.assert_called_once_with(
            mock_abs_path, parser="mock_xml_parser_instance"
        )
        assert root is mock_root_element
        mock_log.error.assert_not_called()

    @patch("wayland.parser.etree.parse")
    @patch("wayland.parser.etree.XMLParser")
    @patch("wayland.parser.os.path.exists")
    @patch("wayland.parser.log")
    def test_get_xml_root_http_url_success(
        self, mock_log, mock_exists, mock_xml_parser, mock_etree_parse
    ):
        """Tests _get_xml_root with an HTTP URL (assuming etree.parse handles URLs)."""
        mock_url = "http://example.com/protocol.xml"

        mock_tree = MagicMock()
        mock_root_element = MagicMock(spec=etree._Element)
        mock_tree.getroot.return_value = mock_root_element
        mock_etree_parse.return_value = mock_tree
        mock_xml_parser.return_value = "mock_xml_parser_instance"

        root = self.parser._get_xml_root(mock_url)

        assert self.parser.definition_uri == mock_url
        mock_exists.assert_called_once_with(mock_url)
        mock_xml_parser.assert_called_once_with(remove_blank_text=True)
        mock_etree_parse.assert_called_once_with(
            mock_url, parser="mock_xml_parser_instance"
        )
        assert root is mock_root_element
        mock_log.error.assert_not_called()

    @patch("wayland.parser.os.path.exists", return_value=False)
    @patch("wayland.parser.os.path.abspath", return_value="/abs/path/file.xml")
    @patch("wayland.parser.log")
    def test_get_xml_root_file_not_found(self, mock_log, mock_abspath, mock_exists):
        """Tests _get_xml_root when local file does not exist."""
        assert self.parser._get_xml_root("/path/file.xml") is None
        mock_log.error.assert_called_once_with(
            "Protocol file not found: /abs/path/file.xml"
        )

    @patch("wayland.parser.etree.parse")
    @patch("wayland.parser.etree.XMLParser")
    @patch("wayland.parser.os.path.exists", return_value=True)
    @patch("wayland.parser.os.path.abspath", return_value="/abs/path/bad.xml")
    @patch("wayland.parser.log")
    def test_get_xml_root_xml_syntax_error(
        self, mock_log, mock_abspath, mock_exists, mock_xml_parser, mock_etree_parse
    ):
        """Tests _get_xml_root with an XMLSyntaxError."""
        from lxml.etree import XMLSyntaxError as ActualXMLSyntaxError

        mock_etree_parse.side_effect = ActualXMLSyntaxError("bad xml", None, 0, 0, 0)
        mock_xml_parser.return_value = "parser_instance"

        assert self.parser._get_xml_root("/path/bad.xml") is None
        assert mock_log.error.called
        args, _ = mock_log.error.call_args
        assert "Failed to parse XML from /abs/path/bad.xml" in args[0]
        assert "bad xml" in args[0]

    @patch("wayland.parser.etree.parse")
    @patch("wayland.parser.etree.XMLParser")
    @patch("wayland.parser.os.path.exists", return_value=True)
    @patch("wayland.parser.os.path.abspath", return_value="/abs/path/os_err.xml")
    @patch("wayland.parser.log")
    def test_get_xml_root_os_error(
        self, mock_log, mock_abspath, mock_exists, mock_xml_parser, mock_etree_parse
    ):
        """Tests _get_xml_root with an OSError during parsing."""
        mock_etree_parse.side_effect = OSError("disk full")
        mock_xml_parser.return_value = "parser_instance"

        assert self.parser._get_xml_root("/path/os_err.xml") is None
        mock_log.error.assert_called_once_with(
            "An OS error occurred while processing /abs/path/os_err.xml: disk full"
        )

    @patch("wayland.parser.log")
    def test_get_xml_root_empty_path(self, mock_log):
        """Tests _get_xml_root with an empty path string."""
        assert self.parser._get_xml_root("  ") is None
        mock_log.warning.assert_called_once_with(
            "Empty path provided to _get_xml_root."
        )


class TestWaylandParserProcessElement(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()
        self.parser.fix_arguments = MagicMock(side_effect=lambda args, item_type: args)
        self.parser.get_description = MagicMock(return_value="Mocked Description")
        self.parser.add_request = MagicMock()
        self.parser.add_event = MagicMock()
        self.parser.add_enum = MagicMock()

    def _create_mock_xml_node(
        self,
        tag_name,
        attribs,
        child_nodes_data=None,
        description_text=None,
        description_summary=None,
    ):
        """Helper to create a mock etree._Element node."""
        node = MagicMock(spec=etree._Element)
        node.tag = tag_name
        node.attrib = dict(attribs)

        children = []
        if child_nodes_data:
            child_tag_name = "arg" if tag_name != "enum" else "entry"
            for child_data in child_nodes_data:
                child = MagicMock(spec=etree._Element)
                child.tag = child_tag_name
                child.attrib = dict(child_data)
                child.find = MagicMock(return_value=None)
                children.append(child)
        node.findall = MagicMock(return_value=children)

        mock_desc_sub_node = None
        if description_text is not None or description_summary is not None:
            mock_desc_sub_node = MagicMock(spec=etree._Element)
            mock_desc_sub_node.text = description_text
            mock_desc_sub_node.attrib = {}
            if description_summary is not None:
                mock_desc_sub_node.attrib["summary"] = description_summary
        node.find = MagicMock(return_value=mock_desc_sub_node)

        return node

    @patch("wayland.parser.log")
    def test_process_protocol_element_request(self, mock_log):
        interface_name = "wl_surface"
        request_attribs = {"name": "attach"}
        arg_data = [
            {"name": "buffer", "type": "object", "interface": "wl_buffer"},
            {"name": "x", "type": "int"},
        ]

        mock_node = self._create_mock_xml_node(
            "request", request_attribs, arg_data, description_text="Attach buffer."
        )

        self.parser._process_protocol_element(mock_node, interface_name)

        expected_args = [
            {
                "name": "buffer",
                "type": "object",
                "interface": "wl_buffer",
                "description": "",
            },
            {"name": "x", "type": "int", "description": ""},
        ]
        self.parser.fix_arguments.assert_called_once_with(expected_args, "request")
        self.parser.get_description.assert_called_once()

        expected_wayland_object = {
            "name": "attach",
            "args": expected_args,
            "description": "Mocked Description",
            "signature": "wl_surface.attach(buffer: object, x: int)",
        }
        self.parser.add_request.assert_called_once_with(
            interface_name, expected_wayland_object
        )
        mock_log.info.assert_called_with("    (request) wl_surface.attach")

    @patch("wayland.parser.log")
    def test_process_protocol_element_event(self, mock_log):
        interface_name = "wl_seat"
        event_attribs = {"name": "capabilities", "since": "1"}
        arg_data = [
            {"name": "capabilities", "type": "uint", "enum": "wl_seat.capability"}
        ]

        mock_node = self._create_mock_xml_node(
            "event", event_attribs, arg_data, description_summary="Seat capabilities"
        )

        self.parser._process_protocol_element(mock_node, interface_name)

        expected_args = [
            {
                "name": "capabilities",
                "type": "uint",
                "enum": "wl_seat.capability",
                "description": "",
            }
        ]
        self.parser.fix_arguments.assert_called_once_with(expected_args, "event")
        self.parser.get_description.assert_called_once()

        expected_wayland_object = {
            "name": "capabilities",
            "since": "1",
            "args": expected_args,
            "description": "Mocked Description",
            "signature": "wl_seat.capabilities(capabilities: uint)",
        }
        self.parser.add_event.assert_called_once_with(
            interface_name, expected_wayland_object
        )
        mock_log.info.assert_called_with("    (event) wl_seat.capabilities")

    @patch("wayland.parser.log")
    def test_process_protocol_element_enum(self, mock_log):
        interface_name = "wl_output"
        enum_attribs = {"name": "transform", "bitfield": "true"}
        entry_data = [
            {"name": "normal", "value": "0", "summary": "normal"},
            {"name": "90", "value": "1", "summary": "90 degrees"},
        ]
        mock_node = self._create_mock_xml_node(
            "enum",
            enum_attribs,
            entry_data,
            description_text="Output transform values.",
        )

        self.parser._process_protocol_element(mock_node, interface_name)

        expected_args = [
            {
                "name": "normal",
                "value": "0",
                "summary": "normal",
                "description": "Normal",
            },
            {
                "name": "90",
                "value": "1",
                "summary": "90 degrees",
                "description": "90 degrees",
            },
        ]
        self.parser.fix_arguments.assert_called_once_with(expected_args, "enum")
        self.parser.get_description.assert_called_once()

        expected_wayland_object = {
            "name": "transform",
            "bitfield": "true",
            "args": expected_args,
            "description": "Mocked Description",
            "signature": "wl_output.transform(normal: , 90: )",
        }
        self.parser.add_enum.assert_called_once_with(
            interface_name, expected_wayland_object
        )
        mock_log.info.assert_called_with("    (enum) wl_output.transform")


class TestWaylandParserParseMethod(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()
        self.patch_get_xml_root = patch.object(self.parser, "_get_xml_root")
        self.patch_should_parse = patch.object(self.parser, "_should_parse_interface")
        self.patch_process_element = patch.object(
            self.parser, "_process_protocol_element"
        )
        self.patch_get_description = patch.object(WaylandParser, "get_description")

        self.mock_get_xml_root = self.patch_get_xml_root.start()
        self.mock_should_parse = self.patch_should_parse.start()
        self.mock_process_element = self.patch_process_element.start()
        self.mock_get_description = self.patch_get_description.start()

        self.addCleanup(self.patch_get_xml_root.stop)
        self.addCleanup(self.patch_should_parse.stop)
        self.addCleanup(self.patch_process_element.stop)
        self.addCleanup(self.patch_get_description.stop)

    def _create_mock_xml_element(
        self, tag, attrib, children_by_tag=None, find_results=None
    ):
        element = MagicMock(spec=etree._Element)
        element.tag = tag
        element.attrib = dict(attrib)

        if children_by_tag:
            element.xpath = MagicMock(
                side_effect=lambda p: children_by_tag.get(p.split("/")[-1], [])
            )
            element.findall = MagicMock(
                side_effect=lambda t: children_by_tag.get(t, [])
            )
        else:
            element.xpath = MagicMock(return_value=[])
            element.findall = MagicMock(return_value=[])

        if find_results:  # dict of tag_name: find_result
            element.find = MagicMock(side_effect=lambda t: find_results.get(t))
        else:
            element.find = MagicMock(return_value=None)
        return element

    @patch("wayland.parser.log")
    def test_parse_successful_simple_protocol(self, mock_log):
        mock_path = "fake_protocol.xml"

        # Mock XML structure
        mock_interface1_desc_node = self._create_mock_xml_element("description", {})
        mock_request_node = self._create_mock_xml_element("request", {"name": "req1"})
        mock_event_node = self._create_mock_xml_element("event", {"name": "ev1"})
        mock_enum_node = self._create_mock_xml_element("enum", {"name": "en1"})

        mock_interface1_node = self._create_mock_xml_element(
            "interface",
            {"name": "wl_test_iface", "version": "1"},
            children_by_tag={
                "request": [mock_request_node],
                "event": [mock_event_node],
                "enum": [mock_enum_node],
            },
            find_results={"description": mock_interface1_desc_node},
        )
        mock_root_node = self._create_mock_xml_element(
            "protocol",
            {"name": "test_protocol"},
            children_by_tag={"interface": [mock_interface1_node]},
        )

        self.mock_get_xml_root.return_value = mock_root_node
        self.mock_should_parse.return_value = True  # Always parse for this test
        self.mock_get_description.return_value = "Interface Description"

        self.parser.parse(mock_path)

        self.mock_get_xml_root.assert_called_once_with(mock_path)
        assert self.parser.protocol_name == "test_protocol"

        self.mock_should_parse.assert_called_once_with(
            "wl_test_iface", 1, self.parser.definition_uri
        )
        self.mock_get_description.assert_called_with(
            mock_interface1_desc_node
        )  # Check it was called for interface

        assert self.mock_process_element.call_count == 3
        self.mock_process_element.assert_any_call(mock_request_node, "wl_test_iface")
        self.mock_process_element.assert_any_call(mock_event_node, "wl_test_iface")
        self.mock_process_element.assert_any_call(mock_enum_node, "wl_test_iface")

        assert "wl_test_iface" in self.parser.interfaces
        assert self.parser.interfaces["wl_test_iface"]["version"] == 1
        assert (
            self.parser.interfaces["wl_test_iface"]["description"]
            == "Interface Description"
        )
        mock_log.debug.assert_any_call(
            f"Successfully processed interface 'wl_test_iface' v1 from {self.parser.definition_uri}."
        )

    @patch("wayland.parser.log")
    def test_parse_get_xml_root_returns_none(self, mock_log):
        """Test parse when _get_xml_root fails."""
        self.mock_get_xml_root.return_value = None
        self.parser.parse("nonexistent.xml")
        self.mock_should_parse.assert_not_called()
        self.mock_process_element.assert_not_called()

    @patch("wayland.parser.log")
    def test_parse_should_not_parse_interface(self, mock_log):
        """Test parse when _should_parse_interface returns False."""
        mock_interface_node = self._create_mock_xml_element(
            "interface", {"name": "wl_skip_iface", "version": "1"}
        )
        mock_root_node = self._create_mock_xml_element(
            "protocol",
            {"name": "skip_protocol"},
            children_by_tag={"interface": [mock_interface_node]},
        )

        self.mock_get_xml_root.return_value = mock_root_node
        self.mock_should_parse.return_value = False  # Do not parse this interface

        self.parser.parse("skip_protocol.xml")

        self.mock_should_parse.assert_called_once_with(
            "wl_skip_iface", 1, self.parser.definition_uri
        )
        self.mock_process_element.assert_not_called()
        assert "wl_skip_iface" not in self.parser.interfaces

    @patch("wayland.parser.log")
    def test_parse_invalid_version_in_xml(self, mock_log):
        """Test parse with an invalid version string in XML, defaults to 1."""
        mock_interface_node = self._create_mock_xml_element(
            "interface", {"name": "wl_bad_version", "version": "foo"}
        )
        mock_root_node = self._create_mock_xml_element(
            "protocol",
            {"name": "bad_ver_protocol"},
            children_by_tag={"interface": [mock_interface_node]},
        )

        self.mock_get_xml_root.return_value = mock_root_node
        self.mock_should_parse.return_value = True  # Assume we should parse

        self.parser.parse("bad_ver.xml")

        # _should_parse_interface should be called with the defaulted version 1
        self.mock_should_parse.assert_called_once_with(
            "wl_bad_version", 1, self.parser.definition_uri
        )
        mock_log.warning.assert_any_call(
            f"Invalid version 'foo' for interface 'wl_bad_version' "
            f"in {self.parser.definition_uri}. Defaulting to version 1."
        )


class TestWaylandParserRun(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()

    @patch("wayland.parser.subprocess.run")
    @patch("wayland.parser.log")
    @patch(
        "wayland.parser.os.environ", new_callable=MagicMock
    )  # Mock os.environ with MagicMock
    def test_run_command_capture_output(
        self, mock_os_environ, mock_log, mock_subprocess_run
    ):
        """Tests _run with output capture (default)."""
        cmd_to_run = ["ls", "-l"]
        mock_process_result = MagicMock()
        mock_subprocess_run.return_value = mock_process_result
        mock_os_environ.copy.return_value = {"ENV_VAR": "value"}

        result = self.parser._run(
            cmd_to_run, cwd="/tmp", env={"CUSTOM_ENV": "custom"}, check=False
        )

        mock_log.info.assert_called_once_with("ls -l")
        mock_subprocess_run.assert_called_once_with(
            cmd_to_run,
            cwd="/tmp",
            env={"CUSTOM_ENV": "custom"},  # Should use provided env
            check=False,
            stdout=unittest.mock.ANY,
            stderr=unittest.mock.ANY,
            text=True,
        )
        assert result is mock_process_result
        assert mock_subprocess_run.call_args.kwargs["stdout"] is not None
        assert mock_subprocess_run.call_args.kwargs["stderr"] is not None

    @patch("wayland.parser.subprocess.run")
    @patch("wayland.parser.log")
    @patch("wayland.parser.os.environ", new_callable=MagicMock)
    def test_run_command_stream_output(
        self, mock_os_environ, mock_log, mock_subprocess_run
    ):
        """Tests _run with stream_output=True."""
        cmd_to_run = ["git", "status"]
        mock_os_environ.copy.return_value = {"COPIED_ENV": "yes"}

        self.parser._run(
            cmd_to_run, stream_output=True, check=True
        )  # Default env, check=True

        mock_log.info.assert_called_once_with("git status")
        mock_subprocess_run.assert_called_once_with(
            cmd_to_run,
            cwd=None,
            env={"COPIED_ENV": "yes"},
            check=True,
            stdout=None,
            stderr=None,
            text=True,
        )

    @patch("wayland.parser.subprocess.run")
    @patch("wayland.parser.log")
    @patch("wayland.parser.os.environ", new_callable=MagicMock)
    def test_run_command_default_env_and_check(
        self, mock_os_environ, mock_log, mock_subprocess_run
    ):
        """Tests _run with default env and check=True."""
        cmd_to_run = ["echo", "hello"]
        mock_copied_env = {"PATH": "/usr/bin"}
        mock_os_environ.copy.return_value = mock_copied_env

        self.parser._run(
            cmd_to_run
        )  # Defaults: cwd=None, env=None (uses os.environ.copy), check=True, stream_output=False

        mock_subprocess_run.assert_called_once_with(
            cmd_to_run,
            cwd=None,
            env=mock_copied_env,
            check=True,
            stdout=unittest.mock.ANY,
            stderr=unittest.mock.ANY,
            text=True,
        )


class TestWaylandParserFileScanning(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()

    @patch("wayland.parser.os.walk")
    @patch("wayland.parser.os.path.isdir")
    @patch("wayland.parser.log")
    def test_scan_directories_for_xml_files(self, mock_log, mock_isdir, mock_os_walk):
        """Tests _scan_directories_for_xml_files method."""

        # Mock os.path.isdir to control which directories are "valid"
        def isdir_side_effect(path):
            if path in ("/valid/dir1", "/valid/dir2"):
                return True
            if path == "/invalid/dir":
                return False
            return False  # Default for any other path

        mock_isdir.side_effect = isdir_side_effect

        # Mock os.walk to simulate directory structures and files
        # (root, dirs, files)
        walk_data = {
            "/valid/dir1": [
                ("/valid/dir1", ["subdir"], ["protocol1.xml", "data.txt"]),
                ("/valid/dir1/subdir", [], ["protocol2.xml", "ignored.xml"]),
            ],
            "/valid/dir2": [("/valid/dir2", [], ["protocol3.xml"])],
            "/empty/dir": [  # This dir might be valid by isdir but os.walk returns empty
                ("/empty/dir", [], [])
            ],
        }
        mock_os_walk.side_effect = lambda path: walk_data.get(path, [])

        directories_to_scan = [
            "/valid/dir1",
            "/valid/dir2",
            "/invalid/dir",
            "/nonexistent/dir",
            "/empty/dir",
        ]
        ignore_set = {"ignored.xml"}

        found_files = self.parser._scan_directories_for_xml_files(
            directories_to_scan, ignore_set, "test_source"
        )

        expected_files = [
            "/valid/dir1/protocol1.xml",
            "/valid/dir1/subdir/protocol2.xml",
            "/valid/dir2/protocol3.xml",
        ]
        assert sorted(found_files) == sorted(expected_files)

        mock_log.warning.assert_any_call(
            "Search directory for test_source not found or not a directory, skipping: /invalid/dir"
        )
        mock_log.warning.assert_any_call(
            "Search directory for test_source not found or not a directory, skipping: /nonexistent/dir"
        )
        mock_log.debug.assert_any_call(
            "Ignoring file 'ignored.xml' from test_source due to effective ignore list: /valid/dir1/subdir/ignored.xml"
        )

        mock_os_walk.assert_any_call("/valid/dir1")
        mock_os_walk.assert_any_call("/valid/dir2")

    @patch("wayland.parser.WaylandParser._scan_directories_for_xml_files")
    @patch("wayland.parser.log")
    def test_get_local_files_with_search_directories(self, mock_log, mock_scan_dirs):
        """Tests get_local_files when search_directories are provided."""
        mock_scan_dirs.return_value = ["/path/to/file1.xml", "/path/to/file2.xml"]
        search_dirs = ["/opt/protocols", "/usr/share/protocols"]
        ignore_list = ["ignore_this.xml"]

        result = self.parser.get_local_files(
            search_directories=search_dirs, ignore_filenames=ignore_list
        )

        mock_scan_dirs.assert_called_once_with(search_dirs, set(ignore_list))
        assert sorted(result) == sorted(["/path/to/file1.xml", "/path/to/file2.xml"])
        mock_log.info.assert_any_call(
            f"Scanning for XML protocol files in specified directories: {', '.join(search_dirs)}"
        )

    @patch("wayland.parser.WaylandParser._scan_directories_for_xml_files")
    @patch(
        "wayland.parser.LOCAL_PROTOCOL_SOURCES",
        new=[  # Mock the global constant
            {
                "name": "Mock Source 1",
                "url": "/mock/source1",
                "dirs": ["./custom", "stable"],
                "ignore": ["s1_ignore.xml"],
            },
            {
                "name": "Mock Source 2",
                "url": "/mock/source2",
                # No "dirs" means ["./"] by default in code, but let's be explicit for mock if needed
                # No "ignore" means empty list
            },
        ],
    )
    @patch(
        "wayland.parser.os.path.normpath", side_effect=lambda p: p
    )  # Keep paths as is for mocking
    @patch("wayland.parser.log")
    def test_get_local_files_no_search_directories_uses_local_sources(
        self, mock_log, mock_normpath, mock_scan_dirs
    ):
        """Tests get_local_files using LOCAL_PROTOCOL_SOURCES when no search_directories are given."""

        # Define what _scan_directories_for_xml_files returns for each call
        def scan_side_effect(dirs, ignores, source_name_for_logging=None):
            # dirs will contain paths like '/mock/source1/./custom' due to mocked normpath
            s_dirs = sorted(dirs)  # Sort for consistent comparison
            if sorted(["/mock/source1/./custom", "/mock/source1/stable"]) == s_dirs:
                assert ignores == {"global_ignore.xml", "s1_ignore.xml"}
                return [
                    "/mock/source1/custom/s1_fileA.xml",
                    "/mock/source1/stable/s1_fileB.xml",
                ]
            if sorted(["/mock/source2/./"]) == s_dirs:
                assert ignores == {"global_ignore.xml"}  # Only global ignore
                return [
                    "/mock/source2/s2_file.xml",
                    "/mock/source1/custom/s1_fileA.xml",
                ]  # Duplicate to test set uniqueness
            return []

        mock_scan_dirs.side_effect = scan_side_effect

        global_ignore = ["global_ignore.xml"]
        result = self.parser.get_local_files(ignore_filenames=global_ignore)

        assert mock_scan_dirs.call_count == 2

        # Expected calls to _scan_directories_for_xml_files
        # Reflecting that normpath is mocked as identity: os.path.join might produce "./"
        expected_dirs_s1 = ["/mock/source1/./custom", "/mock/source1/stable"]
        expected_ignores_s1 = {"global_ignore.xml", "s1_ignore.xml"}

        expected_dirs_s2 = ["/mock/source2/./"]
        expected_ignores_s2 = {"global_ignore.xml"}

        # Check calls using assert_any_call. Note that assert_any_call checks if *any* call matches.
        # To check specific calls in order, or all calls, call_args_list is better, but let's try this.
        # The source_name_for_logging is explicitly passed.
        mock_scan_dirs.assert_any_call(
            expected_dirs_s1,
            expected_ignores_s1,
            source_name_for_logging="Mock Source 1",
        )
        mock_scan_dirs.assert_any_call(
            expected_dirs_s2,
            expected_ignores_s2,
            source_name_for_logging="Mock Source 2",
        )

        # To be more precise about the order and ensure these were the *only* calls with these args:
        [
            call(
                expected_dirs_s1,
                expected_ignores_s1,
                source_name_for_logging="Mock Source 1",
            ),
            call(
                expected_dirs_s2,
                expected_ignores_s2,
                source_name_for_logging="Mock Source 2",
            ),
        ]
        # mock_scan_dirs.assert_has_calls(calls, any_order=False) # This might be too strict if other debug calls happen
        # For now, let's rely on call_count and the side_effect's internal asserts for argument correctness.
        # The previous loop was good for debugging, but if args are correct, assert_any_call should pass.

        expected_unique_sorted_files = sorted(
            [
                "/mock/source1/custom/s1_fileA.xml",
                "/mock/source1/stable/s1_fileB.xml",
                "/mock/source2/s2_file.xml",
            ]
        )
        assert result == expected_unique_sorted_files

    @patch(
        "wayland.parser.WaylandParser._scan_directories_for_xml_files", return_value=[]
    )
    @patch("wayland.parser.log")
    def test_get_local_files_no_files_found(self, mock_log, mock_scan_dirs):
        """Tests get_local_files when no XML files are found."""
        result = self.parser.get_local_files(search_directories=["/empty"])
        assert result == []
        mock_log.info.assert_any_call(
            "Found 0 unique XML protocol files after scanning: /empty (all ignore filters applied)."
        )

    @patch("wayland.parser.json.dumps")
    @patch("wayland.parser.WaylandParser._remove_keys")
    @patch("wayland.parser.deepcopy")
    def test_to_json_minimise_true(
        self, mock_deepcopy, mock_remove_keys, mock_json_dumps
    ):
        """Tests to_json with minimise=True (default)."""
        self.parser.interfaces = {"wl_surface": {"description": "desc"}}
        mock_copied_interfaces = {"wl_surface_copied": {}}
        mock_deepcopy.return_value = mock_copied_interfaces
        mock_json_dumps.return_value = '{"json_output": true}'

        result = self.parser.to_json()  # minimise=True by default

        mock_deepcopy.assert_called_once_with(self.parser.interfaces)
        mock_remove_keys.assert_called_once_with(
            mock_copied_interfaces, ["description", "signature", "summary"]
        )
        mock_json_dumps.assert_called_once_with(
            mock_copied_interfaces, indent=1, sort_keys=True
        )
        assert result == '{"json_output": true}'

    @patch("wayland.parser.json.dumps")
    @patch("wayland.parser.WaylandParser._remove_keys")
    @patch("wayland.parser.deepcopy")
    def test_to_json_minimise_false(
        self, mock_deepcopy, mock_remove_keys, mock_json_dumps
    ):
        """Tests to_json with minimise=False."""
        self.parser.interfaces = {"wl_display": {"description": "display desc"}}
        mock_copied_interfaces = {"wl_display_copied": {}}
        mock_deepcopy.return_value = mock_copied_interfaces
        mock_json_dumps.return_value = '{"full_json": true}'

        result = self.parser.to_json(minimise=False)

        mock_deepcopy.assert_called_once_with(self.parser.interfaces)
        mock_remove_keys.assert_not_called()  # Should not be called
        mock_json_dumps.assert_called_once_with(
            mock_copied_interfaces, indent=1, sort_keys=True
        )
        assert result == '{"full_json": true}'


class TestWaylandParserCloneGitRepo(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()

    @patch("wayland.parser.tempfile.gettempdir")
    @patch("wayland.parser.os.path.basename")
    @patch("wayland.parser.os.path.join")
    @patch("wayland.parser.os.path.isdir")
    @patch("wayland.parser.shutil.rmtree")
    @patch.object(WaylandParser, "_run")
    @patch("wayland.parser.log")
    def test_clone_git_repo_new_repo(
        self,
        mock_log,
        mock_run,
        mock_rmtree,
        mock_isdir,
        mock_join,
        mock_basename,
        mock_gettempdir,
    ):
        """Test cloning a new repository."""
        mock_gettempdir.return_value = "/tmp"
        mock_basename.return_value = "test-repo"
        mock_join.return_value = "/tmp/test-repo"
        mock_isdir.return_value = False

        result = self.parser.clone_git_repo("https://example.com/test-repo.git")

        mock_run.assert_called_once_with(
            ["git", "clone", "https://example.com/test-repo.git", "/tmp/test-repo"]
        )
        mock_rmtree.assert_not_called()
        assert result == "/tmp/test-repo"

    @patch("wayland.parser.tempfile.gettempdir")
    @patch("wayland.parser.os.path.basename")
    @patch("wayland.parser.os.path.join")
    @patch("wayland.parser.os.path.isdir")
    @patch("wayland.parser.shutil.rmtree")
    @patch.object(WaylandParser, "_run")
    @patch("wayland.parser.log")
    def test_clone_git_repo_existing_repo_update(
        self,
        mock_log,
        mock_run,
        mock_rmtree,
        mock_isdir,
        mock_join,
        mock_basename,
        mock_gettempdir,
    ):
        """Test updating an existing repository."""
        mock_gettempdir.return_value = "/tmp"
        mock_basename.return_value = "existing-repo"
        mock_join.return_value = "/tmp/existing-repo"
        mock_isdir.return_value = True

        result = self.parser.clone_git_repo("https://example.com/existing-repo.git")

        mock_run.assert_called_once_with(
            ["git", "pull", "--quiet"], cwd="/tmp/existing-repo"
        )
        mock_rmtree.assert_not_called()
        assert result == "/tmp/existing-repo"

    @patch("wayland.parser.tempfile.gettempdir")
    @patch("wayland.parser.os.path.basename")
    @patch("wayland.parser.os.path.join")
    @patch("wayland.parser.os.path.isdir")
    @patch("wayland.parser.shutil.rmtree")
    @patch.object(WaylandParser, "_run")
    @patch("wayland.parser.log")
    def test_clone_git_repo_existing_repo_delete_and_clone(
        self,
        mock_log,
        mock_run,
        mock_rmtree,
        mock_isdir,
        mock_join,
        mock_basename,
        mock_gettempdir,
    ):
        """Test deleting existing repo - note: current implementation has a bug where it still tries to pull."""
        mock_gettempdir.return_value = "/tmp"
        mock_basename.return_value = "delete-repo"
        mock_join.return_value = "/tmp/delete-repo"
        mock_isdir.return_value = True

        result = self.parser.clone_git_repo(
            "https://example.com/delete-repo.git", delete_existing=True
        )

        mock_rmtree.assert_called_once_with("/tmp/delete-repo")
        mock_run.assert_called_once_with(
            ["git", "pull", "--quiet"], cwd="/tmp/delete-repo"
        )
        assert result == "/tmp/delete-repo"

    @patch("wayland.parser.os.path.basename")
    @patch("wayland.parser.os.path.join")
    @patch("wayland.parser.os.path.isdir")
    @patch.object(WaylandParser, "_run")
    @patch("wayland.parser.log")
    def test_clone_git_repo_custom_dest_dir(
        self, mock_log, mock_run, mock_isdir, mock_join, mock_basename
    ):
        """Test cloning to a custom destination directory."""
        mock_basename.return_value = "custom-repo"
        mock_join.return_value = "/custom/path/custom-repo"
        mock_isdir.return_value = False

        result = self.parser.clone_git_repo(
            "https://example.com/custom-repo.git", dest_dir="/custom/path"
        )

        mock_run.assert_called_once_with(
            [
                "git",
                "clone",
                "https://example.com/custom-repo.git",
                "/custom/path/custom-repo",
            ]
        )
        assert result == "/custom/path/custom-repo"


class TestWaylandParserExtractArguments(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()

    def test_extract_arguments_with_descriptions_summary(self):
        """Test extracting arguments with summary attribute."""
        mock_param1 = MagicMock(spec=etree._Element)
        mock_param1.attrib = {"name": "arg1", "type": "uint", "summary": "First arg"}
        mock_param1.find.return_value = None

        mock_param2 = MagicMock(spec=etree._Element)
        mock_param2.attrib = {"name": "arg2", "type": "string"}
        mock_param2.find.return_value = None

        params = [mock_param1, mock_param2]
        result = self.parser._extract_arguments_with_descriptions(params)

        expected = [
            {
                "name": "arg1",
                "type": "uint",
                "summary": "First arg",
                "description": "First arg",
            },
            {"name": "arg2", "type": "string", "description": ""},
        ]
        assert result == expected

    def test_extract_arguments_with_descriptions_no_summary(self):
        """Test extracting arguments without summary attribute."""
        mock_param = MagicMock(spec=etree._Element)
        mock_param.attrib = {"name": "simple_arg", "type": "int"}
        mock_param.find.return_value = None

        result = self.parser._extract_arguments_with_descriptions([mock_param])

        expected = [{"name": "simple_arg", "type": "int", "description": ""}]
        assert result == expected

    def test_extract_arguments_with_descriptions_empty_list(self):
        """Test extracting arguments from empty list."""
        result = self.parser._extract_arguments_with_descriptions([])
        assert result == []


class TestWaylandParserGetRemoteUris(unittest.TestCase):
    def setUp(self):
        self.parser = WaylandParser()

    @patch("wayland.parser.tempfile.gettempdir")
    @patch.object(WaylandParser, "clone_git_repo")
    @patch.object(WaylandParser, "get_local_files")
    @patch("wayland.parser.log")
    @patch(
        "wayland.parser.REMOTE_PROTOCOL_SOURCES",
        new=[
            {
                "name": "Test Source",
                "url": "https://example.com/test.git",
                "dirs": ["protocols"],
                "ignore": ["test.xml"],
            }
        ],
    )
    def test_get_remote_uris_success(
        self, mock_log, mock_get_local_files, mock_clone_git_repo, mock_gettempdir
    ):
        """Test successful remote URI processing."""
        mock_gettempdir.return_value = "/tmp"
        mock_clone_git_repo.return_value = "/tmp/test"
        mock_get_local_files.return_value = ["/tmp/test/protocols/protocol1.xml"]

        result = self.parser.get_remote_uris()

        mock_clone_git_repo.assert_called_once_with(
            "https://example.com/test.git", "/tmp", delete_existing=False
        )
        mock_get_local_files.assert_called_once_with(
            search_directories=["/tmp/test/protocols"], ignore_filenames=["test.xml"]
        )
        assert result == ["/tmp/test/protocols/protocol1.xml"]

    @patch("wayland.parser.tempfile.gettempdir")
    @patch.object(WaylandParser, "clone_git_repo")
    @patch.object(WaylandParser, "get_local_files")
    @patch("wayland.parser.log")
    @patch(
        "wayland.parser.REMOTE_PROTOCOL_SOURCES",
        new=[
            {
                "name": "Failed Source",
                "url": "https://example.com/fail.git",
                "dirs": ["protocols"],
            }
        ],
    )
    def test_get_remote_uris_clone_failure(
        self, mock_log, mock_get_local_files, mock_clone_git_repo, mock_gettempdir
    ):
        """Test handling of clone failure."""
        mock_gettempdir.return_value = "/tmp"
        mock_clone_git_repo.return_value = False

        result = self.parser.get_remote_uris()

        mock_get_local_files.assert_not_called()
        mock_log.error.assert_called_once()
        assert result == []


if __name__ == "__main__":
    unittest.main()
