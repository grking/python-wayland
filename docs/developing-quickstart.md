# Developing Quick Start

`python-wayland` has been configured with `hatch`.

## Installing Hatch

You can install `hatch` through `pipx`. A full bootstrap may look like:

```bash
# Install pipx
sudo apt-get install pipx  # debian / ubuntu
sudo pacman -S python-pipx  # arch

# Install hatch with pipx
pipx install hatch
```

## Building and Testing

* Run the tests with `hatch test`
* Run lint check with `hatch fmt`

## Generating Documentation

* Build the docs with `hatch run docs:build`
* Serve the docs locally with `hatch run docs:serve`

The documentation is automatically produced using [MkDocs](https://www.mkdocs.org/).

## Updating Wayland Protocol Definitions

The latest Wayland protocols are already packaged in `python-wayland`, see (`wayland/protocols.json`). Refreshing the protocol definitions is optional. It requires the python library `lxml` to be installed.

To download and update the protocol definitions directly from the official git repositories of the protocol sources:

```bash
hatch run wayland:update
```

To rebuild the Wayland protocols from the versions installed on the local operating system:

```bash
hatch run wayland:update-local
```
