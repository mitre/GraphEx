import abc
import base64
import re
import typing
from enum import Enum

from graphex import exceptions
from graphex.fields import InputField
from graphex.graphfile import NodeMetadata, GraphInputMetadata
from graphex.sockets import LinkInputSocket, LinkOutputSocket, _BaseSocket
import dataclasses

if typing.TYPE_CHECKING:
    from graphex.graph import Graph
    from graphex.runtime import Runtime


class NodeType(Enum):
    ACTION = "action"
    """An action node."""

    DATA = "data"
    """A data node."""

    CAST = "cast"
    """A cast node."""

    GENERATOR = "generator"
    """A generator node."""

    COMMENT = "comment"
    """A node for humans to write comments in without effecting the graph"""


@dataclasses.dataclass
class NodeDynamicAttributes:
    sockets: typing.Optional[typing.List[_BaseSocket]]
    """Dynamic sockets on this node. These sockets will be merged into the node."""

    description: typing.Optional[str]
    """Dynamic description on this node. This will replace the original description of the node."""

    color: typing.Optional[str]
    """Dynamic color for this node. This will replace the original node color."""

    error: typing.Optional[str]
    """Any errors on the node."""


class Node(abc.ABC):
    """
    Parent class for all nodes in the graph.

    Subclasses are intended to the overwrite the ``run`` and (optionally) the ``run_next`` methods to handle the functionality of this node.
    """

    node_type: NodeType = NodeType.ACTION
    """The type of this node. This will affect how the node is displayed in the UI."""

    name: str
    """The name of this node."""

    description: str
    """The description of this node."""

    hyperlink: typing.List[str]
    """The link to external documentation (Python, Bash, etc)"""

    categories: typing.List[str]
    """The categories under which this node is sorted."""

    color: str
    """The color to use for this node's header."""

    textColor: str
    """The color to use for this node's text."""

    _is_template: bool = False
    """Whether this node should be considered a template. Template nodes are not loaded into the registry but instead used for inheritance by child nodes."""

    original_plugin: str
    """The plugin which provides this node (or GraphEx itself)"""

    is_inventory_node: bool = False
    "Set to True when this node is created by the inventory"

    inventory_value: typing.Optional[typing.Union[str, int, float, bool, typing.List[typing.Union[int, float, str, bool]]]] = None
    "The value for this node in the inventory. This value should change when the the yml file is edited and the server reserved."

    allows_new_inputs: bool = False
    "Whether this node allows for more input sockets to be added to it or not"

    # field: typing.Optional[InputField]

    def __init_subclass__(cls, include_backward_link: bool = True, include_forward_link: bool = True, is_template: bool = False):
        setattr(cls, "_is_template", is_template)

        # If any of the parent classes are templates, copy down the sockets.
        for base in cls.mro():
            if not issubclass(base, Node) or base == Node or not base._is_template:
                continue
            for key, value in base.__dict__.items():
                if not isinstance(value, _BaseSocket):
                    continue
                setattr(cls, key, value)

        if is_template:
            # Do not check template nodes
            return

        # catch plugins using reserved keywords
        has_name = False
        try:
            assert isinstance(cls.__dict__["name"], str), "Node 'name' must be a string (not a socket)"
            has_name = True
            if "node_type" in cls.__dict__:
                assert isinstance(cls.__dict__["node_type"], NodeType), "'node_type' is a reserved keyword"
            if "description" in cls.__dict__:
                assert isinstance(cls.__dict__["description"], str), "Node 'description' must be a string (not a socket)"
            assert isinstance(cls.__dict__["categories"], list), "Node 'categories' must be a list of strings (not a socket)"
            assert all(isinstance(i, str) for i in cls.__dict__["categories"]), "Node 'categories' must be a list of strings (not a socket)"
            assert isinstance(cls.__dict__["color"], str), "Node 'color' must be a string (not a socket)"
        except AssertionError as ae:
            err_msg = str(ae)
            if has_name:
                err_msg += f" [Erroring node's name is: {cls.__dict__['name']}]"
            raise exceptions.ReservedAttributeException(err_msg)

        # If there are no link sockets and this is an action node, add them
        if cls.node_type == NodeType.ACTION:
            if include_backward_link:
                setattr(cls, "_backward", LinkInputSocket(name="_backward", description="Backward Link (non-data connection)."))

            if include_forward_link:
                setattr(cls, "_forward", LinkOutputSocket(name="_forward", description="Forward Link (non-data connection)."))

        cls._check_sockets(None, None)

        # Set the default field
        if "field" not in cls.__dict__:
            setattr(cls, "field", None)

    def __init__(self, runtime: "Runtime", instance_metadata: NodeMetadata):
        self._instance_metadata: NodeMetadata = instance_metadata
        """The metadata for this node."""

        self._instance_metadata["original_plugin"] = self.original_plugin

        self._runtime: "Runtime" = runtime
        """The runtime for this node."""

        self._graph: "Graph" = self._runtime.graph
        """The graph for this node."""

        self._output_socket_values: typing.Dict[str, typing.Any] = {}
        """The output socket values for this node."""

        self._disabled_outputs: typing.Set[str] = set()
        """Set of disabled output sockets. If an output socket is disabled, any attempt to read from it will raise an error."""

        self.logger = self._runtime.logger
        """Logger for this node."""

        self._check_sockets(self._graph, instance_metadata)

    def clone(self) -> "Node":
        """
        Clone this node, including any internal state.
        """
        cloned_node = self.__class__(self._runtime, self._instance_metadata)
        cloned_node._output_socket_values = {**self._output_socket_values}
        cloned_node._disabled_outputs = set([*self._disabled_outputs])
        return cloned_node

    def forward(self, socket_name: typing.Optional[str] = None) -> typing.List[NodeMetadata]:
        """
        Get the next node(s) in the graph from this node (based on output link sockets).

        :param socket_name: The name of the link output socket for which to get forward node(s). If ``None``, all link output sockets are used (i.e. get all forward nodes).
        """
        return self._graph.get_forward(self._instance_metadata, socket_name=socket_name)

    @abc.abstractmethod
    def run(self):
        """
        Run this node. This function will simply perform some functionality using this node's input sockets.

        This function is expected to populate the values of this node's output socket, or raise an exception if that is not possible.
        """
        raise NotImplementedError

    def run_next(self):
        """
        Function to trigger execution of the next nodes in the graph. Overwrite this function to implement custom control flow within the graph.
        """
        for nextnode in self.forward():
            self._runtime.execute_node(nextnode)

    @classmethod
    def dynamic_attributes(cls, graph: "Graph", instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        """
        Dynamic attributes on this node. Defining this method on a subclass will make this node dynamic, meaning
        that attributes on this node (e.g. the sockets) will update based on the returned value from this method.
        """
        return NodeDynamicAttributes(None, None, None, None)

    @property
    def id(self) -> str:
        """The ID of the node."""
        return self._instance_metadata["id"]

    def get_output_socket_value(self, socket_name: str) -> typing.Any:
        """
        Get the value of an output socket in this runtime.

        :param socket_name: The name of the output socket.

        :returns: The value of the socket.
        :throws: If the socket does not exist or if the socket has no value.
        """
        if self.output_socket_is_disabled(socket_name):
            raise RuntimeError(f"{str(self)}: Value for output socket '{socket_name}' cannot be queried as the socket is flagged as disabled.")
        socket = self.get_output(socket_name, self._graph, self._instance_metadata)
        if socket_name not in self._output_socket_values or not socket.datatype:
            raise RuntimeError(f"{str(self)}: Output socket '{socket_name}' does not have a value")
        value = self._output_socket_values[socket_name]
        socket.datatype.assert_type(value, is_list=socket.is_list)
        return value

    def output_socket_has_value(self, socket_name: str) -> bool:
        """
        Check if an output socket has a value.

        :param socket_name: The name of the output socket.

        :returns: A boolean whether this socket has a value.
        """
        try:
            self.get_output_socket_value(socket_name)
            return True
        except:
            return False

    def set_output_socket_value(self, name: str, value: typing.Any):
        """Set the output value for a socket on this node."""
        self.enable_output_socket(name)
        socket = self.get_output(name, self._runtime.graph, self._instance_metadata)
        if socket.datatype is None:
            raise RuntimeError(f"{str(self)}: Cannot set the value of socket as it is not associated with a DataType")
        socket.datatype.assert_type(value, is_list=socket.is_list)
        self._output_socket_values[name] = value

    def disable_output_socket(self, name: str):
        """
        Disable an output socket. The socket will be enabled again when a value is set or ``enable_output_socket`` is called.

        A disabled output socket will raise an error when another node attempts to read its value. This may be used to mark a socket as "not applicable" given the current state of
        this node or graph.

        Note: Provide a useful description to the appropriate output socket such that the user will know under what conditions the socket may be disabled at runtime.

        :param name: The name of the socket to disable.
        """
        self._disabled_outputs.add(name)

    def enable_output_socket(self, name: str):
        """
        Enable a disabled output socket. If the socket is not disabled, this will do nothing.

        :param name: The name of the socket to enable.
        """
        try:
            self._disabled_outputs.remove(name)
        except KeyError:
            pass

    def output_socket_is_disabled(self, name: str) -> bool:
        """
        Check if an output socket is disabled.

        :param name: The name of the socket.

        :return: A boolean whether the socket is disabled.
        """
        return name in self._disabled_outputs

    def defer(self, func: typing.Callable, insert_back: bool = False):
        """
        Defer a function call until the runtime for this node ends. This function runs when the runtime exits, either successfully or with an exception.
        This is typically used for any clean-up steps that need to always be performed regardless of the runtime exit status.
        All deferred functions will be run in the order of most recently added (even if one previously failed).

        :param func: The function to call.
        :param insert_back: Add the function to be executed to the back of the list (i.e. executed last) instead of the front.
        """
        self._runtime.defer(func, insert_back=insert_back, origin_node=self)

    @classmethod
    def sockets(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]) -> typing.List[_BaseSocket]:
        """
        All sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        sockets = [socket for socket in cls.__dict__.values() if isinstance(socket, _BaseSocket)]
        if graph and instance_metadata:
            if (
                graph.name
                and graph.name in graph.validation_cache.dynamic_sockets
                and instance_metadata["id"] in graph.validation_cache.dynamic_sockets[graph.name]
            ):
                sockets = cls._merge_sockets(sockets, graph.validation_cache.dynamic_sockets[graph.name][instance_metadata["id"]])
            elif graph.name and graph.validation_cache:
                if graph.name not in graph.validation_cache.dynamic_sockets:
                    graph.validation_cache.dynamic_sockets[graph.name] = {}
                if instance_metadata["id"] not in graph.validation_cache.dynamic_sockets[graph.name]:
                    graph.validation_cache.dynamic_sockets[graph.name][instance_metadata["id"]] = []
                dynamic_sockets = cls.dynamic_attributes(graph, instance_metadata).sockets or []
                graph.validation_cache.dynamic_sockets[graph.name][instance_metadata["id"]] = dynamic_sockets
                sockets = cls._merge_sockets(sockets, dynamic_sockets)
            else:
                sockets = cls._merge_sockets(sockets, cls.dynamic_attributes(graph, instance_metadata).sockets or [])

        return sockets

    @classmethod
    def _merge_sockets(cls, default_sockets: typing.List[_BaseSocket], dynamic_sockets: typing.List[_BaseSocket]) -> typing.List[_BaseSocket]:
        """
        Merge dynamic sockets into a list of default sockets. Since dynamic sockets may overwrite a socket on its node by reusing the same
        name, it is not correct to simply extend the default list of sockets with the list of dynamic sockets. Instead, the list
        must be extended and then duplicates removed so that the latest-added socket takes priority.

        :param default_sockets: The default sockets (base list) to merge into.
        :param dynamic_sockets: The dynamic sockets to merge into the default_sockets.

        :returns: The new list of sockets.
        """
        sockets = [*default_sockets, *dynamic_sockets]
        merged_sockets = []
        for i, socket in enumerate(sockets):
            if any([s.name == socket.name and s.is_input == socket.is_input for s in sockets[i + 1 :]]):
                continue
            merged_sockets.append(socket)
        return merged_sockets

    @classmethod
    def inputs(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        """
        All input sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        return [socket for socket in cls.sockets(graph, instance_metadata) if socket.is_input]

    @classmethod
    def data_inputs(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        """
        All data input sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        return [socket for socket in cls.inputs(graph, instance_metadata) if not socket.is_link]

    @classmethod
    def link_inputs(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        """
        All link input sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        return [socket for socket in cls.inputs(graph, instance_metadata) if socket.is_link]

    @classmethod
    def get_input(cls, name: str, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]) -> _BaseSocket:
        """
        Get an input socket by socket name (not class attribute name).

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        found = next(iter([socket for socket in cls.inputs(graph, instance_metadata) if socket.name == name]), None)
        if not found:
            raise ValueError(f"Input socket '{name}' does not exist on node '{cls.name}'")
        return found

    @classmethod
    def outputs(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        """
        All output sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        return [socket for socket in cls.sockets(graph, instance_metadata) if not socket.is_input]

    @classmethod
    def data_outputs(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        """
        All data output sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        return [socket for socket in cls.outputs(graph, instance_metadata) if not socket.is_link]

    @classmethod
    def link_outputs(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        """
        The link output sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        return [socket for socket in cls.outputs(graph, instance_metadata) if socket.is_link]

    @classmethod
    def get_output(
        cls,
        name: str,
        graph: typing.Optional["Graph"],
        instance_metadata: typing.Optional[NodeMetadata],
    ) -> _BaseSocket:
        """
        Get an output socket by socket name (not class attribute name).

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        found = next(iter([socket for socket in cls.outputs(graph, instance_metadata) if socket.name == name]), None)
        if not found:
            raise ValueError(f"Output socket '{name}' does not exist on node '{cls.name}'")
        return found

    @classmethod
    def has_link_sockets(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]) -> bool:
        """Whether this node has any link sockets (input or output)."""
        return len([socket for socket in cls.sockets(graph, instance_metadata) if socket.is_link]) > 0

    @classmethod
    def get_field(cls) -> typing.Optional[InputField]:
        """Get the field object on this node."""
        return cls.__dict__.get("field", None)

    def log_prefix(self) -> str:
        """
        Log prefix for this node. May be overwritten by child classes to change the prefix for all logs written by this node.
        """
        return f"[{self.name}] "

    def log(self, msg: str, level: str = "INFO", skip_printing_level: bool = False):
        msg_to_write = self.log_prefix() + msg
        # Don't print detected as purely whitespace (including whitespace characters)
        if not re.search("^\s*$", msg_to_write):
            self.logger.write(msg_to_write, level=level.strip().upper(), skip_printing_level=skip_printing_level)

    def debug(self, msg: str):
        self.log(msg, "DEBUG")

    def log_debug(self, msg: str):
        self.log(msg, "DEBUG")

    def log_notice(self, msg: str):
        self.log(msg, "NOTICE")

    def log_warning(self, msg: str):
        self.log(msg, "WARNING")

    def log_error(self, msg: str):
        self.log(msg, "ERROR")

    def log_critical(self, msg: str):
        self.log(msg, "CRITICAL")

    def log_image(self, base64_str: typing.Optional[str], path_to_image: typing.Optional[str]):
        """
        Logs an image to the terminal. Will appear as a clickable link in the UI. Will appear as a base64 string on the CLI and in the logs. Provide one of: a base64 string representing the image or the path to the image to convert to a base64 string. Will use the 'base64_str' parameter if both are provided.

        :param base64_str: A base64 string representing the image. This function adds the prefix: 'data:image/jpeg;base64,' to the value you provide.
        :param path_to_image: The path to an image to convert to a base64 string.
        """
        if base64_str:
            self.log("data:image/jpeg;base64," + base64_str, "IMAGE")
        else:
            path_to_image = path_to_image if path_to_image else ""
            with open(path_to_image, "rb") as file:
                encoded_string = base64.b64encode(file.read())
                self.log("data:image/jpeg;base64," + encoded_string.decode("ascii"), "IMAGE")

    @classmethod
    def validate_instance_metadata(cls, graph: "Graph", instance_metadata: NodeMetadata) -> str:
        """
        Check that the given node instance metadata is valid according to this node's definitions. Raises errors when a validation fails.

        :param graph: The Graph object that this instance metadata belongs to.
        :param instance_metadata: The instance metadata.

        :return: The _backward link socket for validation that there are no duplicate _backward sockets or None if the _backward socket was not found
        """
        # Check this node for a dynamic error
        error_message = cls.dynamic_attributes(graph, instance_metadata).error
        if error_message:
            err_prefix = "Dynamic node error "
            if instance_metadata["name"].strip().lower() == "execute graph" and "fieldValue" in instance_metadata:
                err_prefix += f"(Subgraph Name: {instance_metadata['fieldValue']})"
            err_prefix += ":"
            raise exceptions.NodeUsageError(instance_metadata["name"], instance_metadata["id"], f"{err_prefix} {error_message}")

        # Get all sockets up-front to avoid having to recompute the dynamic sockets repeatedly
        all_sockets: typing.List[_BaseSocket] = cls.sockets(graph, instance_metadata)

        # Ensure input sockets align
        defined_input_sockets = set([socket.name for socket in all_sockets if socket.is_input])
        metadata_input_sockets = set([socket["name"] for socket in instance_metadata.get("inputs", [])])

        if defined_input_sockets != metadata_input_sockets:
            raise exceptions.NodeMisalignedSockets(cls.name, instance_metadata["id"], list(defined_input_sockets), list(metadata_input_sockets), is_input=True)

        backward_connection_name = ""

        # Validate each socket
        for socket_metadata in instance_metadata.get("inputs", []):
            name = socket_metadata["name"]
            matching_socket = next(iter([socket for socket in all_sockets if socket.is_input and socket.name == name]), None)
            if not matching_socket:
                raise ValueError(f"Input socket '{name}' does not exist on node '{cls.name}'")
            matching_socket.validate_instance_metadata(graph, instance_metadata, socket_metadata)
            if name == "_backward" and "connections" in socket_metadata:
                 backward_connection_name = socket_metadata["connections"][0]
            
        return backward_connection_name

    @classmethod
    def is_dynamic(cls):
        """Whether this is a dynamic node (is dependent on graph context)."""
        return "dynamic_attributes" in cls.__dict__

    @classmethod
    def metadata(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        field = cls.get_field()
        metadata = {
            "type": cls.node_type.value,
            "name": cls.name,
            "description": cls.description,
            "hyperlink": cls.hyperlink if hasattr(cls, "hyperlink") else [""],
            "color": cls.color,
            "textColor": cls.textColor if hasattr(cls, "textColor") else "",
            "sockets": [],
            "categories": cls.categories,
            "field": field.metadata() if field else None,
            "dynamic": cls.is_dynamic(),
            "error": "",
            "original_plugin": cls.original_plugin,
            "isInventoryNode": cls.is_inventory_node,
            "inventoryValue": cls.inventory_value,
            "allowsNewInputs": cls.allows_new_inputs
        }

        sockets = cls.sockets(None, None)

        if cls.is_dynamic() and graph and instance_metadata:
            try:
                attrs = cls.dynamic_attributes(graph, instance_metadata)
                sockets = cls._merge_sockets(sockets, attrs.sockets or [])
                metadata["description"] = attrs.description or cls.description
                metadata["color"] = attrs.color or cls.color
                metadata["error"] = attrs.error or ""
            except Exception as e:
                metadata["error"] = str(e)

        metadata["sockets"] = [socket.metadata() for socket in sockets]
        
        return metadata

    @classmethod
    def _check_sockets(cls, graph: typing.Optional["Graph"], instance_metadata: typing.Optional[NodeMetadata]):
        """Assert that this node obeys proper socket rules for its node type."""
        if cls.node_type != NodeType.ACTION and cls.has_link_sockets(graph, instance_metadata):
            raise RuntimeError(f"{cls.__name__}: Non-action nodes cannot have link sockets.")

        if (cls.node_type == NodeType.DATA or cls.node_type == NodeType.GENERATOR) and len(cls.inputs(graph, instance_metadata)) != 0:
            raise RuntimeError(f"{cls.__name__}: Node cannot have input sockets.")

    def __str__(self):
        return f"[{self.name} ({self.id})]"

    def __repr__(self):
        return f"[{self.name} ({self.id})]"
