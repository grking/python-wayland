# API Documentation

The basic purpose of `python-wayland` is to provide an implementation of the Wayland protocol and allow interaction with Wayland objects.

This section documents the additional functionality that `python-wayland` provides, functionality that is not part of the low-level Wayland protocol. This functionality falls into two categories:

1. Helper or convenience functions to assist using the library.
1. Semi-internal functions which assist whilst developing the library.

There is almost certainly nothing of interest here currently. It is planned that additional helper functionality be added to the library to assist with actually creating GUI applications, at least, assist with the setup process to create actual windows and surfaces so a GUI could be painted by the client application.