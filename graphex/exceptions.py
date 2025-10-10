import typing
import json
import re


class GraphexException(Exception):
    """Base class for all Graphex exceptions."""

    pass


class GraphValidationError(GraphexException):
    """
    Raised when a graph fails to validate.

    :param graph_name: The graph name.
    :message: The message.
    """

    def __init__(self, graph_name: typing.Optional[str], message: str):
        if graph_name:
            super().__init__(f"Graph {graph_name} failed to validate: {message}")
        else:
            super().__init__(f"Graph failed to validate: {message}")


class NodeUsageError(GraphexException):
    """
    Raised when a node is used incorrectly in a graph file.

    :param node: The node name.
    :param id: The node instance ID.
    :message: The message
    """

    def __init__(self, node_name: str, id: str, message: str):
        super().__init__(f"Node '{node_name}' ({id}): {message}")


class NodeMisalignedSockets(NodeUsageError):
    """
    Raised when a node's defined sockets are misaligned with it's instance sockets (sockets provided in the graph file).

    :param node: The node name.
    :param id: The node instance ID.
    :param defined_sockets: The actual (defined) sockets on the node.
    :param provided_sockets: The sockets that were provided on the instance.
    :param is_input: Whether the sockets in question are input sockets (otherwise, they are output sockets).
    """

    def __init__(
        self,
        node_name: str,
        id: str,
        defined_sockets: typing.List[str],
        provided_sockets: typing.List[str],
        is_input: bool = True,
    ):
        socket_type = "input" if is_input else "output"
        super().__init__(
            node_name=node_name,
            id=id,
            message=f"Misaligned {socket_type} sockets. Required: {','.join(defined_sockets)}; Provided: {','.join(provided_sockets)}",
        )


class SocketError(GraphexException):
    """
    Generic socket error.

    :param socket_name: The name of the socket.
    :param node_name: The name of the node containing this socket.
    :param id: The ID of the node instance.
    :param msg: The error message.
    """

    def __init__(self, socket_name: str, node_name: str, id: str, msg: str):
        super().__init__(
            f"Error for socket '{socket_name}' on node {node_name} ({id}): {msg}"
        )


class SocketMissingConnection(SocketError):
    """
    Raised when a socket is missing a required connection.

    :param socket_name: The name of the socket.
    :param node_name: The name of the node containing this socket.
    :param id: The ID of the node instance.
    :param num_current_connections: The number of connections on this socket.
    :param num_required_connections: The number of connections required on this socket.
    """

    def __init__(
        self,
        socket_name: str,
        node_name: str,
        id: str,
        num_current_connections: int,
        num_required_connections: int,
    ):
        super().__init__(
            socket_name=socket_name,
            node_name=node_name,
            id=id,
            msg=f"{num_current_connections} connections present when {num_required_connections} required",
        )


class SocketTooManyConnections(SocketError):
    """
    Raised when a socket has too many connections.

    :param socket_name: The name of the socket.
    :param node_name: The name of the node containing this socket.
    :param id: The ID of the node instance.
    :param num_current_connections: The number of connections on this socket.
    :param num_maximum_connections: The maximum number of connections on this socket.
    """

    def __init__(
        self,
        socket_name: str,
        node_name: str,
        id: str,
        num_current_connections: int,
        num_maximum_connections: int,
    ):
        super().__init__(
            socket_name=socket_name,
            node_name=node_name,
            id=id,
            msg=f"{num_current_connections} connections present when a maximum of {num_maximum_connections} can exist",
        )


class SocketInvalidDataType(SocketError):
    """
    Raised when socket is connected to another socket and the data types are incompatible.

    :param socket_name: The name of the socket.
    :param node_name: The name of the node containing this socket.
    :param id: The ID of the node instance.
    :param other_socket_name: The name of the socket on the other end of the connection.
        :param other_node_name: The name of the node on the other end of the connection.
    :param other_id: The ID of the node instance on the other end of the connection.
    :param datatype: The name of the datatype.
    :param other_datatype: The name of the datatype on the other end of the connection.
    """

    def __init__(
        self,
        socket_name: str,
        node_name: str,
        id: str,
        other_socket_name: str,
        other_node_name: str,
        other_id: str,
        datatype: str,
        other_datatype: str,
    ):
        super().__init__(
            socket_name=socket_name,
            node_name=node_name,
            id=id,
            msg=f"carries an invalid datatype to socket '{other_socket_name}' on node {other_node_name} ({other_id}) ({datatype} versus {other_datatype})",
        )


class SocketInvalidConnectionType(SocketError):
    """
    Raised when socket is connected to another socket and the connection type is incompatible.

    :param socket_name: The name of the socket.
    :param node_name: The name of the node containing this socket.
    :param id: The ID of the node instance.
    :param other_socket_name: The name of the socket on the other end of the connection.
        :param other_node_name: The name of the node on the other end of the connection.
    :param other_id: The ID of the node instance on the other end of the connection.
    :param msg: The error message.
    """

    def __init__(
        self,
        socket_name: str,
        node_name: str,
        id: str,
        other_socket_name: str,
        other_node_name: str,
        other_id: str,
        msg: str,
    ):
        super().__init__(
            socket_name=socket_name,
            node_name=node_name,
            id=id,
            msg=f"invalid connection to '{other_socket_name}' on node {other_node_name} ({other_id}) ({msg})",
        )


class InvalidParameterError(GraphexException):
    """
    Raised when a value is provided to an action node that isn't allowed.

    :param node_name: The name of the node throwing the error.
    :param socket_name: The name of the socket that has an invalid input.
    :param invalid_param: The invalid parameter for the socket.
    :param valid_params: A printable example of what the valid parameters are / should be.
    """

    def __init__(
        self, node_name: str, socket_name: str, invalid_param: str, valid_params
    ):
        msg: str = (
            f"Node: '{node_name}' received an invalid parameter: '{invalid_param}' ... on socket: '{socket_name}'. Valid inputs are: '{str(valid_params)}'"
        )
        super().__init__(msg)


class StringFormattingError(GraphexException):
    """
    Raised when a string value isn't in the format requested by the node.

    :param node_name: The name of the node throwing the error.
    :param socket_name: The name of the socket that has an invalid input.
    :param poorly_formatted_param: The param that is incorrect.
    :param valid_formatting: An example of what the valid formatting is / should be.
    """

    def __init__(
        self,
        node_name: str,
        socket_name: str,
        poorly_formatted_param: str,
        valid_formatting: str,
    ):
        msg: str = (
            f"Node: '{node_name}' has a formatting error. String: '{poorly_formatted_param}' ... on socket: '{socket_name}'. The string should be formatted based on the following rule: '{valid_formatting}'"
        )
        super().__init__(msg)


class LoopBreakException(GraphexException):
    """
    An exception raised when a node requests to break out of a loop early. This is a not a 'real' exception but instead a method used to signal to the parent loop to exit early.
    """

    pass


class LoopContinueException(GraphexException):
    """
    An exception raised when a node requests to 'continue' a loop. This is a not a 'real' exception but instead a method used to signal to the parent loop to continue to the next iteration.
    """

    pass


class ReservedAttributeException(GraphexException):
    """
    Raised when a plugin uses an attribute that is a reserved keyword by plugins.

    :param assertion_error: The error for the reserved keyword that is of the wrong type
    """

    def __init__(self, assertion_error: str):
        msg: str = (
            f"Plugin node used keyword that has reserved usage by Graphex. Change the variable name in use. The error: {assertion_error} "
        )
        super().__init__(msg)


class SubGraphRuntimeError(RuntimeError):
    """
    Raised when an 'Execute Graph' node (subgraph) encounters one or more errors in the execution of its nodes. The 'errors' parameter can be extracted from this exception to get each individual error that occurred.

    :param name: The name of the subgraph that encountered an error
    :param errors: The list of errors.
    """

    def __init__(self, name: str, errors: typing.List[BaseException]):
        self.errors = errors

        error_strings = [
            re.sub("^", "  │  ", str(e), flags=re.MULTILINE) for e in self.errors
        ]
        error_string = "\n\n".join(error_strings)

        super().__init__(
            f"Subgraph '{name}' finished with the following errors:\n" + error_string
        )


class ThreadedRunTimeError(RuntimeError):
    """
    Raised when a Threaded node fails.

    :param msg: Message for exception
    """

    def __init__(self, msg: str):

        super().__init__(msg)


class DataContainerException(GraphexException):
    """
    Raised when a Data Container is incorrectly used or queried.

    :param msg: The error message.
    :param dc: The Data Container data.
    """

    def __init__(
        self,
        msg: str,
        dc: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]],
    ):
        formatted_dc = re.sub(
            "^",
            "  │  ",
            json.dumps(dc, indent=4, default=lambda x: str(x)),
            flags=re.MULTILINE,
        )
        super().__init__(f"{msg}\n\nData Container:\n{formatted_dc}")


class SubProcessFailed(GraphexException):
    """
    Raised when a aubprocess has failed.

    :param command: The command being ran
    :param stdout: The stdout of the command
    :param stderr: The stderr of the command
    :error_code: The error code of the command
    """

    def __init__(self, command: str, stdout: str, stderr: str, error_code: int):
        msg: str = f""""
        Subprocess command '{command}' failed"
        error_code:{error_code}
        stdout:{stdout}
        stderr:{stderr}
        """
        super().__init__(msg)
