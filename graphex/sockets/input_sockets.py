from graphex.sockets.base import _BaseSocket
from graphex.datatype import DataType
import typing
from graphex import exceptions

if typing.TYPE_CHECKING:
    from graphex.node import Node
    from graphex.graph import Graph
    from graphex.graphfile import SocketMetadata, NodeMetadata

T = typing.TypeVar("T")


class InputSocket(_BaseSocket, typing.Generic[T]):
    """
    A standard input socket on a node.

    :param datatype: The DataType for this input socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    :param input_field: Default value for the input field on this socket (String/Number/Boolean data types only)
    """

    def __init__(self, datatype: DataType[T], name: str, description: str, input_field: typing.Optional[T] = None):
        super().__init__(is_input=True, is_optional=False, is_list=False, datatype=datatype, name=name, description=description, input_field=input_field)

    def __get__(self, obj: "Node", owner) -> T:
        return super().__get__(obj, owner)
    

class EnumInputSocket(_BaseSocket, typing.Generic[T]):
    """
    A standard input socket on a node.

    :param datatype: The DataType for this input socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    :param enum_members: Either a list of objects or a dictionary mapping strings to objects representing the enum members. 
                         If a list, enum will be keyed by string value. keys must be case insensitive i.e. be unique when all uppercase.
                         If datatype is String, enum_members must be a list.
    :param input_field: Default value for the input field on this socket (String/Number/Boolean data types only)
    """

    def __init__(self, datatype: DataType[T], name: str, description: str, enum_members: typing.Union[typing.List[T], typing.Dict[str, T]], input_field: typing.Optional[T] = None):
        from graphex import String

        # I made a consensus choise to not force the keys to be upper case.
        # This is because it might be important in certain cases that keys 'appear' in the right case format.
        # Also, if we switched certain nodes to be enum forcing values to be uppercase can break things (e.g. the Log node has preset values in lowercase).
        # Keys must be unique as if they were uppercase though

        if datatype==String and not isinstance(enum_members,list):
            raise ValueError("If datatype is 'String' enum_members must be a list")
        
        if isinstance(enum_members, dict):
            self.enum_members = enum_members
        elif isinstance(enum_members, list):
            self.enum_members = {str(member): member for member in enum_members}
        else:
            raise ValueError("enum_members must be either a list of objects or a dictionary mapping strings to objects")

        if len(set([m.upper() for m in self.enum_members]))!=len(self.enum_members.keys()):
            raise ValueError(f"enum member keys must be case insenitive unique {', '.join(self.enum_members.keys())}")

        if input_field and input_field not in self.enum_members.values():
            raise ValueError(f"Socket '{name}': Socket input field '{input_field}' must be a part of enum members {', '.join(self.enum_members.keys())}")

        super().__init__(is_input=True, is_optional=False, is_list=False, datatype=datatype, name=name, description=description, input_field=input_field)

    def __get__(self, obj: "Node", owner) -> T:
        from graphex import String
        # Input socket
        metadata = next(iter([s for s in obj._instance_metadata.get("inputs", []) if s["name"] == self.name]), None)
        if not metadata:
            raise RuntimeError(f"Input socket '{self.name}' does not exist on node {obj.name}")
        
        value = None
        # This is value set from the dropdown; it must be a string type, so we check against the map.
        if 'fieldValue' in metadata:
            match = next((en for en in self.enum_members if en.upper() == str(metadata['fieldValue']).upper()), None)
            if not match:
                raise exceptions.SocketError(socket_name=self.name, node_name=obj.name, id=obj.id, msg=f"fieldValue '{metadata['fieldValue']}' must be one of these values [{','.join(self.enum_members.keys())}]")
            return self.enum_members[match]
        
        # This is a value from a connection. Grab it and test if it is in the member list
        value = super().__get__(obj, owner)

        if self.datatype!=String:
            if not value in self.enum_members.values():
                raise exceptions.SocketError(socket_name=self.name, node_name=obj.name, id=obj.id, msg=f"fieldValue '{str(value)}' must be one of these values [{','.join(self.enum_members.keys())}]")
            return value
        
        else:
            match = next((en for en in self.enum_members if en.upper() == str(value).upper()), None)

            if not match:
                raise exceptions.SocketError(socket_name=self.name, node_name=obj.name, id=obj.id, msg=f"fieldValue '{value}' must be one of these values [{','.join(self.enum_members.keys())}]")
            return value


    def validate_instance_metadata(self, graph: "Graph", node_metadata: "NodeMetadata", socket_metadata: "SocketMetadata"):
        """
        Check that the given socket instance metadata is valid according to this sockets's definitions. Raises errors when a validation fails.

        :param graph: The Graph object that this instance metadata belongs to.
        :param node_metadata: The node metadata that this socket belongs to.
        :param socket_metadata: The socket metadata.
        """

        

        if "fieldValue" in socket_metadata and str(socket_metadata["fieldValue"]) and str(socket_metadata["fieldValue"]).upper() not in [key.upper() for key in self.enum_members]:
            raise exceptions.SocketError(
                    socket_name=self.name,
                    node_name=node_metadata["name"],
                    id=node_metadata["id"],
                    msg=f"fieldValue '{socket_metadata['fieldValue']}' must be one of these values:[{','.join([str(member) for member in self.enum_members])}]",
                )
        else:
            super().validate_instance_metadata(graph,node_metadata,socket_metadata)
    
    def metadata(self):
        metadata = super().metadata()
        metadata['enumOptions'] = [str(member) for member in self.enum_members]
        return metadata

    
class OptionalInputSocket(_BaseSocket, typing.Generic[T]):
    """
    An optional input socket. Unlike a standard input socket, this will take a value of ``None`` if no connection is available.

    :param datatype: The DataType for this input socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    :param input_field: Default value for the input field on this socket (String/Number/Boolean data types only)
    """

    def __init__(self, datatype: DataType[T], name: str, description: str, input_field: typing.Optional[T] = None):
        super().__init__(is_input=True, is_optional=True, is_list=False, datatype=datatype, name=name, description=description, input_field=input_field)

    def __get__(self, obj: "Node", owner) -> typing.Optional[T]:
        return super().__get__(obj, owner)


class ListInputSocket(_BaseSocket, typing.Generic[T]):
    """
    An input socket that accepts a list of values.

    :param datatype: The DataType for this input socket.
    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    :param input_field: Default value for the input field on this socket (String/Number/Boolean data types only)
    """

    def __init__(self, datatype: DataType[T], name: str, description: str, input_field: typing.Optional[typing.List[T]] = None):
        super().__init__(is_input=True, is_optional=False, is_list=True, datatype=datatype, name=name, description=description, input_field=input_field)

    def __get__(self, obj: "Node", owner) -> typing.List[T]:
        return super().__get__(obj, owner)


class LinkInputSocket(_BaseSocket):
    """
    A link (non-data) output socket. This socket will not be associated with any data type and thus will not carry a value. This only serves
    the purpose of connecting nodes without passing data.

    :param name: The name of the socket. If empty, it will be derived from the name of the class attribute.
    :param description: The description for this socket.
    """

    def __init__(self, name: str, description: str):
        super().__init__(is_input=True, is_optional=False, is_list=False, datatype=None, name=name, description=description, input_field=None)
