from graphex.util import parse_yml, dump_yml
from graphex import (
    Node,
    InputSocket,
    OptionalInputSocket,
    ListInputSocket,
    OutputSocket,
    ListOutputSocket,
    String,
    Number,
    Boolean,
    DataContainer,
    Dynamic,
    constants,
    exceptions,
    Graph,
    NodeDynamicAttributes,
    NodeMetadata
)
from graphex.nodes.templates import DynamicInputTemplateNode
import typing
import copy
import json
import re

def get_data_container_value(
    datacontainer: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]], query: str, skip_last: bool = False, ignore_query: bool = False
) -> typing.Any:
    if len(query.strip()) == 0:
        return datacontainer
    obj = datacontainer
    if ignore_query:
        key = query
        try:
            if isinstance(obj, list):
                obj = obj[int(key)]
            else:
                obj = obj[key]
        except TypeError as e:
            raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{key}': {str(e)})", datacontainer)
    else:
        query_components = query.strip().split(".")
        if skip_last:
            query_components = query_components[:-1]
        for key in query_components:
            try:
                if isinstance(obj, list):
                    obj = obj[int(key)]
                else:
                    obj = obj[key]
            except KeyError:
                raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{key}' not found in Data Container)", datacontainer)
            except TypeError as e:
                raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{key}': {str(e)})", datacontainer)
    return obj


def set_data_container_value(
    datacontainer: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]], query: str, value: typing.Any, deep_copy: bool = True, ignore_query: bool = False
) -> typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]]:
    if len(query.strip()) == 0:
        raise exceptions.DataContainerException(f"Empty query.", datacontainer)
    new_datacontainer = datacontainer
    if deep_copy:
        new_datacontainer = copy.deepcopy(datacontainer)
    last_key = query
    try:
        obj = get_data_container_value(new_datacontainer, query, True, ignore_query=ignore_query)
    except KeyError:
        if ignore_query and isinstance(new_datacontainer, dict):
            new_datacontainer[last_key] = value
            return new_datacontainer
        else:
            raise exceptions.DataContainerException(f"Invalid query '{query}' (Key not found in Data Container)", datacontainer)
            
    if not ignore_query:
        last_key = query.strip().split(".")[-1]
    try:
        if isinstance(obj, list):
            obj[int(last_key)] = value
        else:
            obj[last_key] = value
    except KeyError:
        raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{last_key}' not found in Data Container)", datacontainer)
    except TypeError as e:
        raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{last_key}': {str(e)})", datacontainer)
    return new_datacontainer


def set_data_container_value_nested(
    datacontainer: typing.Dict[typing.Any, typing.Any], query: str, value: typing.Dict[typing.Any, typing.Any], deep_copy: bool = True, ignore_query: bool = False
) -> typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]]:
    if len(query.strip()) == 0:
        raise exceptions.DataContainerException(f"Empty query.", datacontainer)
    new_datacontainer = datacontainer
    if deep_copy:
        new_datacontainer = copy.deepcopy(datacontainer)
    last_key = query
    if not ignore_query:
        last_key = query.strip().split(".")[-1]
    try:
        new_datacontainer[last_key] = value
    except TypeError as e:
        raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{last_key}': {str(e)})", datacontainer)
    return new_datacontainer


def delete_data_container_value(
    datacontainer: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]], query: str, deep_copy: bool = True
) -> typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]]:
    if len(query.strip()) == 0:
        raise exceptions.DataContainerException(f"Empty query.", datacontainer)
    new_datacontainer = datacontainer
    if deep_copy:
        new_datacontainer = copy.deepcopy(datacontainer)
    obj = get_data_container_value(new_datacontainer, query, skip_last=True)
    last_key = query.strip().split(".")[-1]
    try:
        if isinstance(obj, list):
            obj.pop(int(last_key))
        else:
            del obj[last_key]
    except KeyError:
        raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{last_key}' not found in Data Container)", datacontainer)
    except TypeError as e:
        raise exceptions.DataContainerException(f"Invalid query '{query}' (Key '{last_key}': {str(e)})", datacontainer)
    return new_datacontainer


class EmptyDataContainer(Node):
    name = "Create Empty Data Container"
    description = "Create an empty data container object (python dictionary)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = OutputSocket(
        datatype=DataContainer, name="Data Container", description="The Data Container object containing the data parsed from the given JSON string."
    )

    def run(self):
        self.datacontainer = DataContainer.construct({})


class DataContainerFromJSON(Node):
    name = "Data Container From JSON"
    description = "Convert a JSON string to a queryable data container object."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries", "https://www.json.org/json-en.html"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    jsonstring = InputSocket(datatype=String, name="JSON String", description="The JSON string to convert to a Data Container.")

    datacontainer = OutputSocket(
        datatype=DataContainer, name="Data Container", description="The Data Container object containing the data parsed from the given JSON string."
    )

    def run(self):
        self.datacontainer = json.loads(self.jsonstring)


class DataContainerFromYAML(Node):
    name = "Data Container From YAML"
    description = "Convert a YAML string to a queryable data container object."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries", "https://yaml.org/spec/1.2.2/"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    ymlstring = InputSocket(datatype=String, name="YAML String", description="The YAML string to convert to a Data Container.")

    datacontainer = OutputSocket(
        datatype=DataContainer, name="Data Container", description="The Data Container object containing the data parsed from the given YAML string."
    )

    def run(self):
        self.datacontainer = parse_yml(self.ymlstring)


class DataContainerFromKeyValuePairs(Node):
    name = "Data Container From Key/Value Pairs"
    description = "Convert key/value pairs to a queryable data container object. The input string must follow the format '<key>: <value>' (one per line)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    input_string = InputSocket(datatype=String, name="String", description="The string with key/value pairs to convert to a Data Container.")

    datacontainer = OutputSocket(
        datatype=DataContainer, name="Data Container", description="The Data Container object containing the data parsed from the given string."
    )

    def run(self):
        obj = {}
        for line in self.input_string.strip().split("\n"):
            if not line.strip():
                continue
            if ":" not in line:
                raise ValueError(f"Text '{line.strip()}' does not contain a 'key: value' pair to parse.")
            split = line.strip().split(":", maxsplit=1)
            key = split[0].strip()
            value = split[1].strip()
            obj[key] = value
        self.datacontainer = obj


class DataContainerToJSON(Node):
    name = "Data Container To JSON"
    description = "Convert a Data Container object to JSON."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries", "https://www.json.org/json-en.html"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to convert to a JSON string.")
    indent = OptionalInputSocket(
        datatype=Number,
        name="Indent",
        description="If provided as a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0 will only insert newlines. If not provided, no pretty-printing will occur.",
    )

    jsonstring = OutputSocket(datatype=String, name="JSON String", description="The JSON string representation of the Data Container.")

    def run(self):
        self.jsonstring = json.dumps(self.datacontainer, indent=int(self.indent) if self.indent is not None else None, default=lambda x: str(x))


class DataContainerToYAML(Node):
    name = "Data Container To YAML"
    description = "Convert a Data Container object to YAML."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries", "https://yaml.org/spec/1.2.2/"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to convert to a YAML string.")

    ymlstring = OutputSocket(datatype=String, name="YAML String", description="The YAML string representation of the Data Container.")

    def run(self):
        self.ymlstring = dump_yml(self.datacontainer)


class DataContainerListToJSON(Node):
    name = "Data Container List To JSON"
    description = "Convert a list of Data Container objects to JSON."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries", "https://www.json.org/json-en.html"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainers = ListInputSocket(
        datatype=DataContainer, name="Data Containers", description="The list of Data Container objects to convert to a JSON string."
    )
    indent = OptionalInputSocket(
        datatype=Number,
        name="Indent",
        description="If provided as a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0 will only insert newlines. If not provided, no pretty-printing will occur.",
    )

    jsonstring = OutputSocket(datatype=String, name="JSON String", description="The JSON string representation of the Data Container list.")

    def run(self):
        self.jsonstring = json.dumps(self.datacontainers, indent=int(self.indent) if self.indent is not None else None, default=lambda x: str(x))


class GetDataContainerValue(Node):
    name = "Get Data Container Value"
    description = "Get a value from a Data Container Object. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the query is invalid, an exception will be raised. Queried values will always be returned as strings (cast to the appropriate data type as needed)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to query.")
    query = InputSocket(
        datatype=String,
        name="Query",
        description="The query to use to extract a value from the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'",
    )

    value = OutputSocket(
        datatype=String,
        name="Value",
        description="The value for the query.",
    )

    def run(self):
        self.value = str(get_data_container_value(self.datacontainer, self.query, False))


class GetDataContainerKeys(Node):
    name = "Get Data Container Keys"
    description = "Get the keys from a Data Container Object. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the query is invalid, an exception will be raised. Queried values will always be returned as strings (cast to the appropriate data type as needed)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to query.")
    query = InputSocket(
        datatype=String,
        name="Query",
        description="The query to specify the location in the Data Container from which to get the keys. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'",
    )

    keys = ListOutputSocket(
        datatype=String,
        name="Keys",
        description="The keys of the Data Container object. For dictionary-like objects, this will be the literal keys of the object. For lists, this will be the indices of the list.",
    )

    def run(self):
        data = get_data_container_value(self.datacontainer, self.query, False)
        if isinstance(data, dict):
            self.keys = list(data.keys())
            return
        if isinstance(data, list):
            self.keys = list(range(0, len(data)))
            return
        raise exceptions.DataContainerException(f"Query '{self.query}' does not locate a keyable object within the given Data Container.", self.datacontainer)


class GetNestedDataContainer(Node):
    name = "Get Nested Data Container"
    description = "Get a Data Container Object that is nested within another Data Container object. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectName'. If the query is invalid or the query does not point to a nested Data Container, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to query.")
    query = InputSocket(
        datatype=String,
        name="Query",
        description="The query to use to extract a value from the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectName'",
    )
    ignore_query = OptionalInputSocket(
        datatype=Boolean,
        name="Ignore Dot Notation?",
        description="When True, ignore the dot notation query and retrieve the location strickly as a string (e.g. if you want the location to be '1.2.3.4' you would set this checkbox to True)"
    )

    value = OutputSocket(
        datatype=DataContainer,
        name="Value",
        description="The value for the query.",
    )

    def run(self):
        obj = get_data_container_value(self.datacontainer, self.query, False, ignore_query=self.ignore_query if self.ignore_query else False)
        if not isinstance(obj, list) and not isinstance(obj, dict):
            raise exceptions.DataContainerException(f"Query '{self.query}' does not result in a Data Container.", self.datacontainer)
        self.value = obj


class GetNestedDataContainerList(Node):
    name = "Get Nested Data Container List"
    description = "Get a list of Data Container Objects that are nested within another Data Container object. This method is DEPRECATED in favor of 'Get Data Container List from Data Container'. You should only use this node if the new one doesn't accomplish what you need it to do. The list must contain only Data Container objects and an error will be raised if another type (e.g. strings) are present in the list. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectName'. If the query is invalid or the query does not point to a nested Data Container, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to query.")
    query = InputSocket(
        datatype=String,
        name="Query",
        description="The query to use to extract a value from the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectName'",
    )

    values = ListOutputSocket(
        datatype=DataContainer,
        name="Values",
        description="The value for the query.",
    )

    def run(self):
        obj = get_data_container_value(self.datacontainer, self.query, False, ignore_query=False)
        if not isinstance(obj, list):
            raise exceptions.DataContainerException(f"Query '{self.query}' does not result in a list.", self.datacontainer)
        if not all([isinstance(item, (dict, list)) for item in obj]):
            raise exceptions.DataContainerException(
                f"Query '{self.query}' does not point to list containing only Data Container compatible items.", self.datacontainer
            )
        self.values = obj


class SetDataContainerStringValue(Node):
    name = "Set Data Container String Value"
    description = "Set a string value in a Data Container Object. The location to set the value can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to set a value in.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )
    value = InputSocket(
        datatype=String,
        name="Value",
        description="The value to set.",
    )

    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the new value set. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        self.new_datacontainer = set_data_container_value(self.datacontainer, self.query, self.value)


class SetDataContainerNumberValue(Node):
    name = "Set Data Container Number Value"
    description = "Set a number value in a Data Container Object. The location to set the value can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to set a value in.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )
    value = InputSocket(
        datatype=Number,
        name="Value",
        description="The value to set.",
    )

    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the new value set. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        self.new_datacontainer = set_data_container_value(self.datacontainer, self.query, self.value)


class SetDataContainerBooleanValue(Node):
    name = "Set Data Container Boolean Value"
    description = "Set a boolean value in a Data Container Object. The location to set the value can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to set a value in.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )
    value = InputSocket(
        datatype=Boolean,
        name="Value",
        description="The value to set.",
    )

    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the new value set. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        self.new_datacontainer = set_data_container_value(self.datacontainer, self.query, self.value)


class SetNestedDataContainer(Node):
    name = "Set Nested Data Container"
    description = "Set a nested Data Container Object within another. The location to set the value can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to set a value in.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )
    value = InputSocket(
        datatype=DataContainer,
        name="Value",
        description="The value to set.",
    )
    ignore_query = OptionalInputSocket(
        datatype=Boolean,
        name="Ignore Dot Notation?",
        description="When True, ignore the dot notation query and store the location strickly as a string (e.g. if you want the location to be '1.2.3.4' you would set this checkbox to True)"
    )

    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the new value set. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        self.new_datacontainer = set_data_container_value_nested(self.datacontainer, self.query, self.value, ignore_query=self.ignore_query if self.ignore_query else False)


class DataContainerIsEqual(Node):
    name = "Data Container Is Equal"
    description = "Check if a Data Container is exactly equal to another Data Container (recursively)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer1 = InputSocket(
        datatype=DataContainer,
        name="First Data Container",
        description="A Data Container object to check for equality with the Second Data Container object.",
    )
    datacontainer2 = InputSocket(
        datatype=DataContainer,
        name="Second Data Container",
        description="A Data Container object to check for equality with the First Data Container object.",
    )
    order_independent = InputSocket(
        datatype=Boolean,
        name="Order Independent",
        description="Whether the order of list elements is important to determining equality. If True, the order of list elements is not considered. If False, the elements must appear in the same order.",
        input_field=False,
    )

    is_equal = OutputSocket(datatype=Boolean, name="Is Equal", description="Whether the provided Data Container objects are equal.")

    def check_is_equal(
        self,
        data1: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]],
        data2: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]],
    ) -> bool:
        if type(data1) != type(data2):
            return False

        if isinstance(data1, list) and isinstance(data2, list):
            if len(data1) != len(data2):
                return False

            if not self.order_independent:
                # Order dependent
                for item1, item2 in zip(data1, data2):
                    if isinstance(item1, (int, float, bool, str)) or isinstance(item2, (int, float, bool, str)):
                        if item1 != item2:
                            return False
                    elif not self.check_is_equal(item1, item2):
                        return False
            else:
                # Order independent search
                data2_copy = [*data2]
                for item in data1:
                    if isinstance(item, (int, float, bool, str)):
                        if item not in data2_copy:
                            return False
                        data2_copy.pop(data2_copy.index(item))
                        continue

                    found = False
                    for i in range(len(data2_copy)):
                        if self.check_is_equal(item, data2_copy[i]):
                            data2_copy.pop(i)
                            found = True
                            break

                    if not found:
                        return False

                if len(data2_copy):  # Any extra items?
                    return False

        if isinstance(data1, dict) and isinstance(data2, dict):
            if len(data1) != len(data2):
                return False

            data2_copy = {**data2}
            for key in data1.keys():
                if key not in data2_copy:
                    return False

                if isinstance(data1[key], (int, float, bool, str)) or isinstance(data2_copy[key], (int, float, bool, str)):
                    if data1[key] != data2_copy[key]:
                        return False
                elif not self.check_is_equal(data1[key], data2_copy[key]):
                    return False

                del data2_copy[key]

            if len(data2_copy):  # Any extra keys?
                return False

        return True

    def run(self):
        self.is_equal = self.check_is_equal(self.datacontainer1, self.datacontainer2)


class DataContainerIsSubset(Node):
    name = "Data Container Is Subset"
    description = "Check if a Data Container is a subset of another Data Container. A Data Container is considered a subset of another if all its keys and values are present in the other Data Container, recursively. In the case of lists, each list item of the subset Data Container must be equal to or a subset of a list item in the other Data Container."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(
        datatype=DataContainer,
        name="Main Data Container",
        description="The main Data Container object. This node will check if 'Subset Data Container' is a subset of this.",
    )
    datacontainer_subset = InputSocket(
        datatype=DataContainer,
        name="Subset Data Container",
        description="The subset Data Container object. This node will check if this is a subset of 'Main Data Container'.",
    )

    is_subset = OutputSocket(datatype=Boolean, name="Is Subset", description="Whether 'Subset Data Container' is a subset of 'Main Data Container'")

    def check_is_subset(
        self,
        main: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]],
        subset: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]],
    ) -> bool:
        if type(main) != type(subset):
            return False

        if isinstance(subset, list) and isinstance(main, list):
            if len(subset) > len(main):
                return False

            main_copy = [*main]
            for subset_item in subset:
                if isinstance(subset_item, (int, float, bool, str)):
                    if subset_item not in main_copy:
                        return False
                    main_copy.pop(main_copy.index(subset_item))
                    continue

                found = False
                for i, main_item in enumerate(main_copy):
                    if self.check_is_subset(main_item, subset_item):
                        main_copy.pop(i)
                        found = True
                        break

                if not found:
                    return False

        if isinstance(subset, dict) and isinstance(main, dict):
            if len(subset) > len(main):
                return False

            for subset_key, subset_value in subset.items():
                if subset_key not in main:
                    return False

                main_value = main[subset_key]
                if isinstance(subset_value, (int, float, bool, str)) or isinstance(main_value, (int, float, bool, str)):
                    if subset_value != main_value:
                        return False
                elif not self.check_is_subset(main_value, subset_value):
                    return False

        return True

    def run(self):
        self.is_subset = self.check_is_subset(self.datacontainer, self.datacontainer_subset)


class DeleteDataContainerItems(Node):
    name = "Delete Data Container Items"
    description = "Remove keys/values from a Data Container Object. The locations to delete can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to remove values from.")
    queries = ListInputSocket(
        datatype=String,
        name="Locations",
        description="The queries to use to specify the locations to delete in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The queries will be applied in the order specified (e.g. list deletions will change the list size, which will need to be factored in for subsequent deletions).",
    )

    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the specified values removed. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        new_datacontainer = copy.deepcopy(self.datacontainer)
        for query in self.queries:
            new_datacontainer = delete_data_container_value(new_datacontainer, query, deep_copy=False)
        self.new_datacontainer = new_datacontainer


class DataContainerExtractItems(Node):
    name = "Extract Data Container Items"
    description = "Get keys/values from a Data Container Object as a new Data Container object. The locations to get can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to get values from.")
    queries = ListInputSocket(
        datatype=String,
        name="Locations",
        description="The queries to use to specify the locations to get in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. Invalid locations will be silently ignored.",
    )

    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the specified values removed. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        # Rather than copying the values from the old data container
        # to the new, we'll just create a deep copy of the old and delete
        # unneeded values from it. This is a lot simpler to do since it
        # avoids needed to create a new object from the bottom-up
        # and avoids lots of edge cases.
        if any([len(query.strip()) == 0 for query in self.queries]):
            raise exceptions.DataContainerException(f"Empty query.", self.datacontainer)

        query_components_list = [query.strip().split(".") for query in self.queries]

        def walk_and_delete(obj: typing.Union[typing.Dict[typing.Any, typing.Any], typing.List[typing.Any]], query_components: typing.List[str]):
            nonlocal query_components_list
            if isinstance(obj, dict):
                new_obj = dict()
                for key in list(obj.keys()):
                    subquery_components = [*query_components, key]
                    if any([subquery_components == x for x in query_components_list]):
                        # Keep
                        new_obj[key] = obj[key]
                        continue

                    if isinstance(obj[key], (int, float, bool, str)):
                        # Delete primitives
                        continue

                    # Whether or not we delete this object depends on whether
                    # any keys will remain in it after recursive deletions
                    value = walk_and_delete(obj[key], subquery_components)
                    if len(value) != 0:
                        new_obj[key] = value
                return new_obj

            if isinstance(obj, list):
                new_list = list()
                for i in range(len(obj)):
                    subquery_components = [*query_components, str(i)]
                    if any([subquery_components == x for x in query_components_list]):
                        # Keep
                        new_list.append(obj[i])
                        continue

                    if isinstance(obj[i], (int, float, bool, str)):
                        # Delete primitives
                        continue

                    # Whether or not we delete this list depends on whether
                    # any items will remain in it after recursive deletions
                    value = walk_and_delete(obj[i], subquery_components)
                    if len(value) != 0:
                        new_list.append(obj[i])
                        continue
                return new_list
            return obj

        self.new_datacontainer = walk_and_delete(copy.deepcopy(self.datacontainer), [])


class DataContainerFind(Node):
    name = "Find Data Container"
    description = "Search the given Data Container list for ones that match the given key/value and return the first found. The key can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainers = ListInputSocket(datatype=DataContainer, name="Data Containers", description="The Data Container objects to search.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the locations (i.e. the key) in the Data Container used to compare against 'Value'. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. Invalid locations will be silently ignored.",
    )
    value = InputSocket(
        datatype=String,
        name="Value",
        description="The value to check in the Data Containers. If a Data Container in the list matches this value at the provided 'Location', it will be returned. Non-string values (e.g. Numbers) within the Data Containers will be converted to a string for the purposes of this comparison.",
    )
    error_if_not_found = InputSocket(
        datatype=Boolean,
        name="Error If Not Found",
        description="Raise an error if a match is not found. If False, no error will be raised and the 'Found' output socket will indicate if a match was found.",
        input_field=True,
    )

    output = OutputSocket(
        datatype=DataContainer,
        name="Match",
        description="The found Data Container. If 'Error If Not Found' is False and no match was found, this will be disabled.",
    )
    found = OutputSocket(
        datatype=Boolean,
        name="Found",
        description="Whether a matching Data Container was found. If no match was not found, this will be False (otherwise True).",
    )

    def run(self):
        self.disable_output_socket("Match")
        self.found = False

        for obj in self.datacontainers:
            try:
                value = get_data_container_value(obj, self.query)
                if str(value) == self.value:
                    self.output = obj
                    self.found = True
                    return
            except Exception:
                pass

        if self.error_if_not_found:
            raise RuntimeError(f'No Data Container matching query "{self.query}" and value "{self.value}"')


class DataContainerMoveValue(Node):
    name = "Data Container Move Value"
    description = "Move/rename a Data Container value. The locations can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object.")
    from_query = InputSocket(
        datatype=String,
        name="From Location",
        description="The query specifying the location in the Data Container to move. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'.",
    )
    to_query = InputSocket(
        datatype=String,
        name="To Location",
        description="The query specifying the location in the Data Container to move the value to. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'.",
    )

    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the specified value moved. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        new_datacontainer = copy.deepcopy(self.datacontainer)
        value = get_data_container_value(new_datacontainer, self.from_query)
        new_datacontainer = delete_data_container_value(new_datacontainer, self.from_query, deep_copy=False)
        new_datacontainer = set_data_container_value(new_datacontainer, self.to_query, value, deep_copy=False)
        self.new_datacontainer = new_datacontainer


class DataContainerFormatString(Node):
    name = "Data Container Format String"
    description = r"Format the values of a Data Container to a string. Within the provided string, use {data:query} to substitute a value, where 'query' is the location of the data within the Data Container. The locations can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. For example, a format string containing {data:ListValue.0.ObjectValue} will substitute in the value of the Data Container found at 'ListValue.0.ObjectValue'."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    base = InputSocket(
        datatype=String,
        name="String",
        description=r"The string to apply substitutions to. Use {data:query} to substitute a value, where 'query' is the location of the data within the Data Container. The locations can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. For example, a format string containing {data:ListValue.0.ObjectValue} will substitute in the value of the Data Container found at 'ListValue.0.ObjectValue'.",
    )
    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object containing the values to substitute.")

    result = OutputSocket(datatype=String, name="Result", description="The formatted string.")

    def run(self):
        current = self.base
        sub_regex = re.compile(r"\{\s*data:([^\}]+)\s*\}", flags=re.IGNORECASE)  # For matching the template as a whole
        match = None
        while match := sub_regex.search(current):
            if not match:
                break

            full_match = match.group(0)
            try:
                query = match.group(1).strip()
                value = str(get_data_container_value(self.datacontainer, query))
                current = current[0 : match.start(0)] + value + current[match.end(0) :]
            except Exception as e:
                raise exceptions.DataContainerException(f"Invalid template {full_match} ({str(e)})", self.datacontainer)

        self.result = current


class SetDataContainerListValue(DynamicInputTemplateNode):
    name = "Add List to Data Container"
    description = "Adds a completed list of primitives to a Data Container Object. The location to set the value can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container", "Lists"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to set a value in.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )
    list_items = ListInputSocket(
        datatype=Dynamic,
        name="List",
        description="The list to add to the container. This can be a list of any primitive type.",
    )
    ignore_query = OptionalInputSocket(
        datatype=Boolean,
        name="Ignore Dot Notation?",
        description="When True, ignore the dot notation query and retrieve the location strickly as a string (e.g. if you want the location to be '1.2.3.4' you would set this checkbox to True)"
    )
    new_datacontainer = OutputSocket(
        datatype=DataContainer,
        name="New Data Container",
        description="The Data Container object with the new value set. This is a distinct object from the original Data Container input.",
    )

    def run(self):
        self.new_datacontainer = set_data_container_value(self.datacontainer, self.query, self.list_items, ignore_query=self.ignore_query if self.ignore_query else False)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(
                        datatype=datatype,
                        name="List",
                        description="The list to add to the container. This can be a list of any primitive type.",
                    )
                ],
                description=f"Adds a completed list to a Data Container Object. The location to set the value can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, error=str(e))


class GetDataContainerListValue(Node):
    name = "Get String List from Data Container"
    description = "Retrieves a list of String primitives from a Data Container Object. The location to retrieve the value from can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container", "Lists"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to retrieve a value from.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )

    list_items = ListOutputSocket(
        datatype=String,
        name="List",
        description="The list to retrieve from the container.",
    )

    def run(self):
        self.list_items = get_data_container_value(self.datacontainer, self.query, False)


class GetDataContainerListValueNumber(Node):
    name = "Get Number List from Data Container"
    description = "Retrieves a list of Number primitives from a Data Container Object. The location to retrieve the value from can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container", "Lists"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to retrieve a value from.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )

    list_items = ListOutputSocket(
        datatype=Number,
        name="List",
        description="The list to retrieve from the container.",
    )

    def run(self):
        self.list_items = get_data_container_value(self.datacontainer, self.query, False)


class GetDataContainerListValueBoolean(Node):
    name = "Get Boolean List from Data Container"
    description = "Retrieves a list of Boolean primitives from a Data Container Object. The location to retrieve the value from can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container", "Lists"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to retrieve a value from.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )

    list_items = ListOutputSocket(
        datatype=Boolean,
        name="List",
        description="The list to retrieve from the container.",
    )

    def run(self):
        self.list_items = get_data_container_value(self.datacontainer, self.query, False)


class GetDataContainerListValueContainer(Node):
    name = "Get Data Container List from Data Container"
    description = "Retrieves a list of Data Containers from a Data Container Object. The location to retrieve the value from can be specified using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the location is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container", "Lists"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to retrieve a value from.")
    query = InputSocket(
        datatype=String,
        name="Location",
        description="The query to use to specify the location to set the value in the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. The last portion of the query need not exist and will create a new entry in the Data Container as needed.",
    )

    list_items = ListOutputSocket(
        datatype=DataContainer,
        name="List",
        description="The list to retrieve from the container.",
    )

    def run(self):
        self.list_items = get_data_container_value(self.datacontainer, self.query, False)


class GetDataContainerValueNumber(Node):
    name = "Get Data Container Number Value"
    description = "Get a value from a Data Container Object and type cast it to a Number. It is up to you to ensure that the query's value is actually a Number datatype (see Test Data Container Has...). The default number retrieval is for a float but can be forced to be a floored integer instead. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the query is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to query.")
    query = InputSocket(
        datatype=String,
        name="Query",
        description="The query to use to extract a value from the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'",
    )
    force_int = InputSocket(
        datatype=Boolean,
        name="Force Integer?",
        description="When True: force the output to be a floored integer. When False: retrieve as a float"
    )


    value = OutputSocket(
        datatype=Number,
        name="Value",
        description="The value for the query (typecasted to either a float or an integer).",
    )

    def run(self):
        if self.force_int:
            self.value = int(get_data_container_value(self.datacontainer, self.query, False))
        else:
            self.value = float(get_data_container_value(self.datacontainer, self.query, False))


class GetDataContainerValueBool(Node):
    name = "Get Data Container Boolean Value"
    description = "Get a value from a Data Container Object and return 'True' (Boolean) if it is 'TRUE' or a non-zero number. This is different from normal 'bool' typecasting in Python. All other possibilities for the query's value will result in 'False' being output. Strings will be forced to uppercase before comparision. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the query is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to query.")
    query = InputSocket(
        datatype=String,
        name="Query",
        description="The query to use to extract a value from the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'",
    )

    value = OutputSocket(
        datatype=Boolean,
        name="Value",
        description="The value for the query (typecasted to a boolean value).",
    )

    def run(self):
        v = str(get_data_container_value(self.datacontainer, self.query, False)).upper().strip()
        if v == 'TRUE':
            self.value = True
        elif v == 'FALSE' or v == '0':
            self.value = False
        else:
            try:
                float(v)
                self.value = True
            except ValueError:
                self.value = False


class TestDataContainerValueNumber(Node):
    name = "Test Data Container Has Number Value"
    description = "Get a value from a Data Container Object and type cast it to a Number. Outputs True if the query can be typecasted to a Number value. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'. If the query is invalid, an exception will be raised."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/datastructures.html#dictionaries"]
    categories = ["Data", "Data Container"]
    color = constants.COLOR_DATA_CONTAINER

    datacontainer = InputSocket(datatype=DataContainer, name="Data Container", description="The Data Container object to query.")
    query = InputSocket(
        datatype=String,
        name="Query",
        description="The query to use to extract a value from the Data Container. The value can be queried using dot notation: numbers to index lists, and strings to key into objects. E.g. 'ListValue.0.ObjectValue'",
    )

    value = OutputSocket(
        datatype=Boolean,
        name="Can Be Number?",
        description="True if the output can be a number",
    )

    def run(self):
        try:
            v = get_data_container_value(self.datacontainer, self.query, False)
            float(v)
            int(v)
            self.value = True
        except ValueError:
            self.value = False
