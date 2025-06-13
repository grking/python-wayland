# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import json
import keyword
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from copy import deepcopy

from lxml import etree

from wayland.log import log

REMOTE_PROTOCOL_SOURCES = [
    {
        "name": "Wayland Main Protocol",
        "url": "https://gitlab.freedesktop.org/wayland/wayland.git",
        "dirs": ["protocol"],
        "ignore": ["tests.xml"],
    },
    {
        "name": "Official Wayland Protocol Definitions",
        "url": "https://gitlab.freedesktop.org/wayland/wayland-protocols.git",
        "dirs": ["stable", "staging", "unstable"],
        "ignore": ["linux-dmabuf-unstable-v1.xml"],
    },
    {
        "name": "Hyprland Wayland Extensions",
        "url": "https://github.com/hyprwm/hyprland-protocols",
        "dirs": ["protocols"],
    },
    {
        "name": "wlroots Protocol Extensions",
        "url": "https://gitlab.freedesktop.org/wlroots/wlr-protocols",
        "dirs": ["unstable"],
    },
]


LOCAL_PROTOCOL_SOURCES = [
    {"name": "Wayland Main Protocol", "url": "/usr/share/wayland", "dirs": ["./"]},
    {
        "name": "Official Wayland Protocol Definitions",
        "url": "/usr/share/wayland-protocols",
        "dirs": ["./"],
        "ignore": ["linux-dmabuf-unstable-v1.xml"],
    },
]


class WaylandParser:
    def __init__(self):
        self.interfaces: dict[str, dict] = {}
        self.unique_interfaces_source: dict[str, dict[str, int | str]] = {}
        self.protocol_name: str = ""
        self.definition_uri: str = ""

    def _run(
        self,
        cmd: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        check=True,
        stream_output=False,
    ):
        if stream_output:
            stdout = None  # Use parent process's stdout
            stderr = None  # Use parent process's stderr
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE

        log.info(" ".join(cmd))

        return subprocess.run(
            cmd,
            cwd=cwd,
            env=env or os.environ.copy(),
            check=check,
            stdout=stdout,
            stderr=stderr,
            text=True,
        )

    def clone_git_repo(
        self,
        repo_url: str,
        dest_dir: str | None = None,
        *,
        delete_existing=False,
    ) -> bool:
        if dest_dir is None:
            dest_dir = tempfile.gettempdir()

        repo_name = os.path.basename(repo_url)
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        target_dir = os.path.join(dest_dir, repo_name)

        log.info(f"Cloning {repo_name} into {target_dir}")

        if os.path.isdir(target_dir):
            if delete_existing:
                log.info("Removing existing repo")
                shutil.rmtree(target_dir)
            log.info("Updating exist repo")
            self._run(["git", "pull", "--quiet"], cwd=target_dir)
            return target_dir

        self._run(["git", "clone", repo_url, target_dir])

        return target_dir

    def get_remote_uris(self) -> list[str]:
        temp_dir = tempfile.gettempdir()
        all_repo_files: list[str] = []

        for source in REMOTE_PROTOCOL_SOURCES:
            log.info(f"Processing protocol source: {source['name']}")
            local_dir = self.clone_git_repo(
                source["url"], temp_dir, delete_existing=False
            )
            if not local_dir:
                # Consider whether to raise an exception or just log a warning and continue
                log.error(
                    f"Unable to clone the {source['name']} repository from {source['url']}. Skipping this source."
                )
                continue

            source_search_dirs = [os.path.join(local_dir, d) for d in source["dirs"]]
            ignore_list = source.get("ignore", [])

            log.debug(
                f"Scanning directories for {source['name']}: {source_search_dirs}"
            )
            if ignore_list:
                log.debug(f"Ignoring files for {source['name']}: {ignore_list}")

            files_from_source = self.get_local_files(
                search_directories=source_search_dirs, ignore_filenames=ignore_list
            )
            all_repo_files.extend(files_from_source)
            log.debug(f"Found {len(files_from_source)} files from {source['name']}.")

        log.info(f"Total protocol files found from remote URIs: {len(all_repo_files)}")
        return all_repo_files

    def _scan_directories_for_xml_files(
        self,
        directories_to_scan: list[str],
        effective_ignore_set: set[str],
        source_name_for_logging: str = "specified directories",
    ) -> list[str]:
        """
        Scans a list of directories for .xml files, applying an ignore set.
        Helper for get_local_files.
        """
        found_files: list[str] = []
        for directory in directories_to_scan:
            if not os.path.isdir(directory):
                log.warning(
                    f"Search directory for {source_name_for_logging} not found or not a directory, skipping: {directory}"
                )
                continue
            for root, _, files in os.walk(directory):
                for file_name in files:
                    if file_name.endswith(".xml"):
                        full_file_path = os.path.join(root, file_name)
                        base_filename = os.path.basename(file_name)
                        if base_filename in effective_ignore_set:
                            log.debug(
                                f"Ignoring file '{base_filename}' from {source_name_for_logging} due to effective ignore list: {full_file_path}"
                            )
                            continue
                        found_files.append(full_file_path)
        return found_files

    def get_local_files(
        self,
        search_directories: list[str] | None = None,
        ignore_filenames: list[str] | None = None,
    ) -> list[str]:
        found_files_accumulator: list[str] = []
        global_ignore_set = set(ignore_filenames or [])
        if global_ignore_set:
            log.debug(
                f"Global ignore list active for this call: {', '.join(sorted(global_ignore_set))}"
            )

        dirs_actually_scanned_log: list[str] = []

        if search_directories is not None:
            log.info(
                f"Scanning for XML protocol files in specified directories: {', '.join(search_directories)}"
            )
            # When search_directories are provided, only the global_ignore_set applies directly.
            # The caller (e.g., get_remote_uris) is responsible for passing the correct ignore_filenames.
            dirs_actually_scanned_log.extend(search_directories)
            found_files_accumulator.extend(
                self._scan_directories_for_xml_files(
                    search_directories, global_ignore_set
                )
            )
        else:
            log.info("No search directories provided, using LOCAL_PROTOCOL_SOURCES.")
            for source_config in LOCAL_PROTOCOL_SOURCES:
                source_name = source_config["name"]
                base_path = source_config["url"]
                source_relative_dirs = source_config.get("dirs", ["./"])

                source_specific_ignores = set(source_config.get("ignore", []))
                current_effective_ignore_set = global_ignore_set.union(
                    source_specific_ignores
                )

                log.info(
                    f"Processing local protocol source: {source_name} from base path '{base_path}'"
                )
                if source_specific_ignores:
                    log.debug(
                        f"Source-specific ignores for {source_name}: {', '.join(sorted(source_specific_ignores))}"
                    )
                if current_effective_ignore_set:
                    log.debug(
                        f"Effective ignores for {source_name}: {', '.join(sorted(current_effective_ignore_set))}"
                    )

                actual_search_paths_for_source = [
                    os.path.normpath(os.path.join(base_path, rel_dir))
                    for rel_dir in source_relative_dirs
                ]
                log.debug(
                    f"Scanning directories for {source_name}: {', '.join(actual_search_paths_for_source)}"
                )
                dirs_actually_scanned_log.extend(actual_search_paths_for_source)

                found_files_accumulator.extend(
                    self._scan_directories_for_xml_files(
                        actual_search_paths_for_source,
                        current_effective_ignore_set,
                        source_name_for_logging=source_name,
                    )
                )
                log.debug(
                    f"{len(found_files_accumulator)} total files found so far after processing {source_name}."
                )

        unique_found_files = sorted(set(found_files_accumulator))

        if dirs_actually_scanned_log:
            unique_scanned_dirs = sorted(set(dirs_actually_scanned_log))
            log.info(
                f"Found {len(unique_found_files)} unique XML protocol files after scanning: {', '.join(unique_scanned_dirs)} (all ignore filters applied)."
            )
        else:
            log.info(
                "No directories were scanned (either none provided, none configured, or none found). Found 0 files."
            )

        return unique_found_files

    def to_json(self, *, minimise=True) -> str:
        protocols = deepcopy(self.interfaces)
        if minimise:
            self._remove_keys(protocols, ["description", "signature", "summary"])
        return json.dumps(protocols, indent=1, sort_keys=True)

    @staticmethod
    def _remove_keys(obj: dict | list, keys: list[str]):
        if isinstance(obj, dict):
            for key in keys:
                obj.pop(key, None)
            for value in obj.values():
                WaylandParser._remove_keys(value, keys)
        elif isinstance(obj, list):
            for item in obj:
                WaylandParser._remove_keys(item, keys)

    def _add_interface_item(self, interface: str, item_type: str, item: dict):
        if keyword.iskeyword(item["name"]):
            item["name"] += "_"
            log.info(f"Renamed {self.protocol_name}.{interface}.{item['name']}")

        if interface not in self.interfaces:
            self.interfaces[interface] = {"events": [], "requests": [], "enums": []}

        items = self.interfaces[interface][f"{item_type}s"]
        if item_type != "enum":
            item["opcode"] = len(items)

        if item_type == "event":
            requests = [x["name"] for x in self.interfaces[interface]["requests"]]
            if item["name"] in requests:
                msg = f"Event {item['name']} collides with request of the same name."
                raise ValueError(msg)

        items.append(item)

    def add_request(self, interface: str, request: dict):
        self._add_interface_item(interface, "request", request)

    def add_enum(self, interface: str, enum: dict):
        self._add_interface_item(interface, "enum", enum)

    def add_event(self, interface: str, event: dict):
        self._add_interface_item(interface, "event", event)

    def _process_protocol_element(self, node: etree.Element, interface_name: str):
        """Helper function to process a request, event, or enum node."""
        object_type = node.tag
        object_name = node.attrib["name"]
        log.info(f"    ({object_type}) {interface_name}.{object_name}")

        wayland_object = dict(node.attrib)

        child_tag = "arg" if object_type != "enum" else "entry"
        params = node.findall(child_tag)
        args = self.fix_arguments(
            self._extract_arguments_with_descriptions(params), object_type
        )

        description_node = node.find("description")
        description = self.get_description(description_node)

        signature_args_str = ", ".join(
            f"{x['name']}: {x.get('type', '')}" for x in args
        )
        signature = f"{interface_name}.{object_name}({signature_args_str})"

        wayland_object.update(
            {"args": args, "description": description, "signature": signature}
        )

        getattr(self, f"add_{object_type}")(interface_name, wayland_object)

    def _should_parse_interface(
        self, interface_name: str, current_version: int, current_path: str
    ) -> bool:
        """
        Determines if an interface should be parsed based on its version and whether it's already known.
        Updates self.unique_interfaces_source and self.interfaces accordingly.
        Returns True if the interface should be parsed, False otherwise.
        """
        if interface_name not in self.unique_interfaces_source:
            self.unique_interfaces_source[interface_name] = {
                "version": current_version,
                "path": current_path,
            }
            log.debug(
                f"Registering new interface '{interface_name}' v{current_version} from {current_path}."
            )
            return True

        stored_info = self.unique_interfaces_source[interface_name]
        stored_version = stored_info["version"]  # type: ignore
        stored_path = stored_info["path"]  # type: ignore

        if current_version > stored_version:
            log.info(
                f"Replacing older version {stored_version} of interface '{interface_name}' (from {stored_path}) "
                f"with newer version {current_version} (from {current_path})."
            )
            self.unique_interfaces_source[interface_name] = {
                "version": current_version,
                "path": current_path,
            }
            if (
                interface_name in self.interfaces
            ):  # Clear out old data for this interface
                self.interfaces[interface_name] = {
                    "events": [],
                    "requests": [],
                    "enums": [],
                }
            return True
        if current_version < stored_version:
            log.info(
                f"Ignoring older version {current_version} of interface '{interface_name}' (from {current_path}). "
                f"Already loaded version {stored_version} (from {stored_path})."
            )
            return False
        # current_version == stored_version
        log.warning(
            f"Ignoring duplicate interface definition for '{interface_name}' version {current_version}:\n"
            f"  Attempted to load from: {current_path}\n"
            f"  Already defined in:    {stored_path}"
        )
        return False

    def _get_xml_root(self, path: str) -> etree._Element | None:
        """Loads and parses an XML file from a path or URL, returning the root element."""
        if not path.strip():
            log.warning("Empty path provided to _get_xml_root.")
            return None

        xml_parser = etree.XMLParser(remove_blank_text=True)

        # Determine if it's a URL or local file path and set definition_uri
        if path.startswith(("http://", "https://")):
            self.definition_uri = path  # For http, definition_uri remains the URL
            current_file_path_for_logging = path
        else:
            self.definition_uri = os.path.abspath(path)
            current_file_path_for_logging = self.definition_uri

        try:
            if not os.path.exists(self.definition_uri):
                log.error(f"Protocol file not found: {self.definition_uri}")
                return None
            tree = etree.parse(self.definition_uri, parser=xml_parser)
            return tree.getroot()
        except etree.LxmlError as e:
            log.error(f"Failed to parse XML from {current_file_path_for_logging}: {e}")
            return None
        except OSError as e:
            log.error(
                f"An OS error occurred while processing {current_file_path_for_logging}: {e}"
            )
            return None

    def parse(self, path: str):
        tree_root = self._get_xml_root(path)
        if tree_root is None:
            return

        # self.definition_uri is set by _get_xml_root, use it for logging and tracking
        current_file_path_for_logging = self.definition_uri

        protocol_name_from_xml = tree_root.attrib.get("name", "")
        if not self.protocol_name and protocol_name_from_xml:
            self.protocol_name = protocol_name_from_xml
        elif not protocol_name_from_xml:
            log.warning(
                f"Protocol name attribute not found in root tag of {current_file_path_for_logging}"
            )

        for interface_node in tree_root.xpath("interface"):
            interface_name = interface_node.attrib["name"]
            current_version_str = interface_node.attrib.get("version", "1")
            try:
                current_version = int(current_version_str)
            except ValueError:
                log.warning(
                    f"Invalid version '{current_version_str}' for interface '{interface_name}' "
                    f"in {current_file_path_for_logging}. Defaulting to version 1."
                )
                current_version = 1

            if not self._should_parse_interface(
                interface_name, current_version, current_file_path_for_logging
            ):
                continue

            # Ensure basic structure exists if it's the very first time or after being cleared by _should_parse_interface
            if interface_name not in self.interfaces or not self.interfaces[
                interface_name
            ].get("events"):
                self.interfaces[interface_name] = {
                    "events": [],
                    "requests": [],
                    "enums": [],
                }

            self.interfaces[interface_name]["version"] = current_version
            interface_description_node = interface_node.find("description")
            self.interfaces[interface_name]["description"] = self.get_description(
                interface_description_node
            )

            for child_type_tag in ["request", "event", "enum"]:
                for child_node in interface_node.findall(child_type_tag):
                    self._process_protocol_element(child_node, interface_name)
            log.debug(
                f"Successfully processed interface '{interface_name}' v{current_version} from {current_file_path_for_logging}."
            )

    def format_summary(self, summary):
        return re.sub(r"\b([a-z_]*_[a-z_]*)\b", r"`\1`", summary).strip().capitalize()

    def get_description(self, description: etree.Element) -> str:
        if (
            description is not None
            and hasattr(description, "text")
            and description.text is not None
            and description.text.strip()
        ):
            summary = self.format_summary(description.attrib.get("summary", ""))
            if summary:
                text = textwrap.dedent(description.text).strip()
                text = f"{summary}\n\n{text}"
            else:
                text = textwrap.dedent(description.text).strip()
        elif description is not None and description.attrib.get("summary", "").strip():
            # only have summary
            text = self.format_summary(description.attrib.get("summary", ""))
        else:
            text = ""
        return "\n".join(line.rstrip() for line in text.splitlines())

    def _extract_arguments_with_descriptions(
        self, params: list[etree.Element]
    ) -> list[dict]:
        args = []
        for param in params:
            arg_dict = dict(param.attrib)
            description_node = param.find("description")
            if description_node is not None:
                arg_dict["description"] = self.get_description(description_node)
            elif "summary" in arg_dict:
                arg_dict["description"] = self.format_summary(arg_dict["summary"])
            else:
                arg_dict["description"] = ""
            args.append(arg_dict)
        return args

    def fix_arguments(self, original_args: list[dict], item_type: str) -> list[dict]:
        new_args = []
        for arg in original_args:
            if keyword.iskeyword(arg["name"]):
                arg["name"] += "_"
                log.info(
                    f"Renamed request/event argument to {arg['name']} in protocol {self.protocol_name}"
                )

            if arg.get("type") == "new_id" and not arg.get("interface"):
                if item_type == "event":
                    msg = "Event with dynamic new_id not supported"
                    raise NotImplementedError(msg)
                new_args.extend(
                    [
                        {"name": "interface", "type": "string"},
                        {"name": "version", "type": "uint"},
                    ]
                )

            new_args.append(arg)

        return new_args
