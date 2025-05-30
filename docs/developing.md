# Developing `python-wayland`

This section covers the development of the `python-wayland` library itself, rather than using the library.

## Quick Start

`python-wayland` has been configured with `hatch`.

### Installing Hatch

You can install `hatch` through `pipx`. A full bootstrap may look like:

```bash
# Install pipx
sudo apt-get install pipx  # debian / ubuntu
sudo pacman -S python-pipx  # arch

# Install hatch with pipx
pipx install hatch
```

### Building and Testing

* Run the tests with `hatch test`
* Run lint check with `hatch fmt`

### Generating Documentation

* Build the docs with `hatch run docs:build`
* Serve the docs locally with `hatch run docs:serve`

The API reference is automatically generated from docstrings using `mkdocstrings`.

When you add new functions to `wayland.client`, they will automatically appear in the documentation as long as they have proper docstrings. Only `wayland.client.*` is included in the docs.

## Updating Wayland Protocol Definitions

The latest Wayland protocols are already packaged in `python-wayland`, see (`wayland/protocols.json`). Refreshing the protocol definitions is optional. It requires the python library `lxml` to be installed.

To download and update the protocols definitions directly from the online sources:

```bash
hatch run wayland:update
```

To rebuild the Wayland protocols from the versions globally installed on the local operating system:

```bash
hatch run wayland:update-local
```
