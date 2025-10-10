from graphex.sockets import OutputSocket
from graphex.node import Node, NodeType
from graphex.fields import InputField
from graphex.datatype import DataType
from graphex import constants
import typing
import json

Number = DataType(
    true_type=typing.Union[int, float], #type:ignore
    name="Number",
    description="A number (integer or floating point).",
    color=constants.COLOR_NUMBER,
    categories=["Data"],
)

String = DataType(true_type=str, name="String", description="A string (sequence of characters).", color=constants.COLOR_STRING, categories=["Data"])
Boolean = DataType(true_type=bool, name="Boolean", description="A Boolean (True or False).", color=constants.COLOR_BOOLEAN, categories=["Data"])
DataContainer = DataType(
    true_type=typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]], # type:ignore
    name="Data Container",
    description="A queryable object that contains arbitrary data. This may be a key-value map or list of values.",
    color=constants.COLOR_DATA_CONTAINER,
    categories=["Data"],
    constructor=lambda d: dict(d)
)

# Note: The 'Dynamic' type is a special type that has special defined behavior separate from the other types.
# It should be used where the type is for the socket is not known and could be any type, and the behavior of the node will depend on actual datatype.
# The 'Dynamic' type is limited to input sockets only.
Dynamic = DataType(true_type=typing.Any, name="Dynamic", description="Dynamic type.", color=constants.COLOR_DYNAMIC_DATATYPE, categories=["Data"]) # type:ignore




class NumberDataNode(Node):
    node_type = NodeType.DATA
    name = f"New Number"
    description = "Create a new number (integer or floating point)."
    categories = ["Data"]
    color = constants.COLOR_NUMBER

    output = OutputSocket(datatype=Number, name="Value", description="The number.")
    field = InputField(default_value=-2, name="Value", multiline=False, required=True, floating_label=False)

    def run(self):
        self.output = self.field


class StringDataNode(Node):
    node_type = NodeType.DATA
    name = f"New String"
    description = "Create a new string (sequence of characters)."
    categories = ["Data"]
    color = constants.COLOR_STRING

    output = OutputSocket(datatype=String, name="Value", description="The string.")
    field = InputField(default_value="", name="Value", multiline=True, required=False, floating_label=False)

    def run(self):
        self.output = self.field


class BooleanDataNode(Node):
    node_type = NodeType.DATA
    name = f"New Boolean"
    description = "Create a new boolean (True or False)."
    categories = ["Data"]
    color = constants.COLOR_BOOLEAN

    output = OutputSocket(datatype=Boolean, name="Value", description="The boolean.")
    field = InputField(default_value=False, name="Value", multiline=False, required=False, floating_label=False)

    def run(self):
        self.output = self.field


@Number.cast(to=String)
def number_to_string(value: typing.Union[int, float]) -> str:
    return str(value)


@Number.cast(to=Boolean)
def number_to_boolean(value: typing.Union[int, float]) -> bool:
    return bool(value)


@String.cast(to=Number)
def string_to_number(value: str) -> float:
    return float(value)


@String.cast(to=Boolean)
def string_to_boolean(value: str) -> bool:
    return bool(value)


@Boolean.cast(to=Number)
def boolean_to_number(value: bool) -> int:
    return int(value)


@Boolean.cast(to=String)
def boolean_to_string(value: bool) -> str:
    return str(value)


@DataContainer.cast(to=String)
def datacontainer_to_string(value: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]]) -> str:
    return json.dumps(value, indent=4, default=lambda x: str(x))


@DataContainer.cast(to=Boolean)
def datacontainer_to_boolean(value: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]]) -> bool:
    return bool(value)

