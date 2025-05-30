# Documentation Setup

This directory contains the MkDocs-based documentation for the python-wayland client API.

## Local Development

To work with the documentation locally:

```bash
# Install documentation dependencies
hatch run docs:build

# Serve documentation with hot reload
hatch run docs:serve

# Build static documentation
hatch run docs:build
```

## Structure

- `index.md` - Homepage and overview
- `getting-started.md` - Installation and basic usage guide
- `api/client.md` - Auto-generated API reference
- `examples.md` - Practical usage examples

## Auto-generated Content

The API reference is automatically generated from docstrings using mkdocstrings.

When you add new functions to `wayland.client`, they will automatically appear in the documentation as long as they have proper docstrings.

## Deployment

Documentation is automatically built and deployed to GitHub Pages when changes are pushed to the main branch via GitHub Actions.