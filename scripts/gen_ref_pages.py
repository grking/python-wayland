"""Generate the Wayland interface reference pages."""

from pathlib import Path

import mkdocs_gen_files

import wayland

WAYLAND_INTERFACES = [x for x in dir(wayland) if x[0] != "_" and x != "client"]

WAYLAND_CORE = [
    "wl_display",
    "wl_registry",
    "wl_callback",
    "wl_compositor",
    "wl_shm_pool",
    "wl_shm",
    "wl_buffer",
    "wl_data_offer",
    "wl_data_source",
    "wl_data_device",
    "wl_data_device_manager",
    "wl_shell",
    "wl_shell_surface",
    "wl_surface",
    "wl_seat",
    "wl_pointer",
    "wl_keyboard",
    "wl_touch",
    "wl_output",
    "wl_region",
    "wl_subcompositor",
    "wl_subsurface",
    "wl_fixes",
]

# Generate a page for each interface
for interface in WAYLAND_INTERFACES:
    filename = f"wayland/{interface}.md"

    with mkdocs_gen_files.open(filename, "w") as f:
        print(f"# {interface}\n", file=f)
        print(f"::: wayland.{interface}", file=f)
        print("    options:", file=f)
        print("      show_source: false", file=f)
        print("      show_root_heading: true", file=f)
        print("      show_root_toc_entry: true", file=f)
        print("      members_order: source", file=f)
        print("      heading_level: 2", file=f)

nav = []

# Generate a summary page
with mkdocs_gen_files.open("wayland/index.md", "w") as f:
    print("# Wayland Interface Reference\n", file=f)
    print(
        "This section contains the reference documentation for all Wayland interfaces.\n",
        file=f,
    )

    # Sort interfaces: core interfaces first (in order), then others alphabetically
    core_interfaces = [i for i in WAYLAND_CORE if i in WAYLAND_INTERFACES]
    other_interfaces = sorted([i for i in WAYLAND_INTERFACES if i not in WAYLAND_CORE])
    sorted_interfaces = core_interfaces + other_interfaces

    for interface in sorted_interfaces:
        nav_item = f"- [{interface}]({interface}.md)"
        nav.append(nav_item + "\n")
        print(nav_item, file=f)

with mkdocs_gen_files.open("wayland/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav)

# Include CHANGELOG.md from project root
changelog_path = Path("CHANGELOG.md")
if changelog_path.exists():
    with open(changelog_path, encoding="utf-8") as f:
        changelog_content = f.read()

    # Create it in the docs
    with mkdocs_gen_files.open("changelog.md", "w") as f:
        f.write(changelog_content)
