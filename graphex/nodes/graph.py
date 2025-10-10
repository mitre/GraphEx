import typing

from graphex import (
    FILE_EXTENSION,
    Graph,
    GraphRuntime,
    InputField,
    InputSocket,
    ListInputSocket,
    ListOutputSocket,
    Node,
    NodeDynamicAttributes,
    NodeMetadata,
    NodeType,
    OutputSocket,
    constants,
    exceptions,
)
from graphex.sockets import _BaseSocket


class GraphStart(Node, include_backward_link=False):
    name: str = "Graph Start"
    description: str = "Start of the Graph."
    categories: typing.List[str] = ["Graph"]
    color: str = constants.COLOR_SPECIAL

    def run(self):
        pass


class LinkEnd(Node, include_forward_link=False):
    name: str = "End"
    description: str = "End of a single chain of execution."
    categories: typing.List[str] = ["Graph"]
    color: str = constants.COLOR_SPECIAL

    def run(self):
        pass


class ExecuteGraph(Node):
    name = "Execute Graph"
    description = "Execute another graph from this graph."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#defining-functions"]
    categories = ["Graph"]
    color = constants.COLOR_EXECUTE

    field = InputField(default_value="", name="Graph File Path")

    @classmethod
    def _get_subgraph(cls, graph: Graph, path: str):
        raw_path = path.strip()
        if len(raw_path) == 0:
            raise ValueError("No graph file path provided.")

        if not raw_path.lower().endswith(FILE_EXTENSION):
            raw_path = raw_path + FILE_EXTENSION

        file_path = graph.registry.resolve_path(raw_path)
        subgraph = graph.registry.load_graph_file(
            file_path, validation_cache=graph.validation_cache
        )
        return subgraph

    def run(self):
        self.log(f"Executing graph file: {self.field}")

        dynamic_attributes = self.dynamic_attributes(
            self._graph, self._instance_metadata
        )
        if dynamic_attributes.error:
            raise RuntimeError(dynamic_attributes.error)

        dynamic_sockets = dynamic_attributes.sockets or []

        # Set up a new runtime for this subgraph
        input_values = {
            socket.name: socket.get_value(self)
            for socket in dynamic_sockets
            if socket.is_input and not socket.is_link
        }

        subgraph = self._get_subgraph(self._graph, self.field)
        subgraph_runtime = GraphRuntime(
            subgraph,
            self.logger,
            input_values,
            is_subgraph=True,
            azure_integration=self._runtime.azure_integration,
            verbose_errors=self._runtime.verbose_errors,
            composite_inputs=[],
        )

        # Execute the new graph
        errors = subgraph_runtime.run()
        if errors:
            raise exceptions.SubGraphRuntimeError(
                name=self._graph.name or self.field, errors=errors
            )

        # Extract the output values and set the output sockets
        for socket in dynamic_sockets:
            if not socket.is_input and not socket.is_link:
                assert socket.datatype, f"No datatype set on output socket"
                value = subgraph_runtime.get_output(socket.name)
                socket.set_value(self, value)

    @classmethod
    def dynamic_attributes(
        cls, graph: Graph, instance_metadata: NodeMetadata
    ) -> NodeDynamicAttributes:
        try:
            subgraph = cls._get_subgraph(
                graph, str(instance_metadata.get("fieldValue", ""))
            )
            subgraph.validate()

            # Get the sockets
            subgraph = cls._get_subgraph(
                graph, str(instance_metadata.get("fieldValue", ""))
            )
            input_sockets: typing.List[_BaseSocket] = []
            output_sockets: typing.List[_BaseSocket] = []

            for graph_input in subgraph.inputs:
                input_datatype = graph.registry.get_datatype(graph_input["datatype"])
                if graph_input.get("isList", False):
                    default_value = graph_input.get("defaultValue", None)
                    assert default_value is None or isinstance(
                        default_value, list
                    ), "Invalid default value (must be a list or None)"
                    input_sockets.append(
                        ListInputSocket(
                            datatype=input_datatype,
                            name=graph_input["name"],
                            description=graph_input.get("description", ""),
                            input_field=default_value,
                        )
                    )
                else:
                    input_sockets.append(
                        InputSocket(
                            datatype=input_datatype,
                            name=graph_input["name"],
                            description=graph_input.get("description", ""),
                            input_field=graph_input.get("defaultValue", None),
                        )
                    )

            for graph_output in subgraph.outputs:
                output_datatype = graph.registry.get_datatype(graph_output["datatype"])
                if graph_output.get("isList", False):
                    output_sockets.append(
                        ListOutputSocket(
                            datatype=output_datatype,
                            name=graph_output["name"],
                            description=graph_output.get("description", ""),
                        )
                    )
                else:
                    output_sockets.append(
                        OutputSocket(
                            datatype=output_datatype,
                            name=graph_output["name"],
                            description=graph_output.get("description", ""),
                        )
                    )

            sockets = [*input_sockets, *output_sockets]

            # Get the description
            desc = subgraph.file.get("description", "")

            return NodeDynamicAttributes(sockets, desc, None, None)
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class GetGraphInput(Node):
    node_type = NodeType.GENERATOR
    name = f"Get Graph Input"
    description = f"Get the value of a graph input for this graph."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#defining-functions"]
    categories = ["Graph"]
    color = constants.COLOR_SPECIAL

    field = InputField(default_value="", name="Graph Input Name")

    def run(self):
        input_name = self.field.strip()
        assert len(input_name) != 0, "Graph input names cannot be empty."
        self.get_output("Value", self._graph, self._instance_metadata).set_value(
            self, self._runtime.get_input(input_name)
        )

    @classmethod
    def dynamic_attributes(
        cls, graph: Graph, instance_metadata: NodeMetadata
    ) -> NodeDynamicAttributes:
        input_name = str(instance_metadata.get("fieldValue", "")).strip()
        if not len(input_name):
            return NodeDynamicAttributes(
                None, None, None, "No graph input name provided."
            )

        try:
            found_graph_inputs = [
                inp for inp in graph.inputs if inp["name"] == input_name
            ]
            if len(found_graph_inputs) == 0:
                return NodeDynamicAttributes(
                    None, None, None, f"Graph input '{input_name}' not found."
                )

            found_graph_input = found_graph_inputs[0]
            datatype = graph.registry.get_datatype(found_graph_input["datatype"])

            if found_graph_input.get("isList", False):
                return NodeDynamicAttributes(
                    sockets=[
                        ListOutputSocket(
                            datatype=datatype,
                            name="Value",
                            description=f"The '{datatype.name}' list value of the '{input_name}' graph input.",
                        )
                    ],
                    description=f"Get the '{datatype.name}' list value of a graph input for this graph.",
                    color=datatype.color,
                    error=None,
                )

            return NodeDynamicAttributes(
                sockets=[
                    OutputSocket(
                        datatype=datatype,
                        name="Value",
                        description=f"The '{datatype.name}' value of the '{input_name}' graph input.",
                    )
                ],
                description=f"Get the '{datatype.name}' value of a graph input for this graph.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class SetGraphOutput(Node):
    name = f"Set Graph Output"
    description = f"Set the value of a graph output for this graph."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/simple_stmts.html#return"]
    categories = ["Graph"]
    color = constants.COLOR_SPECIAL

    field = InputField(default_value="", name="Graph Output Name")

    def run(self):
        output_name = self.field.strip()
        assert len(output_name) != 0, "Graph input names cannot be empty."

        value_socket = self.get_input("Value", self._graph, self._instance_metadata)
        assert value_socket.datatype, "No datatype associated with graph output"

        value = value_socket.get_value(self)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(
            self, value
        )

        self._runtime.set_output(
            output_name, value_socket.datatype, value_socket.is_list, value
        )

    @classmethod
    def dynamic_attributes(
        cls, graph: Graph, instance_metadata: NodeMetadata
    ) -> NodeDynamicAttributes:
        output_name = str(instance_metadata.get("fieldValue", "")).strip()
        if not len(output_name):
            return NodeDynamicAttributes(
                None, None, None, "No graph output name provided."
            )

        try:
            found_graph_outputs = [
                output for output in graph.outputs if output["name"] == output_name
            ]
            if len(found_graph_outputs) == 0:
                return NodeDynamicAttributes(
                    None, None, None, f"Graph output '{output_name}' not found."
                )

            found_graph_output = found_graph_outputs[0]
            datatype = graph.registry.get_datatype(found_graph_output["datatype"])

            if found_graph_output.get("isList", False):
                return NodeDynamicAttributes(
                    sockets=[
                        ListInputSocket(
                            datatype=datatype,
                            name="Value",
                            description=f"The '{datatype.name}' list value to set for the '{output_name}' graph output.",
                        ),
                        ListOutputSocket(
                            datatype=datatype,
                            name="Value",
                            description=f"The '{datatype.name}' list value that was set for the '{output_name}' graph output (same as input).",
                        ),
                    ],
                    description=f"Set the '{datatype.name}' list value of a graph output for this graph.",
                    color=datatype.color,
                    error=None,
                )

            return NodeDynamicAttributes(
                sockets=[
                    InputSocket(
                        datatype=datatype,
                        name="Value",
                        description=f"The '{datatype.name}' value to set for the '{output_name}' graph output.",
                    ),
                    OutputSocket(
                        datatype=datatype,
                        name="Value",
                        description=f"The '{datatype.name}' value that was set for the '{output_name}' graph output (same as input).",
                    ),
                ],
                description=f"Set the '{datatype.name}' value of a graph output for this graph.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))
