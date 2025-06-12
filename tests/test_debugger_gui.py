import pytest

import wayland
from wayland.client import wayland_class
from wayland.client.debug.gui import DebuggerClient


@pytest.mark.asyncio
async def test_gui_navigation_and_render(wayland_server):
    global_event_received = 0

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal global_event_received
            global_event_received += 1

    wayland.client.start_debug_server()

    display = wayland.wl_display()
    registry = display.get_registry()

    request = wayland_server.get_request(timeout=1)
    assert request["object_id"] == 1
    assert request["opcode"] == 1

    gui = DebuggerClient(socket_name="python-wayland-test-socket")
    async with gui.run_test(size=(120, 24)) as pilot:
        await pilot.pause(0.5)
        wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 9)
        wayland_server.send_global_event(
            registry.object_id, 2, "wl_data_device_manager", 3
        )
        wayland_server.send_global_event(registry.object_id, 3, "wl_compositor", 6)
        wayland_server.send_global_event(registry.object_id, 4, "wl_subcompositor", 1)
        wayland_server.send_global_event(registry.object_id, 5, "wl_shm", 1)
        wayland_server.send_global_event(registry.object_id, 6, "wp_viewporter", 1)
        wayland_server.send_global_event(
            registry.object_id, 7, "wp_tearing_control_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 8, "wp_fractional_scale_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 9, "zxdg_output_manager_v1", 3
        )
        wayland_server.send_global_event(
            registry.object_id, 10, "wp_cursor_shape_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 11, "zwp_idle_inhibit_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 12, "zwp_relative_pointer_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 13, "zxdg_decoration_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 14, "wp_alpha_modifier_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 15, "zwlr_gamma_control_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 16, "ext_foreign_toplevel_list_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 17, "zwp_pointer_gestures_v1", 3
        )
        wayland_server.send_global_event(
            registry.object_id, 18, "zwlr_foreign_toplevel_manager_v1", 3
        )
        wayland_server.send_global_event(
            registry.object_id, 19, "zwp_keyboard_shortcuts_inhibit_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 20, "zwp_text_input_manager_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 21, "zwp_text_input_manager_v3", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 22, "zwp_pointer_constraints_v1", 1
        )
        wayland_server.send_global_event(
            registry.object_id, 23, "zwlr_output_power_manager_v1", 1
        )
        wayland_server.send_global_event(registry.object_id, 24, "xdg_activation_v1", 1)

        await pilot.pause(0.5)
        display.dispatch_timeout(1)

        await pilot.pause()
        await pilot.wait_for_scheduled_animations()
        await pilot.pause()

        assert global_event_received == 24

        await pilot.press("ctrl+end")
        await pilot.wait_for_scheduled_animations()
        await pilot.pause()

        dt = pilot.app.query_one("#messages")
        assert dt is not None
        svg = pilot.app.export_screenshot(simplify=True)
        assert "xdg_activation_v1" in svg

        await pilot.press("ctrl+home")
        await pilot.wait_for_scheduled_animations()
        await pilot.pause()
        svg = pilot.app.export_screenshot(simplify=True)
        # pilot.app.save_screenshot("screenshot.svg")
        assert "wl_seat" in svg

        await pilot.app.client.get_message_by_key(1)
        await pilot.pause(0.5)


@pytest.mark.asyncio
async def test_debug_commands(wayland_server):
    wayland.client.start_debug_server()

    display = wayland.wl_display()
    display.get_registry()
    request = wayland_server.get_request(timeout=1)
    assert request["object_id"] == 1
    assert request["opcode"] == 1

    gui = DebuggerClient(socket_name="python-wayland-test-socket")
    async with gui.run_test(size=(120, 24)) as pilot:
        await pilot.pause()
        await pilot.app.client.send_text("help")
        await pilot.app.client.send_text("help summary")
        await pilot.app.client.send_text("help get")
        await pilot.app.client.send_text("help stream")
        await pilot.app.client.send_text("help quit")
        await pilot.app.client.send_text("help does-not-exist")
        await pilot.pause(0.5)
        await pilot.app.client.send_text("get_msg 1")
        await pilot.pause(0.5)
