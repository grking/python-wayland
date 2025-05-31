"""Generate the Wayland interface reference pages."""

from pathlib import Path

import mkdocs_gen_files

import wayland

WAYLAND_INTERFACES = [x for x in dir(wayland) if x[0] != "_" and x != "client"]

# Generate a page for each interface
for interface in WAYLAND_INTERFACES:
    filename = f"wayland_reference/{interface}.md"

    with mkdocs_gen_files.open(filename, "w") as f:
        print(f"# {interface}\n", file=f)
        print(f"::: wayland.{interface}", file=f)
        print("    options:", file=f)
        print("      show_source: false", file=f)
        print("      show_root_heading: true", file=f)
        print("      show_root_toc_entry: true", file=f)
        print("      members_order: source", file=f)
        print("      heading_level: 2", file=f)

    # Optionally set the edit path for the generated file
    mkdocs_gen_files.set_edit_path(filename, f"wayland/{interface}.py")

# Generate a summary page
with mkdocs_gen_files.open("wayland_reference/index.md", "w") as f:
    print("# Wayland Interface Reference\n", file=f)
    print(
        "This section contains the reference documentation for all Wayland interfaces.\n",
        file=f,
    )

    for interface in sorted(WAYLAND_INTERFACES):
        print(f"- [{interface}]({interface}.md)", file=f)

# Include CHANGELOG.md from project root
changelog_path = Path("CHANGELOG.md")
if changelog_path.exists():
    with open(changelog_path, encoding="utf-8") as f:
        changelog_content = f.read()

    # Create it in the docs
    with mkdocs_gen_files.open("changelog.md", "w") as f:
        f.write(changelog_content)

    # Set edit path to the actual file
    mkdocs_gen_files.set_edit_path("changelog.md", "CHANGELOG.md")
