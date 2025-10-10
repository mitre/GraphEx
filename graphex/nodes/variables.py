from graphex import (
    Dynamic,
    String,
    Boolean,
    Number,
    Graph,
    NodeMetadata,
    NodeDynamicAttributes,
    NodeType,
    Node,
    InputSocket,
    ListInputSocket,
    OutputSocket,
    ListOutputSocket,
    LinkOutputSocket,
    InputField,
    constants,
)
from graphex.nodes.templates import DynamicInputTemplateNode
from graphex.constants import VARIABLES_NODE_NAMES
import typing

from graphex.sockets.output_sockets import VariableOutputSocket

class SetVariable(DynamicInputTemplateNode):
    name = f"Set Variable"
    description = f"Save a value to a variable. Any datatype (including objects) can be provided to this node to be saved to variable."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Dynamic"]
    color = constants.COLOR_SPECIAL

    variable_value = InputSocket(datatype=Dynamic, name="Value To Save", description="The value to save to a variable.")

    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."

        datatype = self.get_datatype("Value To Save", self._graph, self._instance_metadata)
        assert datatype, f"No DataType available"

        self._runtime.set_variable(variable_name, datatype, False, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("Value To Save", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    InputSocket(datatype=datatype, name="Value To Save", description="The value to save to a variable."),
                    OutputSocket(datatype=datatype, name="Value", description="The value that was saved (same as input)."),
                ],
                description=f"Save a '{datatype.name}' value to a variable.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class SetListVariable(DynamicInputTemplateNode):
    name = "Set List Variable"
    description = f"Save a list of values to a variable.  Any list datatype (including objects) can be provided to this node to be saved to variable."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Dynamic", "Lists"]
    color = constants.COLOR_SPECIAL

    variable_value = ListInputSocket(datatype=Dynamic, name="Value To Save", description="The value to save to a variable.")

    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."

        datatype = self.get_datatype("Value To Save", self._graph, self._instance_metadata)
        assert datatype, f"No DataType available"

        self._runtime.set_variable(variable_name, datatype, True, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("Value To Save", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="Value To Save", description="The value to save to a variable."),
                    ListOutputSocket(datatype=datatype, name="Value", description="The value that was saved (same as input)."),
                ],
                description=f"Save a list of '{datatype.name}' values to a variable.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class AppendToListVariable(DynamicInputTemplateNode):
    name = f"Append To List Variable"
    description = f"Append a value to a list variable. If the list variable does not exist, it will be created with this value as its first entry.  Any list datatype (including objects) can be provided to this node to be saved to variable."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Dynamic", "Lists"]
    color = constants.COLOR_SPECIAL

    value_to_append = InputSocket(datatype=Dynamic, name="Value To Append", description="The value to append to the list variable.")

    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."

        datatype = self.get_datatype("Value To Append", self._graph, self._instance_metadata)
        assert datatype, f"No DataType available"

        if variable_name not in self._runtime.variables:
            # Does not exist, create the variable
            self._runtime.set_variable(variable_name, datatype, True, [self.value_to_append])
            self.get_output("New List", self._graph, self._instance_metadata).set_value(self, [self.value_to_append])
            return

        # Already exists, append
        current_list = self._runtime.get_variable(variable_name)
        assert isinstance(current_list, list), f"{variable_name} does not refer to a list variable."
        list_copy = [*current_list]
        list_copy.append(self.value_to_append)
        self._runtime.set_variable(variable_name, datatype, True, list_copy)
        self.get_output("New List", self._graph, self._instance_metadata).set_value(self, list_copy)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("Value To Append", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    InputSocket(datatype=datatype, name="Value To Append", description="The value to append to the list variable."),
                    ListOutputSocket(datatype=datatype, name="New List", description="The new value of the list variable with the item appended."),
                ],
                description=f"Append a '{datatype.name}' value to a list variable. If the list variable does not exist, it will be created with this value as its first entry.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class GetVariable(DynamicInputTemplateNode):
    node_type = NodeType.GENERATOR
    name = f"Get Variable"
    description = f"Get the saved value of a variable. Once you've typed in the name of a variable that has been previously set (in any way), this node will change to the appropriate color to match the datatype and provide you an output socket to pull the variable data from."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables"]
    color = constants.COLOR_SPECIAL

    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self._runtime.get_variable(variable_name))

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        varname = str(instance_metadata.get("fieldValue", "")).strip()
        if not len(varname):
            return NodeDynamicAttributes(None, None, None, "No variable name provided.")

        try:
            datatype = None
            is_list = False
            for node in graph.nodes:
                if node["name"] not in VARIABLES_NODE_NAMES:
                    actual_node = graph.registry.get_node(node["name"])
                    found_variable_socket = False
                    for actual_socket in actual_node.outputs(graph, node):
                        if isinstance(actual_socket, VariableOutputSocket):
                            if actual_socket.name == varname and actual_socket.save_to_variable: #type:ignore
                                datatype = actual_socket.datatype
                                is_list = actual_socket.is_list
                                found_variable_socket = True
                                break
                    if found_variable_socket:
                        break
                    else:
                        continue
                elif node.get("fieldValue", "") == varname:
                    node_type = graph.registry.get_node(node["name"])
                    output_sockets = node_type.data_outputs(graph, node)
                    if len(output_sockets) != 0:
                        datatype = output_sockets[0].datatype
                        is_list = output_sockets[0].is_list
                        break

            if not datatype:
                return NodeDynamicAttributes(None, None, None, f"Variable '{varname}' not found.")

            if is_list:
                return NodeDynamicAttributes(
                    sockets=[ListOutputSocket(datatype=datatype, name="Value", description=f"The '{datatype.name}' list value of the '{varname}' variable.")],
                    description=f"Get the '{datatype.name}' list value of the '{varname}' variable.",
                    color=datatype.color,
                    error=None,
                )

            return NodeDynamicAttributes(
                sockets=[OutputSocket(datatype=datatype, name="Value", description=f"The '{datatype.name}' value of the '{varname}' variable.")],
                description=f"Get the '{datatype.name}' value of the '{varname}' variable.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class VariableExists(Node):
    name: str = "Variable Exists"
    description: str = "Check if a variable (by name) has been defined / is available in this graph at this point."
    categories: typing.List[str] = ["Variables"]
    color = constants.COLOR_SPECIAL

    varname = InputSocket(datatype=String, name="Variable Name", description="The name of the variable to check.")

    exists = OutputSocket(datatype=Boolean, name="Exists?", description="Whether the variable currently exists.")

    def run(self):
        self.exists = self.varname in self._runtime.variables


class VariableExistsIfElse(Node, include_forward_link=False):
    name = "Variable Exists (If / Else)"
    description = "Conditionally continue this graph based on whether a variable (by name) has been defined / is available in this graph at this point."
    categories = ["Variables"]
    color = constants.COLOR_CONTROL_FLOW

    varname = InputSocket(datatype=String, name="Variable Name", description="The name of the variable to check.")

    exists = LinkOutputSocket(name="Exists", description="Execute this branch if the input boolean is True.")
    does_not_exist = LinkOutputSocket(name="Does Not Exist", description="Execute this branch if the output boolean is True.")

    def run(self):
        pass

    def run_next(self):
        if self.varname in self._runtime.variables:
            # Continue down the 'Exists' line
            for node in self.forward("Exists"):
                self._runtime.execute_node(node)
        else:
            # Continue down the 'Does Not Exist' line
            for node in self.forward("Does Not Exist"):
                self._runtime.execute_node(node)


class SetVariableString(Node):
    name = f"Set Variable (String)"
    description = f"Save a String value to a variable. If the provided variable name doesn't exist, it will create the variable. If the variable already exists, it will overwrite the previously set value."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data"]
    color = constants.COLOR_STRING

    variable_value = InputSocket(datatype=String, name="String To Save", description="The String data to save to a variable.")
    original_value = OutputSocket(datatype=String, name="Value", description="The value that was saved (same as input).")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."
        self._runtime.set_variable(variable_name, String, False, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)


class SetVariableNumber(Node):
    name = f"Set Variable (Number)"
    description = f"Save a Number value to a variable. If the provided variable name doesn't exist, it will create the variable. If the variable already exists, it will overwrite the previously set value."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data"]
    color = constants.COLOR_NUMBER

    variable_value = InputSocket(datatype=Number, name="Number To Save", description="The Number data to save to a variable.")
    original_value = OutputSocket(datatype=Number, name="Value", description="The value that was saved (same as input).")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."
        self._runtime.set_variable(variable_name, Number, False, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)


class SetVariableBoolean(Node):
    name = f"Set Variable (Boolean)"
    description = f"Save a Boolean value to a variable."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data"]
    color = constants.COLOR_BOOLEAN

    variable_value = InputSocket(datatype=Boolean, name="Boolean To Save", description="The Boolean data to save to a variable.")
    original_value = OutputSocket(datatype=Boolean, name="Value", description="The value that was saved (same as input).")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty. If the provided variable name doesn't exist, it will create the variable. If the variable already exists, it will overwrite the previously set value."
        self._runtime.set_variable(variable_name, Boolean, False, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)


class SetVariableStringList(Node):
    name = f"Set List Variable (String)"
    description = f"Save a list of String values to a variable. If the provided variable name doesn't exist, it will create the variable. If the variable already exists, it will overwrite the previously set value."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data", "Lists"]
    color = constants.COLOR_STRING

    variable_value = ListInputSocket(datatype=String, name="String List To Save", description="The String list data to save to a variable.")
    original_value = ListOutputSocket(datatype=String, name="Value", description="The value that was saved (same as input).")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."
        self._runtime.set_variable(variable_name, String, True, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)


class SetVariableBooleanList(Node):
    name = f"Set List Variable (Boolean)"
    description = f"Save a list of Boolean values to a variable. If the provided variable name doesn't exist, it will create the variable. If the variable already exists, it will overwrite the previously set value."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data", "Lists"]
    color = constants.COLOR_BOOLEAN

    variable_value = ListInputSocket(datatype=Boolean, name="Boolean List To Save", description="The Boolean list data to save to a variable.")
    original_value = ListOutputSocket(datatype=Boolean, name="Value", description="The value that was saved (same as input).")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."
        self._runtime.set_variable(variable_name, Boolean, True, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)


class SetVariableNumberList(Node):
    name = f"Set List Variable (Number)"
    description = f"Save a list of Number values to a variable. If the provided variable name doesn't exist, it will create the variable. If the variable already exists, it will overwrite the previously set value."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data", "Lists"]
    color = constants.COLOR_NUMBER

    variable_value = ListInputSocket(datatype=Number, name="Number List To Save", description="The Number list data to save to a variable.")
    original_value = ListOutputSocket(datatype=Number, name="Value", description="The value that was saved (same as input).")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."
        self._runtime.set_variable(variable_name, Number, True, self.variable_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.variable_value)


class AppendToListVariableString(Node):
    name = f"Append To List Variable (String)"
    description = f"Append a String value to a list of Strings stored as a variable. If the list variable does not exist, it will be created with this value as its first entry."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data", "Lists"]
    color = constants.COLOR_STRING

    value_to_append = InputSocket(datatype=String, name="String To Append", description="The String value to append to the list variable.")
    new_list = ListOutputSocket(datatype=String, name="New List", description="The new value of the list variable with the item append.")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."

        runtime = self._runtime
        if variable_name not in runtime.variables:
            # Does not exist, create the variable
            runtime.set_variable(variable_name, String, True, [self.value_to_append])
            self.new_list = [self.value_to_append]
            return

        # Already exists, append
        current_list = runtime.get_variable(variable_name)
        assert isinstance(current_list, list), f"{variable_name} does not refer to a list variable."
        list_copy = [*current_list]
        list_copy.append(self.value_to_append)
        runtime.set_variable(variable_name, String, True, list_copy)
        self.new_list = list_copy


class AppendToListVariableBoolean(Node):
    name = f"Append To List Variable (Boolean)"
    description = f"Append a Boolean value to a list of Booleans stored as a variable. If the list variable does not exist, it will be created with this value as its first entry."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data", "Lists"]
    color = constants.COLOR_BOOLEAN

    value_to_append = InputSocket(datatype=Boolean, name="Boolean To Append", description="The Boolean value to append to the list variable.")
    new_list = ListOutputSocket(datatype=Boolean, name="New List", description="The new value of the list variable with the item append.")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."

        runtime = self._runtime
        if variable_name not in runtime.variables:
            # Does not exist, create the variable
            runtime.set_variable(variable_name, Boolean, True, [self.value_to_append])
            self.new_list = [self.value_to_append]
            return

        # Already exists, append
        current_list = runtime.get_variable(variable_name)
        assert isinstance(current_list, list), f"{variable_name} does not refer to a list variable."
        list_copy = [*current_list]
        list_copy.append(self.value_to_append)
        runtime.set_variable(variable_name, Boolean, True, list_copy)
        self.new_list = list_copy


class AppendToListVariableNumber(Node):
    name = f"Append To List Variable (Number)"
    description = f"Append a Number value to a list of Numbers stored as a variable. If the list variable does not exist, it will be created with this value as its first entry."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#an-informal-introduction-to-python"]
    categories = ["Variables", "Primitive Data", "Lists"]
    color = constants.COLOR_NUMBER

    value_to_append = InputSocket(datatype=Number, name="Number To Append", description="The Number value to append to the list variable.")
    new_list = ListOutputSocket(datatype=Number, name="New List", description="The new value of the list variable with the item append.")
    field = InputField(default_value="", name="Variable Name")

    def run(self):
        variable_name = self.field.strip()
        assert len(variable_name) != 0, "Variable names cannot be empty."

        runtime = self._runtime
        if variable_name not in runtime.variables:
            # Does not exist, create the variable
            runtime.set_variable(variable_name, Number, True, [self.value_to_append])
            self.new_list = [self.value_to_append]
            return

        # Already exists, append
        current_list = runtime.get_variable(variable_name)
        assert isinstance(current_list, list), f"{variable_name} does not refer to a list variable."
        list_copy = [*current_list]
        list_copy.append(self.value_to_append)
        runtime.set_variable(variable_name, Number, True, list_copy)
        self.new_list = list_copy
