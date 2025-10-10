from graphex.datatype import DataType, exceptions
from graphex.graphfile import GraphInputMetadata
from graphex.runtime import Runtime
import abc
import typing

if typing.TYPE_CHECKING:
    from graphex import GraphConfig

T = typing.TypeVar("T")

PRIMITIVES = []


class CompositeInputValue:
    value: typing.Union["CompositeInputValue", typing.Any]
    name: str
    defaultValue: bool


class subGraphInput(typing.Generic[T]):

    def __init__(
        self,
        name: str,
        datatype: DataType[T],
        description: str,
        defaultValue: typing.Optional[T] = None,
    ):
        self.__name = name
        self.__datatype = datatype
        self.__description = description
        self.__defaultValue = defaultValue

    @property
    def datatype(self) -> str:
        return self.__datatype.name

    @property
    def inputGraphMetadata(self) -> GraphInputMetadata:

        metadata: GraphInputMetadata = {
            "name": self.__name,
            "datatype": self.__datatype.name,
            "isList": False,
            "isPassword": False,
            "description": self.__description,
        }

        # Empty string needs to be allowed for defaultValues that are optional
        if self.__defaultValue or self.__defaultValue == "":
            metadata["defaultValue"] = self.__defaultValue

        return metadata

    def __get__(self, obj: "CompositeGraphInput", _) -> T:
        if not self.__datatype:
            raise Exception

        if self.__name not in obj.graphInputValues:
            if self.__defaultValue is None:
                raise Exception

            return self.__defaultValue
        return obj.graphInputValues[self.__name]


class subGraphListInput(subGraphInput, typing.Generic[T]):

    def __init__(
        self,
        name: str,
        datatype: DataType[T],
        description: str,
        defaultValue: typing.Optional[T] = None,
    ):

        super().__init__(name, datatype, description, defaultValue)

    @property
    def inputGraphMetadata(self):

        metadata = super().inputGraphMetadata

        metadata["isList"] = True

        return metadata

    def __get__(self, obj: "CompositeGraphInput", _) -> typing.List[T]:
        return super().__get__(obj, _)


class subGraphEnumInput(subGraphInput, typing.Generic[T]):

    def __init__(
        self,
        name: str,
        datatype: DataType[T],
        description: str,
        enumMap: typing.Dict[str, T],
        defaultValue: typing.Optional[T] = None,
    ):

        super().__init__(name, datatype, description, defaultValue)

        self.enumMap = enumMap

    @property
    def inputGraphMetadata(self):

        metadata = super().inputGraphMetadata

        metadata["enumOptions"] = [key for key in self.enumMap.keys()]

        return metadata

    def __get__(self, obj: "CompositeGraphInput", _) -> T:
        key = super().__get__(obj, _)
        return self.enumMap[key]


class subGraphEnumListInput(subGraphInput, typing.Generic[T]):
    def __init__(
        self,
        name: str,
        datatype: DataType[T],
        description: str,
        enumMap: typing.Dict[str, T],
        defaultValue: typing.Optional[T] = None,
    ):

        super().__init__(name, datatype, description, defaultValue)

        self.enumMap = enumMap

    @property
    def inputGraphMetadata(self):

        metadata = super().inputGraphMetadata

        metadata["isList"] = True
        metadata["enumOptions"] = [key for key in self.enumMap.keys()]

        return metadata

    def __get__(self, obj: "CompositeGraphInput", _) -> T:
        key = super().__get__(obj, _)
        return self.enumMap[key]


class CompositeGraphInput(abc.ABC):
    """
    Metadata about a data type.

    :param true_type: The underlying 'Python Type' for this data type. This should be either a single type (e.g. ``int``) or a Union of types (e.g. ``typing.Union[int, float]``).
    :param name: The name to use for this type in the UI.
    :param description: The description to use for this type in the UI.
    :param color: The color to use for this type in the UI.
    :param category: The categories under which to sort this type in the UI.
    :param inputDataType: In this case true_type,color and category are pulled from this object. Name and description is still from parameters.
    """

    datatype: DataType
    _runtime: Runtime
    """Populated after composite inputs are loaded via the package and before the graph runs"""

    def __init__(
        self,
        graphInputValues: typing.Dict[str, typing.Any],
    ):
        self.graphInputValues = graphInputValues

    def __init_subclass__(cls):
        try:
            if "node_type" in cls.__dict__:
                assert isinstance(
                    cls.__dict__["datatype"], DataType
                ), "'datatype' is a reserved keyword"

        except AssertionError as ae:
            err_msg = str(ae)
            raise exceptions.ReservedAttributeException(err_msg)

    @classmethod
    def subInputs(cls) -> typing.List[subGraphInput]:
        """
        All input sockets on this node.

        If ``graph`` and ``instance_metadata`` are provided, this will also include dynamic sockets.
        """
        return [
            socket
            for socket in cls.__dict__.values()
            if isinstance(socket, subGraphInput)
        ]

    @classmethod
    def inputMetadata(cls) -> typing.List[GraphInputMetadata]:
        return [socket.inputGraphMetadata for socket in cls.subInputs()]

    @classmethod
    def metadata(cls):
        return {
            "datatype": cls.datatype.name,  # type: ignore
            "InputMetadata": cls.inputMetadata(),
        }

    @abc.abstractmethod
    def constructInput(self):
        raise NotImplementedError
