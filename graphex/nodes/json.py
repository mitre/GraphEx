from graphex import String, Boolean, Node, InputSocket, ListInputSocket, OutputSocket, constants, exceptions
import typing
import json


class CreateJSONString(Node):
    name: str = "Create JSON String"
    description: str = "Creates a JSON string out of input key/value pairs. Each input string should be of the form key:value. The character ':' should only be used as shown in the example."
    hyperlink: typing.List[str] = ["https://www.json.org/json-en.html"]
    categories: typing.List[str] = ["Strings", "JSON"]
    color: str = constants.COLOR_STRING

    key_value_pairs = ListInputSocket(datatype=String, name="Key:Value Pairs", description="Strings specifically formatted to be ingested into a JSON string.")

    output_json_str = OutputSocket(datatype=String, name="JSON string", description="A JSON string holding the provided key:value pairs.")

    def run(self):
        d = {}
        for key_value_pair in self.key_value_pairs:
            split = key_value_pair.split(":")
            if len(split) <= 1 or len(split) > 2:
                raise exceptions.StringFormattingError(
                    self.name, "Key:Value Pairs", key_value_pair, "String should contain exactly one ':' character separating the key from the value."
                )
            key = split[0].strip()
            value = split[1].strip()
            d[key] = value
        self.output_json_str = json.dumps(d)


class ExtractStringFromJSON(Node):
    name: str = "Extract Value from JSON"
    description: str = "Outputs the value for a given key in a JSON string (or empty string if the key doesn't exist)."
    hyperlink: typing.List[str] = ["https://www.json.org/json-en.html"]
    categories: typing.List[str] = ["Strings", "JSON"]
    color: str = constants.COLOR_STRING

    input_json = InputSocket(datatype=String, name="JSON String", description="The JSON string to extract a value from.")
    search_key = InputSocket(datatype=String, name="Key", description="The key to look for in the JSON")

    output_value = OutputSocket(datatype=String, name="Value", description="The value of Key in the JSON string or an empty string.")

    def run(self):
        d = json.loads(self.input_json)
        if self.search_key in d:
            found = d[self.search_key]
        elif self.search_key.strip() in d:
            found = d[self.search_key.strip()]
        else:
            self.output_value = ""
            return
        if isinstance(found, dict) or isinstance(found, list):
            self.output_value = json.dumps(found)
        else:
            self.output_value = str(found)


class StringIsJSON(Node):
    name: str = "String is JSON"
    description: str = "Outputs True if the string can be loaded as JSON."
    hyperlink: typing.List[str] = ["https://www.json.org/json-en.html"]
    categories: typing.List[str] = ["Strings", "JSON"]
    color: str = constants.COLOR_STRING

    input_json = InputSocket(datatype=String, name="String", description="The string to test as JSON")

    output_result = OutputSocket(datatype=Boolean, name="Result", description="The result of the JSON string check.")

    def run(self):
        try:
            json.loads(self.input_json)
            self.output_result = True
        except Exception:
            self.output_result = False
