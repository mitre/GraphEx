import typing
import typeguard
from graphex import exceptions

if typing.TYPE_CHECKING:
    from graphex.node import Node

T = typing.TypeVar("T")
U = typing.TypeVar("U")


class DataType(typing.Generic[T]):
    """
    Metadata about a data type.

    :param true_type: The underlying 'Python Type' for this data type. This should be either a single type (e.g. ``int``) or a Union of types (e.g. ``typing.Union[int, float]``).
    :param name: The name to use for this type in the UI.
    :param description: The description to use for this type in the UI.
    :param color: The color to use for this type in the UI.
    :param category: The categories under which to sort this type in the UI.
    :param constructor: A function that can be passed in to construct the python object for this datatype
    """

    def __init__(self, true_type: typing.Type[T], name: str, description: str, color: str, categories: typing.List[str], constructor: typing.Optional[typing.Callable] = None):
        self.true_type = true_type
        """The underlying 'Python Type' for this data type."""

        self.name = name
        """The name to use for this type in the UI."""

        self.description = description
        """The description to use for this type in the UI."""

        self.color = color
        """The color to use for this type in the UI."""

        self.categories = categories
        """The categories under which to sort this type in the UI."""

        self._casts: typing.Dict[DataType, typing.Callable[[T], typing.Any]] = {}
        """Cast functions available to this data type."""

        if constructor is not None:
            self.construct = constructor

    def cast(self, to: "DataType[U]") -> typing.Callable[[typing.Callable[[T], U]], typing.Callable[[T], U]]:
        """
        Add a cast from for this data type to another data type. This should be used as a decorator for a function that accepts this data type as
        as parameter and returns the cast data type.

        :param to: The data type that this function casts to.
        """

        def handler(func: typing.Callable[[T], U]):
            if to in self._casts:
                raise RuntimeError(f"A cast function already exists from DataType {self.name} to {to.name}")
            self._casts[to] = func
            return func

        return handler

    def get_type(self) -> typing.Type[T]:
        """Get the underyling 'Python Type' for this data type."""
        return self.true_type

    def check_type(self, value: typing.Any, is_list: bool = False) -> bool:
        """
        Check the type of a value to ensure it is compatible with this data type.

        :param value: The value to type check.
        :param is_list: Whether this should be treated as a list of values.

        :return: Whether this value satisfies type checking.
        """
        try:
            if is_list:
                if not isinstance(value, list):
                    return False
                for item in value:
                    typeguard.check_type(item, self.true_type)
            else:
                typeguard.check_type(value, self.true_type)
            return True
        except typeguard.TypeCheckError:
            return False

    def assert_type(self, value: typing.Any, is_list: bool = False):
        """
        Assert that the type of a value is compatible with this data type.

        :param value: The value to type check.
        :param is_list: Whether this should be treated as a list of values.

        :raises: When this type check fails.
        """
        if not self.check_type(value, is_list=is_list):
            if is_list:
                raise TypeError(f"Value '{value}' (type: {type(value)}) is not compatible with a list of DataType '{self.name}' ({self.true_type})")
            raise TypeError(f"Value '{value}' (type: {type(value)}) is not compatible with DataType '{self.name}' ({self.true_type})")

    def create_all_cast_nodes(self) -> typing.List[typing.Type["Node"]]:
        """Create all cast node classes for this data type."""
        nodes = []
        for to in self._casts.keys():
            nodes.extend(self.create_cast_nodes(to))
        return nodes

    def create_cast_nodes(self, to: "DataType") -> typing.List[typing.Type["Node"]]:
        """Create cast node classes for a target data type."""
        if to not in self._casts:
            raise ValueError(f"{self.name} has no cast function for casting to {to.name}")

        from graphex.node import Node, NodeType
        from graphex.sockets import InputSocket, ListInputSocket, ListOutputSocket, OutputSocket

        class CastNode(Node):
            node_type = NodeType.CAST
            name = f"{self.name} To {to.name}"
            description = f"Convert {self.name} To {to.name}"
            categories = [*self.categories, "Cast", self.name]
            color = self.color

            input = InputSocket(datatype=self, name="Cast From", description=f"The {self.name} to cast from.")
            output = OutputSocket(datatype=to, name="Cast To", description=f"The {to.name} to cast to.")

            def run(_obj):
                _obj.output = self._casts[to](_obj.input)

        class CastNodeList(Node):
            node_type = NodeType.CAST
            name = f"{self.name} (List) To {to.name} (List)"
            description = f"Convert a list of '{self.name}' values to a list of '{to.name}' values."
            categories = [*self.categories, "Cast", self.name]
            color = self.color

            input = ListInputSocket(datatype=self, name="Cast From", description=f"The {self.name} list to cast from.")
            output = ListOutputSocket(datatype=to, name="Cast To", description=f"The {to.name} list to cast to.")

            def run(_obj):
                _obj.output = [self._casts[to](x) for x in _obj.input]

        return [CastNode, CastNodeList]

    def create_list_nodes(self) -> typing.List[typing.Type["Node"]]:
        """Create all list-related nodes for this data type."""

        from graphex.node import Node, NodeType
        from graphex.data import primitives
        from graphex.sockets import ListOutputSocket

        if self == primitives.Dynamic:
            return []
        
        class EmptyList(Node, include_forward_link=False):
            node_type = NodeType.GENERATOR
            name = f"Empty List ({self.name})"
            description = f"Create/Get a new/empty {self.name} list."
            categories = ["Lists", "Create", self.name]
            color = self.color

            value = ListOutputSocket(datatype=self, name="Value", description="The empty list.")

            def run(_obj):
                _obj.value = []

        return [EmptyList]

    def create_nodes(self) -> typing.List[typing.Type["Node"]]:
        """Create all dynamic nodes associated with this data type."""
        return [*self.create_all_cast_nodes(), *self.create_list_nodes()]

    def metadata(self):
        return {"name": self.name, "description": self.description, "color": self.color}

    def __str__(self):
        return f"<{self.name} - {self.true_type}>"

    def construct(self, *arg):
        """
        Can be used by object datatypes to construct data in a duplicatable way.
        """
        pass
