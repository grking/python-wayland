# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import argparse
import json
import sys

from wayland.client.package import get_package_root
from wayland.log import log
from wayland.parser import WaylandParser
from wayland.typehint import TypeHinter


def setup_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process Wayland protocols.")
    parser.add_argument(
        "--no-minimise",
        action="store_false",
        dest="minimise",
        help="Disable protocol file minimisation.",
    )
    parser.add_argument(
        "--download", action="store_true", help="Download latest protocol definitions."
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare local and remote protocol files.",
    )
    return parser


def compare_protocols() -> None:
    local_parser = WaylandParser()
    remote_parser = WaylandParser()

    def get_interfaces(parser: WaylandParser, uris: list) -> dict[str, str]:
        for i, protocol in enumerate(uris, 1):
            log.info(f"Parsing protocol definition {i} of {len(uris)}")
            parser.parse(protocol)
        return {
            interface: details["version"]
            for interface, details in parser.interfaces.items()
        }

    print(
        "Comparing locally installed and latest official protocol definitions. Please wait."
    )

    local_interfaces = get_interfaces(
        local_parser, local_parser.get_local_files() or []
    )
    remote_interfaces = get_interfaces(
        remote_parser, remote_parser.get_remote_uris() or []
    )

    changed = {
        i: (local_interfaces[i], v)
        for i, v in remote_interfaces.items()
        if i in local_interfaces and local_interfaces[i] != v
    }
    only_remote = {
        i: v for i, v in remote_interfaces.items() if i not in local_interfaces
    }
    only_local = {
        i: v for i, v in local_interfaces.items() if i not in remote_interfaces
    }

    print("\nProtocol definitions which have been updated:")
    for interface, (local_v, remote_v) in changed.items():
        print(f"{interface}: local version {local_v}, remote version {remote_v}")

    print("\nAvailable remote protocol definitions, but not installed locally:")
    for interface, version in only_remote.items():
        print(f"{interface}: version {version}")

    print(
        "\nProtocol definitions installed locally but not in official stable or staging repositories:"
    )
    for interface, version in only_local.items():
        print(f"{interface}: version {version}")


def process_protocols(parser: WaylandParser, args: argparse.Namespace) -> None:
    uris = parser.get_local_files() if not args.download else []
    if args.download or not uris:
        uris = parser.get_remote_uris()

    for i, protocol in enumerate(uris, 1):
        log.info(f"Parsing protocol definition {i} of {len(uris)}")
        parser.parse(protocol)

    type_hinter = TypeHinter()
    type_hinter.create_type_hinting(parser.interfaces, get_package_root())
    log.info("Created type hinting file.")

    protocols = parser.to_json(minimise=args.minimise)
    filepath = f"{get_package_root()}/protocols.json"
    with open(filepath, "w", encoding="utf-8") as outfile:
        json.dump(json.loads(protocols), outfile, separators=(",", ":"), indent=1)
    log.info(f"Created protocol database: {filepath}")


def main():
    args = setup_argparser().parse_args()

    if args.verbose:
        log.enable()
        log.info("Starting Wayland protocol update.")

    parser = WaylandParser()

    if args.compare:
        compare_protocols()
        sys.exit(0)

    process_protocols(parser, args)


if __name__ == "__main__":
    main()
