import os
import tempfile
from pathlib import Path

import pytest

from tests.mock_server import MockServer


@pytest.fixture(autouse=True)
def reset_wayland_state():
    """Reset all Wayland-related state between tests."""
    import wayland
    from wayland.baseobject import WaylandObject
    from wayland.proxy import Proxy
    from wayland.state import WaylandState

    # Disconnect if a connection from a previous (failed) test exists.
    # We need to do this before resetting the singletons.
    try:
        proxy = Proxy()
        if proxy.state.connected:
            proxy.state.disconnect()
    except Exception:  # noqa: BLE001
        pass

    # Reset the singletons to ensure a clean slate for each test.
    Proxy._instance = None
    Proxy._initialised = False
    Proxy._event_queues.clear()
    WaylandState._instance = None
    WaylandState._initialised = False

    # Purge the dynamically created classes from the wayland module.
    # This is necessary so that they can be recreated with the new Proxy instance.
    for name, value in list(wayland.__dict__.items()):
        if (
            isinstance(value, type)
            and issubclass(value, WaylandObject)
            and value is not WaylandObject
            and name in wayland.__dict__
        ):
            del wayland.__dict__[name]

    # Re-initialize the wayland module by creating a new proxy and running its initializer.
    # This will populate the wayland module with fresh dynamic classes.
    new_proxy = Proxy()
    new_proxy.initialise(wayland.__dict__)

    yield

    # After the test, disconnect to clean up resources.
    try:
        proxy = Proxy()
        if proxy.state.connected:
            proxy.state.disconnect()
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture
def wayland_server():
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = Path(tmpdir) / "wayland-0"

        # Set environment variables for the client to connect to the mock server
        original_wayland_display = os.environ.get("WAYLAND_DISPLAY")
        original_xdg_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        original_debug_socket = os.environ.get("PYTHON_WAYLAND_DEBUG_SOCKET")

        os.environ["WAYLAND_DISPLAY"] = "wayland-0"
        os.environ["XDG_RUNTIME_DIR"] = tmpdir
        os.environ["PYTHON_WAYLAND_DEBUG_SOCKET"] = "python-wayland-test-socket"

        server = MockServer(str(sock_path))
        server.start()

        # Wait for the socket file to be created
        import time

        timeout = 5.0
        start_time = time.time()
        while not sock_path.exists():
            if time.time() - start_time > timeout:
                msg = "Mock server failed to create socket within timeout"
                raise RuntimeError(msg)
            time.sleep(0.01)

        yield server

        server.stop()

        # Restore original environment variables
        if original_wayland_display is not None:
            os.environ["WAYLAND_DISPLAY"] = original_wayland_display
        else:
            os.environ.pop("WAYLAND_DISPLAY", None)

        if original_xdg_runtime_dir is not None:
            os.environ["XDG_RUNTIME_DIR"] = original_xdg_runtime_dir
        else:
            os.environ.pop("XDG_RUNTIME_DIR", None)

        if original_debug_socket is not None:
            os.environ["PYTHON_WAYLAND_DEBUG_SOCKET"] = original_debug_socket
        else:
            os.environ.pop("PYTHON_WAYLAND_DEBUG_SOCKET", None)
