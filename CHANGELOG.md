# Changelog

## DEVELOPMENT VERSION

> [!WARNING]
> The development version is in the middle of significant redesign and refactor.

This version replaces the previous experiments with a more formal Wayland class library and stable API. It introduces a more typical design pattern and behaviour, with more explicit and predictable Pythonic usage and less implicit magic.

### Major Changes

* Now exposes a Wayland class library (rather than a library of magic instances).

- Introduces a Wayland protocol debugger. A terminal application providing a TUI to intercept and analyse Wayland protocol messages between your application and the Wayland compositor.
- Comprehensive [online documentation](https://python-wayland.org) is now available.

### Other API Changes
- All non-Wayland protocol APIs are now in `wayland.client`
- `wayland.process_messages()` removed. Use dispatch*
- `wayland.initialise()` replaced with `wayland.client.get_wayland_proxy()`
- `wayland.get_package_root()` replaced with `wayland.client.package.get_package_root()`
- `wayland.is_wayland` replaced with `wayland.client.is_wayland()`
- Event dispatching is now a similar pattern to `libwayland-client`, using dispatch and dispatch_pending for blocking and non-blocking event dispatching.
- [`wayland.wl_display.dispatch()`](https://python-wayland.org/wayland/wl_display/#wayland.wl_display.dispatch) added.
- [`wayland.wl_display.dispatch_timeout()`](https://python-wayland.org/wayland/wl_display/#wayland.wl_display.dispatch_timeout) added.
- [`wayland.wl_display.dispatch_pending()`](https://python-wayland.org/wayland/wl_display/#wayland.wl_display.dispatch_pending) added.

### General Changes
- No connection is made to the Wayland compositor until either explicitly requested or a method that sends a Wayland message is used.
- Internal Wayland event processing has been improved. There are now multiple event queues with automatic creation of per-thread queues.
- Type hinting now uses the correct `python-wayland` types.
- Type hinting uses less magic to increase compatibility with IDEs.
- Type hint docs cleaned up with better formatting.
- Type hints now have argument descriptions included.

### Fixed
- `array` types in events are now correctly parsed into Python lists.
- Importing the package has consistent behaviour on Wayland and non-Wayland systems.
- Fixed type hints where enums had the wrong type when passed as an argument to a request.
- Fixed protocol error when parsing some unicode characters in strings.

## v0.7.1 (28th May 2025)
- Remove dependency on requests library.
- Lint fixes for unit tests.

## v0.7.0 (28th May 2025)
- Include Wayland unstable protocols definitions.
- Include Hyprland protocol extensions.
- Include wlroots protocol extensions.
- Update to latest Wayland protocol definitions.
- Include the highest version number definition of any particular interface.
- Auto detect if running under wayland.
- Use git to fetch Wayland protocol definitions, not some local hack.
- Sort the keys in the protocols.json file to make the diffs less painful.

## v0.6.0 (3rd September 2024)
- Support Wayland enums as Python enums including bitfields.
- Change terminology of "methods" to "requests" to match Wayland.

## v0.5.0 (31st August 2024)
- Support multiple wayland contexts not just a single global context.
- Support debug output without full protocol level debugging output.
- Fix for rapid events passing file descriptors
- Slightly extended unit tests.

## v0.4.1 (28th August 2024)
- Fix pypi package build.

## v0.4.0 (27th August 2024)
- Renamed to python-wayland

## v0.3.0 (26th August 2024)
- File descriptors received in events are now not implicitly converted to Python file objects.
- Add --verbose command line switch for more output when updating protocol files.
- Add --compare option to compare locally installed and latest official protocol definitions.
- Add interface version and description to type checking / intellisense file.
- Add interface version to protocols.json runtime file.

## v0.2.0 (22nd August 2024)
- Improve low-level socket handling.
- Add support for file descriptors in events.
- Add support for Wayland enum data type.
- Add support for Wayland "fixed" floating point types.
- Search for Wayland protocol definitions online and locally.

## v0.1.0 (17th August 2024)
- Initial commit.
