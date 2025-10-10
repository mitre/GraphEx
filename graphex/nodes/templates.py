from graphex import DataType, Graph, NodeMetadata, Node
import typing

from graphex.constants import VARIABLES_NODE_NAMES


class DynamicInputTemplateNode(Node, is_template=True):
    """
    Template Node for nodes that accept a Dynamic input and change their behavior based on that input.
    """

    @classmethod
    def get_datatype(cls, input_name: str, graph: Graph, instance_metadata: NodeMetadata) -> typing.Optional[DataType]:
        """
        Get the data type that is input into a Dynamic-typed input socket. This will determine the incoming data type, either from
        a connection, a variable, or a graph input.
        """
        all_socket_metadata = [s for s in instance_metadata.get("inputs", []) if s["name"] == input_name]
        if len(all_socket_metadata) == 0:
            raise ValueError(f"No socket found with name {input_name}")
        socket_metadata = all_socket_metadata[0]

        connections = socket_metadata.get("connections", [])
        if len(connections):
            datatype = None
            for connection in connections:
                conn_node_id, conn_socket_name = connection.split("::")
                conn_node_metadata = graph.get_node(conn_node_id)
                conn_node = graph.registry.get_node(conn_node_metadata["name"])

                conn_datatype = conn_node.get_output(conn_socket_name, graph, conn_node_metadata).datatype
                if not datatype:
                    datatype = conn_datatype

                if datatype and conn_datatype and conn_datatype != datatype:
                    raise RuntimeError(
                        f"Connection from node '{conn_node_metadata['name']}' (ID={conn_node_metadata['id']}) mismatches the DataType for socket ({datatype.name} versus {conn_datatype.name})"
                    )

            if datatype:
                return datatype

        varname = socket_metadata.get("variableName", "")
        if varname:
            var_nodes = [
                n for n in graph.nodes if (n["name"] in VARIABLES_NODE_NAMES and n["name"] != "Get Variable") and n.get("fieldValue", None) == varname
            ]
            if len(var_nodes):
                var_node_metadata = var_nodes[0]
                var_node = graph.registry.get_node(var_node_metadata["name"])
                try:
                    conn_sockets = var_node.data_outputs(graph, var_node_metadata)
                    for conn_socket in conn_sockets:
                        if conn_socket.datatype:
                            return conn_socket.datatype
                except Exception:
                    pass

        graph_input = socket_metadata.get("graphInputName", "")
        if graph_input:
            for input_metadata in graph.inputs:
                if input_metadata["name"] == graph_input:
                    try:
                        return graph.registry.get_datatype(input_metadata["datatype"])
                    except Exception:
                        pass

        return None
