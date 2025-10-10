from graphex import (
    Dynamic,
    Number,
    Boolean,
    Graph,
    NodeMetadata,
    NodeDynamicAttributes,
    InputSocket,
    ListInputSocket,
    OptionalInputSocket,
    OutputSocket,
    ListOutputSocket,
    constants,
    Node,
    String,
    Number,
    Boolean
)
from graphex.nodes.templates import DynamicInputTemplateNode
import typing
import re


class GetListSize(DynamicInputTemplateNode):
    name = f"Get List Size"
    description = f"Get the size/length of a list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#len"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to get the size/length of.")

    list_size = OutputSocket(datatype=Number, name="List Size", description="The size of the list.")

    def run(self):
        self.list_size = len(self.list_value)
        self.get_output("List", self._graph, self._instance_metadata).set_value(self, self.list_value)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to get the size/length of."),
                    ListOutputSocket(datatype=datatype, name="List", description="The list of values (same as input)."),
                ],
                description=f"Get the size/length of a '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class GetListItem(DynamicInputTemplateNode):
    name = f"Get List Item"
    description = f"Get an item in a list by index."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to get the item from.")
    index = InputSocket(
        datatype=Number,
        name="Index",
        description="The index of the item to get. If the index is out of range for this list, an error will be raised. Negative indices are allowed to index from the back of the list (e.g. -1 to get the last item).",
    )

    def run(self):
        self.get_output("List", self._graph, self._instance_metadata).set_value(self, self.list_value)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, self.list_value[int(self.index)])

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to get the item from."),
                    OutputSocket(datatype=datatype, name="Value", description="The value for the item at this index."),
                    ListOutputSocket(datatype=datatype, name="List", description="The list of values (same as input)."),
                ],
                description=f"Get an item from a '{datatype.name}' list by index.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListPop(DynamicInputTemplateNode):
    name = f"List Pop"
    description = f"Remove and return an item at an index in a list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#more-on-lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to get the item from.")
    index = InputSocket(
        datatype=Number,
        name="Index",
        description="The index of the item to get. If the index is out of range for this list, an error will be raised. Negative indices are allowed to index from the back of the list (e.g. -1 to get the last item).",
        input_field=-1,
    )

    def run(self):
        list_copy = [*self.list_value]
        value = list_copy.pop(int(self.index))
        self.get_output("List", self._graph, self._instance_metadata).set_value(self, list_copy)
        self.get_output("Value", self._graph, self._instance_metadata).set_value(self, value)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to get the item from."),
                    OutputSocket(datatype=datatype, name="Value", description="The value for the item at this index."),
                    ListOutputSocket(datatype=datatype, name="List", description="The list of values with the item at 'Index' removed."),
                ],
                description=f"Remove and return an item at an index in a '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListSlice(DynamicInputTemplateNode):
    name = f"List Slice"
    description = f"Extract a segment of a list between two indices into a new list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to slice.")
    start_index = OptionalInputSocket(
        datatype=Number,
        name="Start Index",
        description="The start index of the slice to extract (inclusive). Negative indices are allowed to index from the back of the list (e.g. -1 to reference the last item). If no value is provided, the slice will start from the beginning of the list.",
    )
    end_index = OptionalInputSocket(
        datatype=Number,
        name="End Index",
        description="The end index of the slice to extract (non-inclusive). Negative indices are allowed to index from the back of the list (e.g. -1 to reference the last item). If no value is provided, the slice will end at the end of the list.",
    )

    def run(self):
        start = int(self.start_index) if self.start_index is not None else 0
        end = int(self.end_index) if self.end_index is not None else len(self.list_value)
        slice = self.list_value[start:end]

        self.get_output("Original List", self._graph, self._instance_metadata).set_value(self, self.list_value)
        self.get_output("Slice", self._graph, self._instance_metadata).set_value(self, slice)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to slice."),
                    ListOutputSocket(datatype=datatype, name="Slice", description="The list of values extracted between the two indices (the 'slice')."),
                    ListOutputSocket(datatype=datatype, name="Original List", description="The original list of values (same as input)."),
                ],
                description=f"Extract a segment of a '{datatype.name}' list between two indices into a new '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListContains(DynamicInputTemplateNode):
    name = f"List Contains"
    description = f"Outputs True (and the index location) if the provided item is included in the list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#more-on-lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to search.")

    def run(self):
        try:
            index = self.list_value.index(self.get_input("Value", self._graph, self._instance_metadata).get_value(self))
            self.get_output("Contained in List?", self._graph, self._instance_metadata).set_value(self, True)
            self.get_output("Index", self._graph, self._instance_metadata).set_value(self, index)
        except ValueError:
            self.get_output("Contained in List?", self._graph, self._instance_metadata).set_value(self, False)
            self.get_output("Index", self._graph, self._instance_metadata).set_value(self, -1)

        self.get_output("List", self._graph, self._instance_metadata).set_value(self, self.list_value)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to search."),
                    InputSocket(datatype=datatype, name="Value", description="The value to look for in the list"),
                    OutputSocket(datatype=Boolean, name="Contained in List?", description="True if the provided item is in the list."),
                    OutputSocket(
                        datatype=Number, name="Index", description="If found, the first index in the list that the value was found at (-1 if not found)."
                    ),
                    ListOutputSocket(datatype=datatype, name="List", description="The list of values (same as input)."),
                ],
                description=f"Outputs True (and the index location) if the provided item is included in the '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListIndexOf(DynamicInputTemplateNode):
    name = f"List Index Of"
    description = f"Outputs the first index location of a provided item in the list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#more-on-lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to search.")
    start_index = OptionalInputSocket(
        datatype=Number,
        name="Start Index",
        description="The index to begin searching from (inclusive). Negative indices are allowed to index from the back of the list (e.g. -1 to reference the last item). If no value is provided, the search will start from the beginning of the list.",
    )
    end_index = OptionalInputSocket(
        datatype=Number,
        name="End Index",
        description="The index to end searching at (non-inclusive). Negative indices are allowed to index from the back of the list (e.g. -1 to reference the last item). If no value is provided, the search will end at the end of the list.",
    )

    def run(self):
        start = int(self.start_index) if self.start_index is not None else 0
        end = int(self.end_index) if self.end_index is not None else len(self.list_value)
        value = self.get_input("Value", self._graph, self._instance_metadata).get_value(self)
        try:
            index = self.list_value.index(value, start, end)
            self.get_output("Index", self._graph, self._instance_metadata).set_value(self, index)
        except ValueError:
            self.get_output("Index", self._graph, self._instance_metadata).set_value(self, -1)

        self.get_output("List", self._graph, self._instance_metadata).set_value(self, self.list_value)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to search."),
                    InputSocket(datatype=datatype, name="Value", description="The value to look for in the list"),
                    OutputSocket(
                        datatype=Number, name="Index", description="If found, the first index in the list that the value was found at (-1 if not found)."
                    ),
                    ListOutputSocket(datatype=datatype, name="List", description="The list of values (same as input)."),
                ],
                description=f"Outputs the first index location of a provided item in the '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class AppendToList(DynamicInputTemplateNode):
    name = f"Append To List"
    description = f"Append an item to the end of a list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#more-on-lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to append to.")

    def run(self):
        list_copy = [*self.list_value]
        list_copy.append(self.get_input("Value", self._graph, self._instance_metadata).get_value(self))
        self.get_output("New List", self._graph, self._instance_metadata).set_value(self, list_copy)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to append to."),
                    InputSocket(datatype=datatype, name="Value", description="The value to append to the list."),
                    ListOutputSocket(datatype=datatype, name="New List", description="The new list of values."),
                ],
                description=f"Append an item to the end of a '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ExtendList(DynamicInputTemplateNode):
    name = f"Extend List"
    description = f"Extend a list by appending contents of another list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#more-on-lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to extend.")

    def run(self):
        list_copy = [*self.list_value]
        list_copy.extend(self.get_input("Values To Append", self._graph, self._instance_metadata).get_value(self))
        self.get_output("New List", self._graph, self._instance_metadata).set_value(self, list_copy)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to extend."),
                    ListInputSocket(datatype=datatype, name="Values To Append", description="The list to append to the end of 'List'."),
                    ListOutputSocket(datatype=datatype, name="New List", description="The new list of values."),
                ],
                description=f"Extend a '{datatype.name}' list by appending contents of another '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class InsertInList(DynamicInputTemplateNode):
    name = f"Insert In List"
    description = f"Insert an item at a specified position in the list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#more-on-lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to insert into.")
    index = InputSocket(datatype=Number, name="Index", description="The index at which to insert the item.")

    def run(self):
        index = int(self.index)
        new_list = [*self.list_value[0:index], self.get_input("Value", self._graph, self._instance_metadata).get_value(self), *self.list_value[index:]]
        self.get_output("New List", self._graph, self._instance_metadata).set_value(self, new_list)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to insert into."),
                    InputSocket(datatype=datatype, name="Value", description="The value to insert into the list."),
                    ListOutputSocket(datatype=datatype, name="New List", description="The new list of values."),
                ],
                description=f"Insert an item at a specified position in the '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ReverseList(DynamicInputTemplateNode):
    name = f"Reverse List"
    description = f"Reverse a list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#more-on-lists"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to reverse.")

    def run(self):
        reversed_list = self.get_input("List", self._graph, self._instance_metadata).get_value(self)[::-1]
        self.get_output("New List", self._graph, self._instance_metadata).set_value(self, reversed_list)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to reverse."),
                    ListOutputSocket(datatype=datatype, name="New List", description="The reversed list."),
                ],
                description=f"Reverse a '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListContainsAny(DynamicInputTemplateNode):
    name = f"List Contains Any"
    description = f"Check whether a list has any (one or more) requested values."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists", "https://docs.python.org/3/reference/expressions.html#membership-test-operations", "https://stackoverflow.com/questions/7571635/fastest-way-to-check-if-a-value-exists-in-a-list"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to search.")
    found = OutputSocket(datatype=Boolean, name="Any in List?", description="True if the searched list has any value in the 'Values' list.")

    def run(self):
        self.get_output("List", self._graph, self._instance_metadata).set_value(self, self.list_value)
        for value in self.get_input("Values", self._graph, self._instance_metadata).get_value(self):
            if value in self.list_value:
                self.found = True
                return
        self.found = False

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to search."),
                    ListInputSocket(datatype=datatype, name="Values", description="The values to look for in the list."),
                    ListOutputSocket(datatype=datatype, name="List", description="The list of values (same as input)."),
                ],
                description=f"Check whether a '{datatype.name}' list has any (one or more) requested values.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListContainsAll(DynamicInputTemplateNode):
    name = f"List Contains All"
    description = f"Check whether a list has all requested values."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists", "https://docs.python.org/3/reference/expressions.html#membership-test-operations", "https://stackoverflow.com/questions/7571635/fastest-way-to-check-if-a-value-exists-in-a-list"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to search.")
    found = OutputSocket(datatype=Boolean, name="All in List?", description="True if the searched list has all values in the 'Values' list.")

    def run(self):
        self.get_output("List", self._graph, self._instance_metadata).set_value(self, self.list_value)
        for value in self.get_input("Values", self._graph, self._instance_metadata).get_value(self):
            if value not in self.list_value:
                self.found = False
                return
        self.found = True

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to search."),
                    ListInputSocket(datatype=datatype, name="Values", description="The values to look for in the list."),
                    ListOutputSocket(datatype=datatype, name="List", description="The list of values (same as input)."),
                ],
                description=f"Check whether a '{datatype.name}' list has all requested values.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListEquality(DynamicInputTemplateNode):
    name = f"Lists Are Equal"
    description = f"Check whether a list is equal to another list (contain exactly the same elements, no more and no fewer)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists", "https://docs.python.org/3/reference/expressions.html#comparisons"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value1 = ListInputSocket(datatype=Dynamic, name="First List", description="The first list of values.")

    equals = OutputSocket(datatype=Boolean, name="Equal", description="True if the lists are considered to be equal.")

    def run(self):
        list_value1 = self.list_value1
        list_value2 = self.get_input("Second List", self._graph, self._instance_metadata).get_value(self)
        if not self.get_input("Order Independent", self._graph, self._instance_metadata).get_value(self):
            self.equals = list_value1 == list_value2
            return

        # Order independent
        # Quick and easy methods for testing equality while ignoring order,
        # such as sorting or using collections.Counter, do not work
        # for all types (i.e. non-hashable types).
        # We'll need to check explicitly
        if len(list_value1) != len(list_value2):
            self.equals = False
            return
        list2_copy = [*list_value2]
        for item in list_value1:
            try:
                index = list2_copy.index(item)
                list2_copy.pop(index)
            except ValueError:
                self.equals = False
                return
        self.equals = True

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("First List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="First List", description="The first list of values."),
                    ListInputSocket(datatype=datatype, name="Second List", description="The second list of values."),
                    InputSocket(
                        datatype=Boolean,
                        name="Order Independent",
                        description="Whether the order of the elements is important to determining equality. If True, the order of the elements is not considered. If False, the elements must appear in the same order.",
                        input_field=False,
                    ),
                ],
                description=f"Check whether a '{datatype.name}' list has all requested values.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))

class BuildStringList(Node):
    name = f"Build List (String)"
    description = f"Build a list of strings by connecting individual string data values or by typing list values into the input field of this node."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists"]
    categories = ["Lists", "Create", "String"]
    color = constants.COLOR_STRING

    start_list = ListInputSocket(datatype=String, name="List to Build", description="Connect values to this list input socket or create them inline using the 'Input Field' option and then click 'add'")
    same_list = ListOutputSocket(datatype=String, name="List", description="The list of values you put together.")


    def run(self):
        self.same_list = self.start_list

class BuildNumberList(Node):
    name = f"Build List (Number)"
    description = f"Build a list of numbers by connecting individual number data values or by typing list values into the input field of this node."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists"]
    categories = ["Lists", "Create", "Number"]
    color = constants.COLOR_NUMBER

    start_list = ListInputSocket(datatype=Number, name="List to Build", description="Connect values to this list input socket or create them inline using the 'Input Field' option and then click 'add'")
    same_list = ListOutputSocket(datatype=Number, name="List", description="The list of values you put together.")


    def run(self):
        self.same_list = self.start_list

class BuildBooleanList(Node):
    name = f"Build List (Boolean)"
    description = f"Build a list of booleans by connecting individual boolean data values or by typing list values into the input field of this node."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#lists"]
    categories = ["Lists", "Create", "Boolean"]
    color = constants.COLOR_BOOLEAN

    start_list = ListInputSocket(datatype=Boolean, name="List to Build", description="Connect values to this list input socket or create them inline using the 'Input Field' option and then click 'add'")
    same_list = ListOutputSocket(datatype=Boolean, name="List", description="The list of values you put together.")


    def run(self):
        self.same_list = self.start_list


class SortList(DynamicInputTemplateNode):
    name = f"Sort List"
    description = f"Sort a list in ascending order (e.g. a, b, c or 1, 2, 3). Can also natural sort lists of Strings or Numbers."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/howto/sorting.html"]
    categories = ["Lists"]
    color = constants.COLOR_SPECIAL

    list_value = ListInputSocket(datatype=Dynamic, name="List", description="The list to sort.")
    natural_sort = InputSocket(datatype=Boolean, name="Natural Sort?", description="When True, will use an algorithm to sort naturally instead of the python built-in 'machine' way of sorting. Note that this is much slower than a normal sort.")

    def run(self):
        def natural_sort(l):
            def convert(text):
                return int(text) if text.isdigit() else text.lower()

            def alphanum_key(key):
                # Convert everything to string first to handle mixed types
                key = str(key)
                return [convert(c) for c in re.split('([0-9]+)', key)]

            return sorted(l, key=alphanum_key)

        i = self.get_input("List", self._graph, self._instance_metadata).get_value(self)
        if self.natural_sort:
            self.get_output("New List", self._graph, self._instance_metadata).set_value(self, natural_sort(i))
        else:
            self.get_output("New List", self._graph, self._instance_metadata).set_value(self, sorted(i))

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(datatype=datatype, name="List", description="The list to sort."),
                    ListOutputSocket(datatype=datatype, name="New List", description="The sorted list."),
                ],
                description=f"Sort a '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))
