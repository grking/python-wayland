The following changes have been made to:

* Clean up the top-level `wayland` namespace so it contains only the expected wayland protocol methods.
* Allow additional library functionality to be added without further pollution of the `wayland` namespace.
* Remove unnecessary runtime monkey patching to allow IDEs a chance at correctly discovering `python-wayland`'s own API.
* Allow more sensible documentation of the `python-wayland` API.

Methods and attributes in the top-level package namespace `wayland` that were not wayland protocol related have been moved to `wayland.client`.

`wayland.client` now contains any and all functionality introduced by the `python-wayland` library, leaving the top level `wayland` namespace as a pure wayland protocol namespace.

Removed method:

* `wayland.process_messages()` this method has been removed. Event polling and dispatching is now handled automatically. As a library user you don't need to be concerned with this. Events will be dispatched to your registered event handlers as they arrive.

Other than cleaning up junk from the `wayland` namespace this changes the following methods (none of which are required in the normal use of this library):

* `wayland.initialise()` becomes `wayland.client.initialise()`
* `wayland.get_package_root()` becomes `wayland.client.get_package_root()`
* `wayland.is_wayland` becomes `wayland.client.is_wayland()` (note it became a function)
