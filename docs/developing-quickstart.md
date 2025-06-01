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

* Build and serve the docs locally: `hatch run docs:serve`
* Build the docs locally: `hatch run docs:build`

The documentation is automatically produced using [MkDocs](https://www.mkdocs.org/).

## Docker Containers

* Run unit tests in Sway `hatch run docker-sway`
* Run unit tests in Weston `hatch run docker-weston`

* Stop all docker containers `hatch run docker-stop`

* Sway container shell `hatch run docker-sway-shell`
* Weston container shell `hatch run docker-sway-shell`

* Build all images `hatch run docker-build`

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
