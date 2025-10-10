import typing

from graphex import exceptions
from graphex.graphfile import (
    GraphFile,
    GraphInputMetadata,
    GraphOutputMetadata,
    NodeMetadata,
)

if typing.TYPE_CHECKING:
    from graphex.registry import GraphRegistry
    from graphex.sockets import _BaseSocket


class GraphValidationCache:
    """
    Cached used to store the results of expensive computations during validation.
    """

    def __init__(self):
        self.dynamic_sockets: typing.Dict[
            str, typing.Dict[str, typing.List["_BaseSocket"]]
        ] = {}
        """Cached dynamic sockets. Maps: Graph Name -> Node ID -> List of Dynamic Sockets"""


class Graph:
    """An actualized Graph (graph file + registry)."""

    def __init__(
        self,
        file: GraphFile,
        registry: "GraphRegistry",
        name: typing.Optional[str] = None,
        validation_cache: typing.Optional[GraphValidationCache] = None,
    ):
        self.file = file
        """The graph file."""

        self.registry = registry
        """The graph registry."""

        self.name = name
        """The name of this graph."""

        self.filepath: typing.Optional[str] = None
        """Optional value containing the relative or absolute path to the file"""

        self.validation_cache = (
            validation_cache if validation_cache else GraphValidationCache()
        )
        """The validation cache. This is used to store the results of expensive computations during validation."""

        self.socket_output_to_input: typing.Dict[
            str, typing.List[typing.Tuple[NodeMetadata, str]]
        ] = {}
        """Mapping of an output socket's ID (NodeID::SocketName) to the nodes/sockets that it is connected to."""

        # Create the socket output-to-input mapping
        # This is necessary because the graph file only stores information about input-to-output connections
        # Often, we'll want the reverse and do not want to traverse the graph file to obtain this information
        for node in self.file.get("nodes", []):
            for socket in node.get("inputs", []):
                for connection in socket.get("connections", []):
                    if not isinstance(connection, str):
                        continue
                    if connection not in self.socket_output_to_input:
                        self.socket_output_to_input[connection] = []
                    self.socket_output_to_input[connection].append(
                        (node, socket["name"])
                    )

    @property
    def nodes(self) -> typing.List[NodeMetadata]:
        """All nodes in this graph."""
        return self.file["nodes"]

    @property
    def inputs(self) -> typing.List[GraphInputMetadata]:
        """All inputs for this graph."""
        return self.file.get("inputs", [])

    @property
    def outputs(self) -> typing.List[GraphOutputMetadata]:
        """All outputs for this graph."""
        return self.file.get("outputs", [])

    def is_executable(self) -> bool:
        """Test whether this graph is directly executable (only contains primitive inputs or is a composite input that is not a list)."""
        return all(
            [
                (gi["datatype"] in ["String", "Number", "Boolean"])
                or (
                    gi["datatype"] in self.registry.composite_inputs
                    and not gi.get("isList", False)
                )
                for gi in self.inputs
            ]
        )

    def find_node(self, id: str) -> typing.Optional[NodeMetadata]:
        """Get a node in the graph file by ID and return ``None`` if the node does not exist."""
        for node in self.nodes:
            if node["id"] == id:
                return node
        return None

    def get_node(self, id: str) -> NodeMetadata:
        """Get a node in the graph file by ID and raise an error if it does not exist."""
        metadata = self.find_node(id)
        if not metadata:
            raise ValueError(f"No node exists with ID {id}")
        return metadata

    def get_socket_connected_inputs(
        self, node: NodeMetadata, output_socket_name: str
    ) -> typing.List[typing.Tuple[NodeMetadata, str]]:
        """
        Get all the input sockets that the given output socket is connected to. The input sockets will be returned as a list of tuples. Each
        tuple contains the node metadata for the node that the output socket is connected to, as well as the input socket name on that node.

        :param node: The node containing the output socket to query.
        :param output_socket_name: The name of the output socket on the node.

        :returns: A list of tuples (NodeMetadata, Input Socket Name)
        """
        output_socket_id = f"{node['id']}::{output_socket_name}"
        if output_socket_id not in self.socket_output_to_input:
            return []
        return self.socket_output_to_input[output_socket_id]

    def get_backward(
        self, node: NodeMetadata, socket_name: typing.Optional[str] = None
    ) -> typing.List[NodeMetadata]:
        """
        Get all backward nodes from this node (immediate ancestors).

        :param node: The target node.
        :param socket_name: The name of the link input socket for which to get backward node(s). If ``None``, all link input sockets are used (i.e. get all backward nodes).
        """
        ids: typing.Set[str] = set()
        sockets = self.registry.get_node(node["name"]).link_inputs(self, node)

        available_sockets = [socket.name for socket in sockets]
        if socket_name and socket_name not in available_sockets:
            raise RuntimeError(
                f"Input link socket '{socket_name}' is not available on '{node['name']}'. Available sockets: {', '.join(available_sockets)}"
            )

        for socket in sockets:
            if socket_name and socket.name != socket_name:
                continue
            socket_metadata = [
                metadata
                for metadata in node.get("inputs", [])
                if metadata["name"] == socket.name
            ][0]
            for connection in socket_metadata.get("connections", []):
                ids.add(connection.split("::")[0])

        return [self.get_node(id) for id in ids]

    def get_forward(
        self, node: NodeMetadata, socket_name: typing.Optional[str] = None
    ) -> typing.List[NodeMetadata]:
        """
        Get all forward nodes from this node (immediate descendants).

        :param node: The target node.
        :param socket_name: The name of the link output socket for which to get forward node(s). If ``None``, all link output sockets are used (i.e. get all forward nodes).
        """
        ids: typing.Set[str] = set()
        sockets = self.registry.get_node(node["name"]).link_outputs(self, node)

        available_sockets = [socket.name for socket in sockets]
        if socket_name and socket_name not in available_sockets:
            raise RuntimeError(
                f"Output link socket '{socket_name}' is not available on '{node['name']}'. Available sockets: {', '.join(available_sockets)}"
            )

        for socket in sockets:
            if socket_name and socket.name != socket_name:
                continue
            connected_inputs = self.get_socket_connected_inputs(node, socket.name)
            for connected_input in connected_inputs:
                ids.add(connected_input[0]["id"])

        return [self.get_node(id) for id in ids]

    def get_start_node(self) -> NodeMetadata:
        """
        Get the nodes at the start of the graph.

        The start node is defined as any node with output link sockets but no input link sockets.

        If zero or multiple exist, an error will be raised.
        """
        valid_nodes: typing.List[NodeMetadata] = []
        for metadata in self.nodes:
            node = self.registry.get_node(metadata["name"])
            if (
                len(node.link_inputs(self, metadata)) == 0
                and len(node.link_outputs(self, metadata)) > 0
            ):
                valid_nodes.append(metadata)
        if len(valid_nodes) == 0:
            raise RuntimeError(
                "No starting nodes found in graph. Ensure exactly one valid start node exists (a node containing output link sockets but no input link sockets)."
            )
        if len(valid_nodes) > 1:
            node_strings = [f"{node['name']} ({node['id']})" for node in valid_nodes]
            raise RuntimeError(
                f"Multiple starting nodes found in graph: {', '.join(node_strings)}"
            )
        return valid_nodes[0]

    #################
    # Validations
    #################
    def validate(self):
        """
        Validate that this is a valid graph (e.g. all required sockets are connected, data types match up, no cycles exist, etc.).
        """
        error = None
        try:
            # Keep track of _backward socket connections
            # This is to catch yaml file corruption errors where two nodes have the same _backward connection
            previously_seen_connections: typing.Set[str] = set()

            # Validate nodes
            for node_metadata in self.nodes:
                node = self.registry.get_node(node_metadata["name"])
                backward_connection_name = node.validate_instance_metadata(
                    self, node_metadata
                )
                if backward_connection_name:
                    if backward_connection_name in previously_seen_connections:
                        raise RuntimeError(
                            f"Node with name: '{node_metadata['name']}' is connected in sequence to a connection: '{backward_connection_name}' that is already assigned to another node! This graph file is corrupted: '{self.name}'! Open the '.gx' file in the UI and resolve the errors."
                        )
                    else:
                        previously_seen_connections.add(backward_connection_name)

            del previously_seen_connections

            # Validate I/O
            self._validate_graph_io()

            # Ensure we can get the start of the graph
            self.get_start_node()

            # Check for loops
            self._validate_cycles()
        except Exception as e:
            error = e

        if error:
            if isinstance(error, exceptions.SocketError):
                raise error
            raise exceptions.GraphValidationError(
                self.name, f"({type(error).__name__}) {str(error)}"
            )

    def _validate_graph_io(self):
        """Validate the graph input/output data."""
        # Validate inputs
        input_names: typing.Dict[str, GraphInputMetadata] = {}
        for input_metadata in self.inputs:
            # Check for duplicate name
            name = input_metadata["name"].strip()
            if len(name) == 0:
                raise RuntimeError(f"Graph input name is empty.")
            if name in input_names:
                raise RuntimeError(f"Duplicate graph input found with name '{name}'")
            input_names[name] = input_metadata

            # Check datatype
            datatype = self.registry.get_datatype(input_metadata["datatype"])
            if "defaultValue" in input_metadata:
                datatype.assert_type(
                    input_metadata["defaultValue"],
                    is_list=input_metadata.get("isList", False),
                )

        # Validate outputs
        output_names: typing.Dict[str, GraphOutputMetadata] = {}
        for output_metadata in self.outputs:
            # Check for duplicate name
            name = output_metadata["name"].strip()
            if len(name) == 0:
                raise RuntimeError(f"Graph output name is empty.")
            if name in output_names:
                raise RuntimeError(f"Duplicate graph output found with name '{name}'")
            output_names[name] = output_metadata

            # Ensure datatype exists
            self.registry.get_datatype(output_metadata["datatype"])

    def _validate_cycles(self):
        """Ensure no cycles exist in the graph."""

        def find_cycles(node: NodeMetadata, seen: typing.List[NodeMetadata]):
            if node in seen:
                nodes_in_cycle = seen[seen.index(node) :]
                cycle_string = (
                    " -> ".join([f"{n['name']} ({n['id']})" for n in nodes_in_cycle])
                    + f" -> {node['name']} ({node['id']})"
                )
                raise RuntimeError(f"Cycle detect in graph: {cycle_string}")
            for n in self.get_forward(node):
                find_cycles(n, [*seen, node])

        find_cycles(self.get_start_node(), [])
