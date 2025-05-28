# Copyright (c) 2024 Graham R King
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import json
import keyword
import os
import shutil
import subprocess
import tempfile
from copy import deepcopy
from typing import Dict, List, Optional

import requests
from lxml import etree

from wayland.log import log


class WaylandParser:
    def __init__(self):
        self.interfaces: dict[str, dict] = {}
        self.unique_interfaces: list = []
        self.protocol_name: str = ""
        self.definition_uri: str = ""

    def _run(
        self,
        cmd: List[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        check=True,
        stream_output=False,
    ):
        """
        Run a subprocess with common options.

        Args:
            cmd: Command to run as a list of strings
            cwd: Working directory
            env: Environment variables
            check: Whether to check the return code
            stream_output: Whether to stream output to terminal in real-time

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If the process returns non-zero exit status and check=True
        """
        # Set stdout/stderr based on stream_output parameter
        if stream_output:
            stdout = None  # Use parent process's stdout
            stderr = None  # Use parent process's stderr
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE

        log.info(" ".join(cmd))

        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env or os.environ.copy(),
            check=check,
            stdout=stdout,
            stderr=stderr,
            text=True,
        )
        return result

    def clone_git_repo(
        self, repo_url: str, dest_dir: str = "/tmp/", *, delete_existing=False,
    ) -> bool:
        """
        Clone or update a repository.

        Args:
            repo_url: URL of the repository to clone

        Returns:
            str: The absolute path of the local repository. Or None on error
        """
        # Extract repo name from URL
        repo_name = os.path.basename(repo_url)
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        # Calculate target directory
        target_dir = os.path.join(dest_dir, repo_name)

        # Start with status message
        log.info(f"Cloning {repo_name} into {target_dir}")

        if os.path.isdir(target_dir):
            if delete_existing:
                log.info("Removing existing repo")
                shutil.rmtree(target_dir)
            # Update existing repository
            log.info("Updating exist repo")
            self._run(
                ["git", "pull", "--quiet"], cwd=target_dir
            )
            return target_dir

        # Clone new repository
        self._run(["git", "clone", repo_url, target_dir])

        return target_dir

    def get_remote_uris(self) -> list[str]:
        wayland_repo = "https://gitlab.freedesktop.org/wayland/wayland.git"
        wayland_protocols_repo = "https://gitlab.freedesktop.org/wayland/wayland-protocols.git"
        paths = ["staging", "stable", "unstable"]

        temp_dir = tempfile.gettempdir()

        # Clone the wayland repo to get the main protocol definition
        # TODO support --force
        local_wayland_dir = self.clone_git_repo(wayland_repo, temp_dir, delete_existing=False)
        if not local_wayland_dir:
            raise Exception("Unable to clone the wayland git repository")

        # Clone the wayland protocol repo
        # TODO support --force
        local_dir = self.clone_git_repo(wayland_protocols_repo, temp_dir, delete_existing=False)
        if not local_dir:
            raise Exception("Unable to clone the wayland protocol git repository")

        search_paths = [os.path.join(local_dir, x) for x in paths]
        search_paths.append(os.path.join(local_wayland_dir, "protocol"))
        repo_files = self.get_local_files(search_paths)
        log.info(f"Found files {repo_files} in {search_paths}")
        return repo_files

    def get_local_files(self, search_path=None) -> list[str]:
        if not search_path:
            protocol_dirs = ["/usr/share/wayland", "/usr/share/wayland-protocols"]
        else:
            if isinstance(search_path, str):
                protocol_dirs = [search_path]
            else:
                protocol_dirs = search_path

        log.info(f"Loading wayland protocol definitions from {', '.join(protocol_dirs)}")
        return [
            os.path.join(root, file)
            for directory in protocol_dirs
            for root, _, files in os.walk(directory)
            for file in files
            if file.endswith(".xml")
        ]

    def to_json(self, *, minimise=True) -> str:
        protocols = deepcopy(self.interfaces)
        if minimise:
            self._remove_keys(protocols, ["description", "signature", "summary"])
        return json.dumps(protocols, indent=1)

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

        # Arguments or entries
        child_tag = "arg" if object_type != "enum" else "entry"
        params = node.findall(child_tag)
        args = self.fix_arguments([dict(x.attrib) for x in params], object_type)

        description_node = node.find("description")
        description = self.get_description(description_node)

        signature_args_str = ', '.join(f'{x["name"]}: {x.get("type","")}' for x in args)
        signature = f"{interface_name}.{object_name}({signature_args_str})"

        wayland_object.update(
            {"args": args, "description": description, "signature": signature}
        )

        # This uses self.add_request, self.add_event, self.add_enum
        getattr(self, f"add_{object_type}")(interface_name, wayland_object)

    def parse(self, path: str):
        if not path.strip():
            return
        self.definition_uri = path
        xml_parser = etree.XMLParser(remove_blank_text=True)

        if path.startswith("http"):
            response = requests.get(path, timeout=20)
            response.raise_for_status()
            xml_content = response.content
            tree_root = etree.fromstring(xml_content, parser=xml_parser)
        else:
            tree = etree.parse(path, parser=xml_parser)
            tree_root = tree.getroot()

        # Protocol name from the root <protocol> element
        self.protocol_name = tree_root.attrib.get("name", "")
        if not self.protocol_name:
            log.warning(f"Protocol name not found in {path}")

        # Iterate over <interface> elements
        for interface_node in tree_root.xpath("interface"):
            interface_name = interface_node.attrib["name"]

            # Check if this interface has already been processed (e.g. from another file)
            if interface_name in self.unique_interfaces:
                log.warning(
                    f"Ignoring duplicate interface definition for {interface_name} "
                    f"(already processed) in {self.definition_uri}"
                )
                continue

            # Initialize interface structure if it's new, and set/update its version and description
            # The _add_interface_item method (called by add_request etc) will create the basic lists if needed.
            if interface_name not in self.interfaces:
                self.interfaces[interface_name] = {"events": [], "requests": [], "enums": []}

            self.interfaces[interface_name]["version"] = interface_node.attrib.get("version", "1")
            interface_description_node = interface_node.find("description")
            self.interfaces[interface_name]["description"] = self.get_description(interface_description_node)

            # Process requests, events, and enums for this interface
            for child_type_tag in ["request", "event", "enum"]:
                for child_node in interface_node.findall(child_type_tag):
                    self._process_protocol_element(child_node, interface_name)

            # Mark this interface as processed
            self.unique_interfaces.append(interface_name)

    @staticmethod
    def get_description(description: etree.Element) -> str:
        if description is None:
            return ""
        summary = description.attrib.get("summary", "").strip()
        text = "\n".join(
            line.strip()
            for line in (description.text or "").split("\n")
            if line.strip()
        )
        return f"{summary}\n{text}" if text else summary

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
