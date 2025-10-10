import typeguard
import typing

if typing.TYPE_CHECKING:
    from graphex.node import Node

T = typing.TypeVar("T", str, int, float, bool)


class InputField(typing.Generic[T]):
    """
    Class for all input fields.

    Input fields are direct inputs added to a node that enables user input to determine some value.

    The type of input field will be determined by the type of the default value.
    """

    def __init__(self, default_value: T, name: str = "Value", multiline: bool = False, required: bool = True, floating_label: bool = True):
        self.default_value: T = default_value
        """The default value of this input field."""

        self.name = name
        """The name of this input field."""

        self.multiline = multiline
        """Whether this is a multi-line text area (otherwise, newlines are not allowed)."""

        self.required = required
        """Whether this field is required."""

        self.floating_label = floating_label
        """Whether to use the 'floating label' style of input in the UI."""

    def __get__(self, obj: "Node", owner) -> T:
        value: T = obj._instance_metadata.get("fieldValue", self.default_value)  # type: ignore
        try:
            typeguard.check_type(value, type(self.default_value))
        except typeguard.TypeCheckError as e:
            raise TypeError(f"Field '{self.name}' on {str(obj)} failed type checking: {str(e)}")
        return value

    def __set__(self, obj: "Node", value) -> None:
        raise AttributeError(f"Cannot overwrite the value of a field on node {obj._instance_metadata['name']} ({obj._instance_metadata['id']})")

    def metadata(self):
        return {"default": self.default_value, "name": self.name, "multiline": self.multiline, "required": self.required, "floatingLabel": self.floating_label}
