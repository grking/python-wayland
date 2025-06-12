# Wayland Protocol and Model of Operation

An extract from https://wayland.freedesktop.org/docs/html/ch04.html

## Basic Principles

The Wayland protocol is an asynchronous object oriented protocol. All requests are method invocations on some object. The requests include an object ID that uniquely identifies an object on the server. Each object implements an interface and the requests include an opcode that identifies which method in the interface to invoke.

The protocol is message-based. A message sent by a client to the server is called request. A message from the server to a client is called event. A message has a number of arguments, each of which has a certain type (see the section called "Wire Format" for a list of argument types).

Additionally, the protocol can specify enums which associate names to specific numeric enumeration values. These are primarily just descriptive in nature: at the wire format level enums are just integers. But they also serve a secondary purpose to enhance type safety or otherwise add context for use in language bindings or other such code. This latter usage is only supported so long as code written before these attributes were introduced still works after; in other words, adding an enum should not break API, otherwise it puts backwards compatibility at risk.

Enums can be defined as just a set of integers, or as bitfields. This is specified via the bitfield boolean attribute in the enum definition. If this attribute is true, the enum is intended to be accessed primarily using bitwise operations, for example when arbitrarily many choices of the enum can be ORed together; if it is false, or the attribute is omitted, then the enum arguments are a just a sequence of numerical values.

The enum attribute can be used on either uint or int arguments, however if the enum is defined as a bitfield, it can only be used on uint args.

The server sends back events to the client, each event is emitted from an object. Events can be error conditions. The event includes the object ID and the event opcode, from which the client can determine the type of event. Events are generated both in response to requests (in which case the request and the event constitutes a round trip) or spontaneously when the server state changes.

**Key Points:**
- State is broadcast on connect, events are sent out when state changes. Clients must listen for these changes and cache the state. There is no need (or mechanism) to query server state.
- The server will broadcast the presence of a number of global objects, which in turn will broadcast their current state.

## Code Generation

The interfaces, requests and events are defined in `protocol/wayland.xml`. This xml is used to generate the function prototypes that can be used by clients and compositors.

The protocol entry points are generated as inline functions which just wrap the `wl_proxy_*` functions. The inline functions aren't part of the library ABI and language bindings should generate their own stubs for the protocol entry points from the xml.

## Wire Format

The protocol is sent over a UNIX domain stream socket, where the endpoint usually is named `wayland-0` (although it can be changed via `WAYLAND_DISPLAY` in the environment). Beginning in Wayland 1.15, implementations can optionally support server socket endpoints located at arbitrary locations in the filesystem by setting `WAYLAND_DISPLAY` to the absolute path at which the server endpoint listens.

Every message is structured as 32-bit words; values are represented in the host's byte-order. The message header has 2 words in it:

- The first word is the sender's object ID (32-bit).
- The second has 2 parts of 16-bit. The upper 16-bits are the message size in bytes, starting at the header (i.e. it has a minimum value of 8). The lower is the request/event opcode.

The payload describes the request/event arguments. Every argument is always aligned to 32-bits. Where padding is required, the value of padding bytes is undefined. There is no prefix that describes the type, but it is inferred implicitly from the xml specification.

### Argument Types

The representation of argument types are as follows:

**int, uint**
- The value is the 32-bit value of the signed/unsigned int.

**fixed**
- Signed 24.8 decimal numbers. It is a signed decimal type which offers a sign bit, 23 bits of integer precision and 8 bits of decimal precision. This is exposed as an opaque struct with conversion helpers to and from double and int on the C API side.

**string**
- Starts with an unsigned 32-bit length (including null terminator), followed by the string contents, including terminating null byte, then padding to a 32-bit boundary. A null value is represented with a length of 0.

**object**
- 32-bit object ID. A null value is represented with an ID of 0.

**new_id**
- The 32-bit object ID. Generally, the interface used for the new object is inferred from the xml, but in the case where it's not specified, a new_id is preceded by a string specifying the interface name, and a uint specifying the version.

**array**
- Starts with 32-bit array size in bytes, followed by the array contents verbatim, and finally padding to a 32-bit boundary.

**fd**
- The file descriptor is not stored in the message buffer, but in the ancillary data of the UNIX domain socket message (`msg_control`).

### File Descriptor Handling

The protocol does not specify the exact position of the ancillary data in the stream, except that the order of file descriptors is the same as the order of messages and fd arguments within messages on the wire.

In particular, it means that any byte of the stream, even the message header, may carry the ancillary data with file descriptors.

Clients and compositors should queue incoming data until they have whole messages to process, as file descriptors may arrive earlier or later than the corresponding data bytes.