import typing
import sys

if sys.version_info < (3, 11):
    from typing_extensions import TypedDict, NotRequired, List, Union
else:
    from typing import TypedDict, NotRequired, List, Union


FILE_EXTENSION = ".gx"


class SocketMetadata(TypedDict):
    name: str
    """The name for this socket."""

    connections: NotRequired[List[str]]
    """The connections for this socket (NodeID::SocketName)."""

    fieldValue: NotRequired[typing.Union[str, int, float, bool, typing.List[str], typing.List[int], typing.List[float], typing.List[bool]]]
    """The value for this socket's input field."""

    variableName: NotRequired[str]
    """Name of the variable that this socket derives its value from. (Input sockets only)"""

    graphInputName: NotRequired[str]
    """Name of the graph input that this socket derives its value from. (Input sockets only)"""

class GraphInputValueMetadata(TypedDict):
    value: NotRequired[typing.Any]
    fromSecret: NotRequired[str]
    fromConfig: NotRequired[str]
    childValues: typing.Dict[str,'GraphInputValueMetadata']
    datatype: str # datatype only really needs to be defined of childValues is not empty
    
class NodeMetadata(TypedDict):
    name: str
    """The name of this node."""

    id: str
    """Unique ID to identify this node within this graph."""

    xy: str
    """The X,Y position of the node."""

    original_plugin: str
    """The plugin which provides this node (or GraphEx itself)"""

    inputs: NotRequired[List[SocketMetadata]]
    """Input sockets on this node."""

    fieldValue: NotRequired[typing.Union[str, int, float, bool]]
    """The value for this node's input field."""

    color: NotRequired[str]
    """Custom color of this node"""

    textColor: NotRequired[str]
    """Custom text color of this node"""

    disabledVariableOutputs: NotRequired[List[str]]
    """The outputs on this node that the user specified should not be saved to a variable (only for VariableOutputSockets)"""

    requiresInventory: NotRequired[bool]
    """Whether or not this node needs an inventory to be loaded to use it"""

class UIOffsetsMetadata(TypedDict):
    x: float
    y: float


class UIMetadata(TypedDict):
    scale: float
    """Editor scale (zoom in/out)."""

    offsets: UIOffsetsMetadata
    """Editor content offsets."""


class GraphInputMetadata(TypedDict):
    name: str
    """Name of this input."""

    datatype: str
    """Name of the data type for this input."""

    isList: NotRequired[bool]
    """Whether this is a list input."""

    isPassword: NotRequired[bool]
    """Whether this string contains a password or not."""

    description: NotRequired[str]
    """Description for this input."""

    defaultValue: NotRequired[Union[str, float, int, bool, List[Union[str, float, int, bool]]]]
    """Default value for this input."""

    enumOptions: NotRequired[List[str]]
    """List of enum values to use for input"""


class GraphOutputMetadata(TypedDict):
    name: str
    """Name of this output."""

    datatype: str
    """Name of the data type for this output."""

    isList: NotRequired[bool]
    """Whether this is a list output."""

    description: NotRequired[str]
    """Description for this output."""


class GraphFile(TypedDict):
    nodes: List[NodeMetadata]
    """Nodes in the graph."""

    ui: UIMetadata
    """UI Metadata."""

    inputs: NotRequired[List[GraphInputMetadata]]
    """Inputs to this graph."""

    outputs: NotRequired[List[GraphOutputMetadata]]
    """Outputs to this graph."""

    description: NotRequired[str]
    """The description for this graph."""
