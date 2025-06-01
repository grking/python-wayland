#!/bin/bash
# docker/configs/startup.sh

cd
cp -r /home/user/python-wayland /tmp/python-wayland
cd /tmp/python-wayland

echo "Running python-wayland tests..."
echo "==============================="

# Run tests and capture exit code
hatch test
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo
    echo "✅ All tests passed!"
    echo "Shutting down container in 2 seconds..."
    sleep 2
    # Shutdown sway which will exit the container
    swaymsg exit
else
    echo
    echo "❌ Tests failed with exit code: $TEST_EXIT_CODE"
    echo "Container will remain open for debugging."
    echo
    echo "You can:"
    echo "  - Run 'hatch test' again"
    echo "  - Run 'hatch test -v' for verbose output"
    echo "  - Run 'hatch test tests/specific_test.py' for specific tests"
    echo "  - Run 'hatch shell' to enter the environment"
    echo
    echo "Press Ctrl+D or type 'exit' to close this terminal"
    echo "Type 'swaymsg exit' to shutdown the container"

    # Keep the shell open
    exec bash
fi