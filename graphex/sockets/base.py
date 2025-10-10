from graphex.datatype import DataType
from graphex import exceptions
from graphex.constants import VARIABLES_NODE_NAMES
import typeguard
import typing

if typing.TYPE_CHECKING:
    from graphex.node import Node
    from graphex.graph import Graph
    from graphex.graphfile import SocketMetadata, NodeMetadata
    


class _BaseSocket:
    """Base class for socket types."""

    def __init__(
        self,
        is_input: bool,
        is_optional: bool,
        is_list: bool,
        datatype: typing.Optional[DataType],
        name: str,
        description: str,
        input_field: typing.Optional[typing.Any],
    ):
        
        from graphex.data.primitives import Dynamic, String, Number, Boolean

        self.is_input = is_input
        """Whether this is an input socket (otherwise, this is an output socket)."""

        self.is_optional = is_optional
        """Whether this is an optional socket."""

        self.is_list = is_list
        """Whether this is a list socket."""

        self.name = name.strip()
        """The socket name"""

        self.datatype = datatype
        """The data type of this socket. A value of None indicates this is a non-data socket."""

        self.description = description
        """The socket description."""

        self.can_have_input_field = False
        """Whether this socket can have an input field."""

        self.input_field = None
        """Default value for the input field on this socket (String/Number/Boolean data types only)"""


        if input_field is not None and (datatype not in [String, Number, Boolean] or not is_input):
            raise ValueError(f"Socket '{self.name}': Socket input field only applies to String/Number/Boolean types.")

        if not self.is_input and self.datatype == Dynamic:
            raise ValueError(f"Socket '{self.name}': Only Input Sockets may have a 'Dynamic' type.")

        if datatype is not None and is_input and (datatype == String or datatype == Number or datatype == Boolean):
            # Input field is allowed
            self.can_have_input_field = True
            self.input_field = input_field

            if self.input_field is not None:
                datatype.assert_type(self.input_field, is_list=is_list)

    def get_value(self, obj: "Node"):
        """
        Get the value of this socket on the given node.
        """
        return self.__get__(obj, None)

    def __get__(self, obj: "Node", _) -> typing.Any:
        if not self.datatype:
            raise exceptions.SocketError(socket_name=self.name, node_name=obj.name, id=obj.id, msg=f"cannot get the value of non-data sockets.")

        if not self.is_input:
            # Output socket
            return obj.get_output_socket_value(self.name)

        # Input socket
        metadata = next(iter([s for s in obj._instance_metadata.get("inputs", []) if s["name"] == self.name]), None)
        if not metadata:
            raise RuntimeError(f"Input socket '{self.name}' does not exist on node {obj.name}")

        if "fieldValue" in metadata:
            value = metadata["fieldValue"]
            error = None
            try:
                self.datatype.assert_type(value, is_list=self.is_list)
            except TypeError as e:
                error = e
            if error:
                raise exceptions.SocketError(socket_name=self.name, node_name=obj.name, id=obj.id, msg=f"field failed type checking ({str(error)})")
            return value

        if "variableName" in metadata:
            return obj._runtime.get_variable(metadata["variableName"])

        if "graphInputName" in metadata:
            return obj._runtime.get_input(metadata["graphInputName"])

        # Fall back to connection source
        if self.is_optional and ("connections" not in metadata or len(metadata["connections"]) == 0):
            return None
        elif "connections" not in metadata or len(metadata["connections"]) == 0:
            raise exceptions.SocketError(socket_name=self.name, node_name=obj.name, id=obj.id, msg=f"no connections exist when one is required.")

        if self.is_list:
            values: typing.List[typing.Any] = []
            for connection in metadata["connections"]:
                conn_node_id, conn_socket_name = connection.split("::")
                value = obj._runtime.nodes[conn_node_id].get_output_socket_value(conn_socket_name)
                if isinstance(value, list):
                    values.extend(value)
                else:
                    values.append(value)
            return values

        # Standard socket
        conn_node_id, conn_socket_name = metadata["connections"][0].split("::")
        return obj._runtime.nodes[conn_node_id].get_output_socket_value(conn_socket_name)

    def set_value(self, obj: "Node", value: typing.Any):
        """
        Set the value of this socket on the given node.
        """
        return self.__set__(obj, value)

    def __set__(self, obj: "Node", value: typing.Any):
        if self.is_input:
            raise AttributeError(f"Cannot get the value of input sockets ({self.name} on node {obj})")

        if not self.datatype:
            raise AttributeError(f"Cannot get the value of link output sockets ({self.name} on node {obj})")

        obj.set_output_socket_value(self.name, value)

    @property
    def is_link(self) -> bool:
        """Whether this is a link (non-data) socket."""
        return self.datatype is None

    def validate_instance_metadata(self, graph: "Graph", node_metadata: "NodeMetadata", socket_metadata: "SocketMetadata"):
        """
        Check that the given socket instance metadata is valid according to this sockets's definitions. Raises errors when a validation fails.

        :param graph: The Graph object that this instance metadata belongs to.
        :param node_metadata: The node metadata that this socket belongs to.
        :param socket_metadata: The socket metadata.
        """
        from graphex.data import primitives
        from graphex import EnumInputSocket

        if not self.is_input:
            # Do not check output sockets; validation is done as a byproduct of checking the inputs
            return

        # Check for invariants
        for source in ["fieldValue", "variableName", "graphInputName"]:
            if source not in socket_metadata:
                continue

            # Ensure no connections exist when a non-connection source is set
            if len(socket_metadata.get("connections", [])) > 0:
                raise exceptions.SocketError(
                    socket_name=self.name,
                    node_name=node_metadata["name"],
                    id=node_metadata["id"],
                    msg=f"no connections can exist when '{source}' is set",
                )

            # Ensure this is a data socket
            if not self.datatype:
                raise exceptions.SocketError(
                    socket_name=self.name, node_name=node_metadata["name"], id=node_metadata["id"], msg=f"non-data sockets cannot have a '{source}' key"
                )

        # Check fieldValue
        if "fieldValue" in socket_metadata and not isinstance(self,EnumInputSocket):
            assert self.datatype, "no datatype"
            if not self.can_have_input_field:
                raise exceptions.SocketError(
                    socket_name=self.name, node_name=node_metadata["name"], id=node_metadata["id"], msg=f"fieldValue is specified when a field does not exist."
                )

            try:
                self.datatype.assert_type(socket_metadata["fieldValue"], is_list=self.is_list)
            except TypeError as e:
                raise exceptions.SocketError(
                    socket_name=self.name, node_name=node_metadata["name"], id=node_metadata["id"], msg=f"field failed type checking ({str(e)})"
                )
            return
        
        # Check fieldValue for enumerated type
        if "fieldValue" in socket_metadata and isinstance(self,EnumInputSocket):
            assert self.datatype, "no datatype"
            if not self.can_have_input_field:
                raise exceptions.SocketError(
                    socket_name=self.name, node_name=node_metadata["name"], id=node_metadata["id"], msg=f"fieldValue is specified when a field does not exist."
                )

            
            if str(socket_metadata["fieldValue"]).upper() not in [key.upper() for key in self.enum_members]:
                raise exceptions.SocketError(
                    socket_name=self.name, node_name=node_metadata["name"], id=node_metadata["id"], msg=f"fieldValue '{socket_metadata['fieldValue']}' must be one of these values [{','.join(self.enum_members.keys())}]"
                )
            return

        # Check variableName
        if "variableName" in socket_metadata:
            assert self.datatype, "no datatype"
            # Ensure at least one set_variable node exists in the graph for this variable
            found = False
            for graph_node in graph.nodes:
                if graph_node["name"] not in VARIABLES_NODE_NAMES or graph_node["name"] == "Get Variable":
                    # Not a set_variable node

                    # Check for any sockets of the type 'VariableOutputSocket' in the graph that match the variable name
                    actual_node = graph.registry.get_node(graph_node["name"])
                    for actual_socket in actual_node.outputs(graph, graph_node):
                        if "allowsVariable" in actual_socket.metadata() and actual_socket.name == socket_metadata["variableName"]:
                            found = True
                            break
                    # both: Not a set_variable node and no sockets of the type 'VariableOutputSocket' exist in the graph the match the variable name
                    continue
                if graph_node.get("fieldValue", "") != socket_metadata["variableName"]:
                    # Variable names do not match
                    continue
                node_type = graph.registry.get_node(graph_node["name"])
                data_inputs = node_type.data_inputs(graph, node_metadata)
                if len(data_inputs) == 0 or (data_inputs[0].datatype != primitives.Dynamic and data_inputs[0].datatype != self.datatype):
                    # Data types do not match
                    continue
                found = True
                break

            if not found:
                raise exceptions.SocketError(
                    socket_name=self.name,
                    node_name=node_metadata["name"],
                    id=node_metadata["id"],
                    msg=f"no '{self.datatype.name}' variable exists with the name '{socket_metadata['variableName']}'.",
                )
            return

        # Check graphInputName
        if "graphInputName" in socket_metadata:
            assert self.datatype, "no datatype"
            # Ensure input value exists in graph
            if not any(
                [
                    socket_metadata["graphInputName"] == graph_input["name"]
                    and self.datatype.name == graph_input["datatype"]
                    and self.is_list == graph_input.get("isList", False)
                    for graph_input in graph.inputs
                ]
            ):
                raise exceptions.SocketError(
                    socket_name=self.name,
                    node_name=node_metadata["name"],
                    id=node_metadata["id"],
                    msg=f"no Graph Input exists with name '{socket_metadata['graphInputName']}' that matches the given socket type.",
                )
            return

        # Fall back to connections
        if len(socket_metadata.get("connections", [])) == 0 and not self.is_optional:
            raise exceptions.SocketError(
                socket_name=self.name, node_name=node_metadata["name"], id=node_metadata["id"], msg=f"no connections exist when one is required."
            )

        if len(socket_metadata.get("connections", [])) > 1 and not self.is_list:
            raise exceptions.SocketError(
                socket_name=self.name,
                node_name=node_metadata["name"],
                id=node_metadata["id"],
                msg=f"{len(socket_metadata.get('connections', []))} connections exist when only one can exist.",
            )

        # Check connections
        for connection in socket_metadata.get("connections", []):
            conn_node_id, conn_socket_name = connection.split("::")

            target_node_metadata = graph.get_node(conn_node_id)
            target_node = graph.registry.get_node(target_node_metadata["name"])
            target_socket = target_node.get_output(conn_socket_name, graph, target_node_metadata)

            if self.datatype != primitives.Dynamic and target_socket.datatype != self.datatype:
                datatype = self.datatype.name if self.datatype else "None"
                other_datatype = target_socket.datatype.name if target_socket.datatype else "None"
                raise exceptions.SocketInvalidDataType(
                    self.name, node_metadata["name"], node_metadata["id"], conn_socket_name, target_node.name, conn_node_id, datatype, other_datatype
                )

            if target_socket.is_list and not self.is_list:
                raise exceptions.SocketInvalidConnectionType(
                    self.name,
                    node_metadata["name"],
                    node_metadata["id"],
                    conn_socket_name,
                    target_node.name,
                    conn_node_id,
                    "non-list input sockets cannot receive inputs from a list output socket",
                )

    def metadata(self):
        return {
                    "isInput": self.is_input,
                    "isOptional": self.is_optional,
                    "isList": self.is_list,
                    "isLink": self.is_link,
                    "name": self.name,
                    "datatype": self.datatype.name if self.datatype else None,
                    "description": self.description,
                    "canHaveField": self.can_have_input_field,
                    "field": self.input_field,
                }
