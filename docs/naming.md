## Wayland/Python Naming Conflicts

Wayland interfaces use the original Wayland naming convention by default rather than being renamed to a more Pythonic form. This ensures that [Wayland API documentation](https://python-wayland.org/wayland) and other Wayland references remain directly applicable when using this library.

Wayland identifiers that collide with Python builtin keywords are renamed to end with an underscore. There are very few of these. The list of known protocols that have changes are:

* `wayland.wl_registry.global` renamed to `global_`
* `xdg_foreign_unstable_v1.zxdg_importer_v1.import` renamed to `import_`

Enums with integer names, which are not permitted in Python, have the value prefixed with the name of the enum. This is also very rare, at the time of writing the below example is the only case in the stable and staging protocols.

For example:

```python
class wl_output.transform(Enum):
    normal: int
    90: int
    180: int
    270: int
    flipped: int
    flipped_90: int
    flipped_180: int
    flipped_270: int
```

becomes:

```python
class wl_output.transform(Enum):
    normal: int
    transform_90: int
    transform_180: int
    transform_270: int
    flipped: int
    flipped_90: int
    flipped_180: int
    flipped_270: int
```
