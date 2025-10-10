from graphex.sockets.base import _BaseSocket
from graphex.datatype import DataType
import typing

if typing.TYPE_CHECKING:
    from graphex.node import Node

T = typing.TypeVar("T")


class OutputSocket(_BaseSocket, typing.Generic[T]):
    """
    A standard output socket on a node.

    :param datatype: The DataType for this output socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    """

    def __init__(self, datatype: DataType[T], name: str, description: str):
        super().__init__(is_input=False, is_optional=False, is_list=False, datatype=datatype, name=name, description=description, input_field=None)

    def __get__(self, obj: "Node", owner) -> T:
        return super().__get__(obj, owner)


class ListOutputSocket(_BaseSocket, typing.Generic[T]):
    """
    An output socket that outputs a list of values.

    :param datatype: The DataType for this output socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    """

    def __init__(self, datatype: DataType[T], name: str, description: str):
        super().__init__(is_input=False, is_optional=False, is_list=True, datatype=datatype, name=name, description=description, input_field=None)

    def __get__(self, obj: "Node", owner) -> typing.List[T]:
        return super().__get__(obj, owner)


class LinkOutputSocket(_BaseSocket):
    """
    A link (non-data) output socket. This socket will not be associated with any data type and thus will not carry a value. This only serves
    the purpose of connecting nodes without passing data.

    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    """

    def __init__(self, name: str, description: str):
        super().__init__(is_input=False, is_optional=False, is_list=False, datatype=None, name=name, description=description, input_field=None)


class VariableOutputSocket(_BaseSocket, typing.Generic[T]):
    """
    A standard output socket on a node that also saves (or overwrites) the value to variable of the same name as the output socket.

    :param datatype: The DataType for this output socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    :param save_enabled: Whether to save the output value to a variable or not
    """

    def __init__(self, datatype: DataType[T], name: str, description: str):
        super().__init__(is_input=False, is_optional=False, is_list=False, datatype=datatype, name=name, description=description, input_field=None)

    def __get__(self, obj: "Node", owner) -> T:
        return super().__get__(obj, owner)
    
    def metadata(self):
        metadata = super().metadata()
        metadata['allowsVariable'] = True
        return metadata
    
    def set_value(self, obj: "Node", value: typing.Any):
        """
        Set the value of this socket on the given node.
        Also assigns the name of this socket to a variable (if the datatype of the socket is not 'None').
        """
        return self.__set__(obj, value)

    def __set__(self, obj: "Node", value: typing.Any):
        if not self.datatype:
            raise AttributeError(f"Cannot get the value of link output sockets ({self.name} on node {obj})")

        obj.set_output_socket_value(self.name, value)
        
        if ('disabledVariableOutputs' in obj._instance_metadata) and (self.name in obj._instance_metadata['disabledVariableOutputs']):
            return
        obj._runtime.set_variable(self.name, self.datatype, self.is_list, value)


class ListVariableOutputSocket(_BaseSocket, typing.Generic[T]):
    """
    A standard output socket on a node that also saves (or overwrites) the value to variable of the same name as the output socket.

    :param datatype: The DataType for this output socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    :param save_enabled: Whether to save the output value to a variable or not
    """

    def __init__(self, datatype: DataType[T], name: str, description: str):
        super().__init__(is_input=False, is_optional=False, is_list=True, datatype=datatype, name=name, description=description, input_field=None)

    def __get__(self, obj: "Node", owner) -> typing.List[T]:
        return super().__get__(obj, owner)
    
    def metadata(self):
        metadata = super().metadata()
        metadata['allowsVariable'] = True
        return metadata
    
    def set_value(self, obj: "Node", value: typing.Any):
        """
        Set the value of this socket on the given node.
        Also assigns the name of this socket to a variable (if the datatype of the socket is not 'None').
        """
        return self.__set__(obj, value)

    def __set__(self, obj: "Node", value: typing.Any):
        if not self.datatype:
            raise AttributeError(f"Cannot get the value of link output sockets ({self.name} on node {obj})")

        obj.set_output_socket_value(self.name, value)
        
        if ('disabledVariableOutputs' in obj._instance_metadata) and (self.name in obj._instance_metadata['disabledVariableOutputs']):
            return
        obj._runtime.set_variable(self.name, self.datatype, self.is_list, value)
