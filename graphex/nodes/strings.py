from graphex import (
    String,
    Boolean,
    Number,
    Dynamic,
    Node,
    NodeType,
    NodeDynamicAttributes,
    InputSocket,
    OptionalInputSocket,
    ListInputSocket,
    OutputSocket,
    ListOutputSocket,
    constants,
    InputField,
    Graph,
    NodeMetadata,
    EnumInputSocket
)
from graphex.sockets import _BaseSocket
from graphex.exceptions import InvalidParameterError
from graphex.runtime import base64encode
from graphex.nodes.templates import DynamicInputTemplateNode
import typing
import re


class ConcatenateStrings(Node):
    name: str = "Concatenate Strings"
    description: str = "Concatenate / join two or more strings together into a single string. See 'List to String' for interaction with all datatypes."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.join"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    strings = ListInputSocket(datatype=String, name="Strings", description="The strings to concatenate.")
    separator = InputSocket(datatype=String, name="Separator", description="The separator between concatenated strings.")

    result = OutputSocket(datatype=String, name="Result", description="The result of the concatenation.")

    def run(self):
        sep = self.separator if self.separator else ""
        self.result = sep.join([s for s in self.strings])


class AppendToString(Node):
    name: str = "Append To String"
    description: str = "Append a string onto another string to create a single string (e.g. concatenate strings)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#text"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    base_string = InputSocket(datatype=String, name="Base String", description="The base string to append to.")
    string_to_append = InputSocket(datatype=String, name="String To Append", description="The string to append.")

    result = OutputSocket(datatype=String, name="Result", description="The resulting string (Base String + String To Append).")

    def run(self):
        self.result = self.base_string + self.string_to_append


class FormatStrings(Node):
    name: str = "Format String"
    description: str = "It is not recommended to use this node. USE 'Named Format String' INSTEAD! Format strings into another. Should only be used if you need the 'Base String' to be a variable (which isn't allowed in 'Named Format String')"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.format"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    base = InputSocket(datatype=String, name="Base String", description="The format string (replacement are defined in order by a pair of curly braces {{}}).")
    sub = ListInputSocket(datatype=String, name="Substitutions", description="The string(s) to insert into the format string.")

    result = OutputSocket(datatype=String, name="Result", description="The result of the string format.")

    def run(self):
        self.result = self.base.format(*self.sub)


class FormatStrings1(Node):
    name: str = "Format String (1)"
    description: str = "!!! DEPRECATED !!! THIS NODE IS MARKED FOR FUTURE REMOVAL. Use 'Named Format String' instead... Format a single string into another."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.format"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    base = InputSocket(datatype=String, name="Base String", description="The format string (replacement is defined by a pair of curly braces {{}}).")
    sub = InputSocket(datatype=String, name="Substitution", description="The string to insert into the format string.")

    result = OutputSocket(datatype=String, name="Result", description="The result of the string format.")

    def run(self):
        self.result = self.base.format(self.sub)


class StripString(Node):
    name: str = "Strip String"
    description: str = "Return a copy of the string with leading and trailing characters removed (whitespace by default)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.strip"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to strip.")
    chars = OptionalInputSocket(datatype=String, name="Characters", description="The characters to strip. If empty, whitespace will be stripped by default.")

    output = OutputSocket(datatype=String, name="Result", description="The string with given characters removed.")

    def run(self):
        self.output = self.input.strip(self.chars if self.chars else None)


class PrintLog(Node):
    name: str = "Log (Print)"
    description: str = "Print a string using the built-in logger. When run from the command line, this fuctionality is similar to the python3 'print' function."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#print"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = InputSocket(datatype=String, name="String", description="The string to print.")
    level = EnumInputSocket(datatype=String,name="Level", description="The log level",enum_members=['debug','info','notice','warning','error'],input_field="info")

    def log_prefix(self) -> str:
        return ""

    def run(self):
        self.log(self.value, level=self.level)


class BreakpointLog(Node):
    name: str = "Debug Breakpoint (Log)"
    description: str = "Print a string/log using the built-in logger and optionally exit the program. Useful for debugging behavior at a particular point in the graph."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#print", "https://docs.python.org/3/library/os.html#os._exit", "https://docs.python.org/3/library/sys.html#sys.exit"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    endProgram = InputSocket(datatype=Boolean, name="End Program", description="Whether to end the program after logging or not. This is a destructive exit for debugging purposes and SHOULD NOT BE USED IN PRODUCTION!", input_field=True)
    logGraphInputs = InputSocket(datatype=Boolean, name="Log Graph Inputs", description="Whether to log all the inputs to this graph or not. As this is a debugging node it WILL SHOW PASSWORDS in PLAIN TEXT.", input_field=False)
    logVariables = InputSocket(datatype=Boolean, name="Log Variables", description="Whether to log all the variables in this graph or not.", input_field=False)
    value = InputSocket(datatype=String, name="String", description="The string to print before exiting the program.")
    level = EnumInputSocket(datatype=String,name="Level", description="The log level",enum_members=['debug','info','notice','warning','error'],input_field="info")

    def log_prefix(self) -> str:
        return f"[{self.name}] "

    def run(self):
        import sys, os, time, threading
        # log the "string" specified by the user
        self.log(self.value, level=self.level)
        # log graph outputs
        if self.logGraphInputs:
            if len(self._graph.inputs) > 0:
                self.log(f"Logging all graph inputs to the graph with name: '{self._graph.name}' ...")
            else:
                self.log(f"Graph with name: '{self._graph.name}' has no graph inputs to log.")
            for gi in self._graph.inputs:
                input_name = gi['name']
                input_datatype = gi['datatype']
                if "isList" in gi and gi["isList"]:
                    input_datatype = input_datatype + " List"
                v = self._runtime.inputs[input_name][0]
                if input_name in self._runtime.hide_secret_names:
                    v = "ENCRYPTED_SECRET"
                self.log(f"Input Name: '{input_name}', Input Datatype: '{input_datatype}', Input Value: '{v}'")
        # log variables that exist at this point
        if self.logVariables:
            if len(self._runtime.variables.keys()) > 0:
                self.log(f"Logging all variables to the graph with name: '{self._graph.name}' ...")
                v_dict = self._runtime.variables
                for v_key in v_dict.keys():
                    # value, datatype, islist
                    v_data = self._runtime.variables[v_key]
                    v_datatype = v_data[1].name
                    if v_data[2]:
                        v_datatype = v_datatype + " List"
                    self.log(f"Variable Name: '{v_key}', Variable Datatype: '{v_datatype}', Variable Value: '{v_data[0]}'")
            else:
                self.log(f"Graph with name: '{self._graph.name}' either has no variables to log or there are no variables set/created yet at this breakpoint.")
        # attempt to flush all the logging
        sys.stdout.flush()
        # End the program if specified
        if self.endProgram:
            graph_name = self._graph.name if self._graph.name else "?"
            error_link = base64encode(self.name, self.id, graph_name)
            self.log_critical(f"A breakpoint node has caused the program to end now:\n {error_link}")
            # attempt to flush all the logging
            sys.stdout.flush()
            # attempt to wait for everything to flush to the screen
            time.sleep(1)
            # end the program (harshly if a thread)
            if threading.current_thread().__class__.__name__ == "_MainThread":
                # not a thread, preferred way to exit the program
                sys.exit()
            else:
                # is a thread, need to force kill the program
                # give time for the stdout to flush
                time.sleep(0.1)
                os._exit(1)

class PrintLogImage(Node):
    name: str = "Log Image"
    description: str = "Output an image using the built-in logger. This will appear as a clickable link in the UI output. It will appear as a base64 string from the CLI (and in log files). You can provide either the path to an image file or a base64 string to log. If both values are provided, the base64 string will be used instead of the path to the image file."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#print"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    path_to_file = OptionalInputSocket(datatype=String, name="Path to File", description="(Optional) The path to the image file to add to the terminal output")
    base64_str = OptionalInputSocket(datatype=String, name="Base64 String", description="(Optional) The base64 string representing displayable image data.")

    def log_prefix(self) -> str:
        return ""

    def run(self):
        if not self.path_to_file and not self.base64_str:
            raise InvalidParameterError(
                node_name=self.name, socket_name="Path to File", invalid_param="Nothing provided to either input", valid_params=["A value for either input"]
            )
        self.log_image(base64_str=self.base64_str, path_to_image=self.path_to_file)


class PrintLogList(Node):
    name: str = "Log (Print) List"
    description: str = "Print a list of strings using the built-in logger."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#print"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    values = ListInputSocket(datatype=String, name="Strings", description="The list of strings to print.")
    level = EnumInputSocket(datatype=String,name="Level", description="The log level",enum_members=['debug','info','notice','warning','error'],input_field="info")
    separate_lines = InputSocket(
        datatype=Boolean,
        name="Separate Lines?",
        description="Whether to print each list item on a separate line rather than together as list object.",
        input_field=True,
    )

    def log_prefix(self) -> str:
        return ""

    def run(self):
        if self.separate_lines:
            for val in self.values:
                self.log(str(val), level=self.level)
        else:
            self.log(str(self.values), level=self.level)


class FormatAndPrintLog(Node):
    name: str = "Format & Log (Print)"
    description: str = "!!! DEPRECATED !!! THIS NODE IS MARKED FOR FUTURE REMOVAL. Use 'Named Format String' instead... Format strings into another and print the result using the built-in logger."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.format", "https://docs.python.org/3/library/functions.html#print"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = InputSocket(datatype=String, name="String", description="The string to print (replacement are defined in order by a pair of curly braces {{}}).")
    sub = ListInputSocket(datatype=String, name="Substitutions", description="The string(s) to insert into the format string.")
    level = EnumInputSocket(datatype=String,name="Level", description="The log level",enum_members=['debug','info','notice','warning','error'],input_field="info")

    result = OutputSocket(datatype=String, name="Result", description="The result of the string format.")

    def log_prefix(self) -> str:
        return ""

    def run(self):
        self.result = self.value.format(*self.sub)
        self.log(self.result, level=self.level)


class FormatAndPrintLog1(Node):
    name: str = "Format & Log (Print) (1)"
    description: str = "!!! DEPRECATED !!! THIS NODE IS MARKED FOR FUTURE REMOVAL. Use 'Named Format String' instead... Format a string into another and print the result using the built-in logger."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.format", "https://docs.python.org/3/library/functions.html#print"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = InputSocket(datatype=String, name="String", description="The string to print (replacement is defined by a pair of curly braces {{}}).")
    sub = InputSocket(datatype=String, name="Substitution", description="The string to insert into the format string.")
    level = EnumInputSocket(datatype=String,name="Level", description="The log level",enum_members=['debug','info','notice','warning','error'],input_field="info")

    result = OutputSocket(datatype=String, name="Result", description="The result of the string format.")

    def log_prefix(self) -> str:
        return ""

    def run(self):
        self.result = self.value.format(self.sub)
        self.log(self.result, level=self.level)


class UppercaseString(Node):
    name: str = "Uppercase String"
    description: str = "Convert all characters in a string to Uppercase."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.upper"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to convert to uppercase.")

    output = OutputSocket(datatype=String, name="Result", description="The string converted to uppercase.")

    def run(self):
        self.output = self.input.upper()


class LowercaseString(Node):
    name: str = "Lowercase String"
    description: str = "Convert all characters in a string to Lowercase."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.lower"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to convert to lowercase.")

    output = OutputSocket(datatype=String, name="Result", description="The string converted to lowercase.")

    def run(self):
        self.output = self.input.lower()


class StringEndsWith(Node):
    name: str = "String Ends With"
    description: str = "Outputs True if the input string ends with (has as a suffix) the provided substring. Character case matters."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.endswith"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check the ending of.")
    substring_input = InputSocket(datatype=String, name="Substring", description="The (sub)string to search for.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the string ends with the substring.")

    def run(self):
        self.output = self.input.endswith(self.substring_input)


class StringEndsWithAny(Node):
    name: str = "String Ends With Any"
    description: str = "Outputs True if the input string ends with (has as a suffix) any of the provided substrings. Character case matters."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.endswith"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check the ending of.")
    substring_input = ListInputSocket(datatype=String, name="Substrings", description="The (sub)strings to search for.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the string ends with any of the substrings.")

    def run(self):
        self.output = any([self.input.endswith(s) for s in self.substring_input])


class StringStartsWith(Node):
    name: str = "String Starts With"
    description: str = "Outputs True if the input string starts with (has as a prefix) the provided substring. Character case matters."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.startswith"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check the start of.")
    substring_input = InputSocket(datatype=String, name="Substring", description="The (sub)string to search for.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the string starts with the substring.")

    def run(self):
        self.output = self.input.startswith(self.substring_input)


class StringStartsWithAny(Node):
    name: str = "String Starts With Any"
    description: str = "Outputs True if the input string starts with (has as a prefix) any of the provided substrings. Character case matters."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.startswith"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check the start of.")
    substring_input = ListInputSocket(datatype=String, name="Substrings", description="The (sub)strings to search for.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the string starts with any of the substrings.")

    def run(self):
        self.output = any([self.input.startswith(s) for s in self.substring_input])


class StringLength(Node):
    name: str = "Length of String"
    description: str = "Counts the number of characters in a string and outputs the length."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#len"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to count.")

    output = OutputSocket(datatype=Number, name="Length", description="The length of the string.")

    def run(self):
        self.output = len(self.input)


class StringFindSubstring(Node):
    name: str = "Find Substring in String"
    description: str = "Find the index of the substring in the string and output it. If the substring is not found: will output -1."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.find"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string being searched.")
    substring_input = InputSocket(datatype=String, name="Substring", description="The (sub)string to search for.")
    start_index = InputSocket(datatype=Number, name="Starting Index", description="The index to start searching from.")
    end_index = OptionalInputSocket(datatype=Number, name="Ending Index", description="The index to stop looking at (no value indicates until end of string).")

    output = OutputSocket(datatype=Number, name="Index", description="The index of the found substring or -1.")

    def run(self):
        end_index = int(self.end_index) if self.end_index is not None else None
        self.output = self.input.find(self.substring_input, int(self.start_index), end_index)


class StringReverseFindSubstring(Node):
    name: str = "Reverse Find Substring in String"
    description: str = (
        "Find the index of the substring in the string (starting from the end of the string) and output it. If the substring is not found: will output -1."
    )
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.rfind"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string being searched.")
    substring_input = InputSocket(datatype=String, name="Substring", description="The (sub)string to search for.")
    start_index = InputSocket(datatype=Number, name="Starting Index", description="The index to start searching from (not reversed).")
    end_index = OptionalInputSocket(
        datatype=Number, name="Ending Index", description="The index to stop looking at (no value indicates until end of string) (not reversed)."
    )

    output = OutputSocket(datatype=Number, name="Index", description="The index of the found substring or -1.")

    def run(self):
        end_index = int(self.end_index) if self.end_index is not None else None
        self.output = self.input.rfind(self.substring_input, int(self.start_index), end_index)


class CountSubstringInString(Node):
    name: str = "Count Substring in String"
    description: str = "Counts the number of times a substring occurs in the given string and outputs it."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.count"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to count inside.")
    substring_input = InputSocket(datatype=String, name="Substring", description="The (sub)string to search for.")
    start_index = InputSocket(datatype=Number, name="Starting Index", description="The index to start searching from.")
    end_index = OptionalInputSocket(datatype=Number, name="Ending Index", description="The index to stop looking at (no value indicates until end of string).")

    output = OutputSocket(datatype=Number, name="Result", description="The number of occurances of the substring.")

    def run(self):
        end_index: typing.Union[int, None] = int(self.end_index) if self.end_index is not None else None
        self.output = self.input.count(self.substring_input, int(self.start_index), end_index)


class StringIsAscii(Node):
    name: str = "String is ASCII"
    description: str = "Outputs true if the string contains only ASCII characters."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.isascii"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="The result of the ASCII check.")

    def run(self):
        self.output = self.input.isascii()


class StringIsSpace(Node):
    name: str = "String is White Space"
    description: str = "Outputs true if the string contains only whitespace. A string is whitespace if all characters in the string are whitespace and there is at least one character in the string."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.isspace"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="The result of the whitespace check.")

    def run(self):
        self.output = self.input.isspace()


class StringIsUpper(Node):
    name: str = "String is Uppercase"
    description: str = "Outputs true if the string contains only uppercase characters"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.isupper"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="The result of the uppercase check.")

    def run(self):
        self.output = self.input.isupper()


class StringIsLower(Node):
    name: str = "String is Lowercase"
    description: str = "Outputs true if the string contains only lowercase characters"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.lower"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="The result of the lowercase check")

    def run(self):
        self.output = self.input.islower()


class StringReplace(Node):
    name: str = "Replace Substring in String"
    description: str = "Replaces occurances of the substring in the string with new substrings."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.replace"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to replace occurances in.")
    old_substring = InputSocket(datatype=String, name="Old", description="The substring to replace.")
    new_substring = InputSocket(datatype=String, name="New", description="The substring to insert.")
    num_replaces = InputSocket(
        datatype=Number,
        name="Count",
        description="Maximum number of occurrences to replace. -1 (the default value) means replace all occurrences.",
        input_field=-1,
    )

    output = OutputSocket(datatype=String, name="Result", description="The string with occurances of 'Old' replaced with 'New'.")

    def run(self):
        self.output = self.input.replace(self.old_substring, self.new_substring, int(self.num_replaces))


class SplitString(Node):
    name: str = "Split String"
    description: str = "Breaks a string around the specified delimiter."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.split"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to break into smaller strings.")
    sep = OptionalInputSocket(
        datatype=String, name="Delimiter", description="The delimiter string in which to split on (default when empty is to split according to any whitespace)."
    )
    maxsplit = InputSocket(
        datatype=Number, name="Max Split", description="The maximum number of splits to make. -1 (the default value) means no limit.", input_field=-1
    )

    output = ListOutputSocket(datatype=String, name="Split", description="The results of the string split.")

    def run(self):
        sep: typing.Union[str, None] = self.sep if self.sep else None
        self.output = self.input.split(sep, maxsplit=int(self.maxsplit))


class SplitStringAround(Node):
    name: str = "Split String Around"
    description: str = "Breaks a string around the specified delimiter into two separate strings. If multiple occurances of the delimiter exist, the split will happen around the first occurance."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.split"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to break into two smaller strings.")
    sep = OptionalInputSocket(
        datatype=String, name="Delimiter", description="The delimiter string in which to split on (default when empty is to split according to any whitespace)."
    )

    first_string = OutputSocket(
        datatype=String,
        name="Before Delimiter",
        description="The first segment (before the delimiter). If the delimiter is not found in the string, this will be the whole (original) string.",
    )
    second_string = OutputSocket(
        datatype=String,
        name="After Delimiter",
        description="The second segment (after the delimiter). If the delimiter is not found in the string, this will be an empty string.",
    )

    def run(self):
        sep: typing.Union[str, None] = self.sep if self.sep else None
        split = self.input.split(sep, maxsplit=1)
        self.first_string = split[0]
        self.second_string = split[1] if len(split) == 2 else ""


class StringChars(Node):
    name: str = "String Characters"
    description: str = "Breaks a string into individual characters."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#arbitrary-argument-lists", "https://docs.python.org/3/tutorial/controlflow.html#unpacking-argument-lists"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string to break into characters.")

    output = ListOutputSocket(datatype=String, name="Characters", description="The characters of the string.")

    def run(self):
        self.output = [*self.input]


class StringSlice(Node):
    name: str = "Slice Substring"
    description: str = "Slices (extracts) a string on the provided indices and returns the substring."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/introduction.html#text"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input_string = InputSocket(datatype=String, name="String", description="The string to slice.")
    index_1 = InputSocket(datatype=Number, name="Starting Index", description="Where to start the slice from.")
    index_2 = OptionalInputSocket(datatype=Number, name="Ending Index", description="Where to end the slice at (no value indicates until end of string)")

    output = OutputSocket(datatype=String, name="Substring", description="The substring between the specified indices.")

    def run(self):
        end = self.index_2 if self.index_2 is not None else len(self.input_string)
        self.output = self.input_string[self.index_1 : end]


class AsciiString(Node):
    name: str = "ASCII String"
    description: str = "Returns an ASCII string with non-ASCII characters 'escaped'"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#ascii"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input_string = InputSocket(datatype=String, name="String", description="The string to convert.")

    output = OutputSocket(datatype=String, name="ASCII String", description="An ASCII string with non-ASCII characters 'escaped'")

    def run(self):
        self.output = ascii(self.input_string)


class UnicodeValueToString(Node):
    name: str = "Unicode Number to String"
    description: str = "Converts an integer value representing a unicode character into the unicode character (as a string)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#chr"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input_number = InputSocket(datatype=Number, name="Unicode Number", description="The value of the unicode character.")

    output_string = OutputSocket(datatype=String, name="Unicode String", description="The string representation of the value.")

    def run(self):
        self.output_string = chr(int(self.input_number))


class StringToUnicodeValue(Node):
    name: str = "Unicode String to Number"
    description: str = "Converts an string value representing a unicode character into the unicode character's ('code point') value (as a Number)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/functions.html#ord"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input_string = InputSocket(
        datatype=String,
        name="Unicode String",
        description="The string representation of a unicode character. Only the first character in the string is used.",
    )

    output_value = OutputSocket(datatype=Number, name="Unicode Number", description="The value of the unicode character.")

    def run(self):
        if len(self.input_string) > 1:
            self.output_value = ord(self.input_string[0])
        else:
            self.output_value = ord(self.input_string)


class StringsEqual(Node):
    name: str = "Equal (String)"
    description: str = "Outputs True if the strings are equal / identical."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    string1 = InputSocket(datatype=String, name="String 1", description="The first string to compare.")
    string2 = InputSocket(datatype=String, name="String 2", description="The second string to compare.")

    result = OutputSocket(datatype=Boolean, name="Result", description="Whether the strings are equal or not.")

    def run(self):
        self.result = self.string1 == self.string2


class StringsEqualAny(Node):
    name: str = "Equal Any (String)"
    description: str = "Outputs True if a string is equal / identical to any other string in the given list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    string = InputSocket(datatype=String, name="String", description="The first string to compare.")
    comparison_strings = ListInputSocket(datatype=String, name="Comparison Strings", description="The strings to compare.")

    result = OutputSocket(datatype=Boolean, name="Result", description="Whether 'String' is equal to any of the other strings.")

    def run(self):
        self.result = any([self.string == s for s in self.comparison_strings])


class StringsNotEqual(Node):
    name: str = "Not Equal (String)"
    description: str = "Outputs True if the strings are not equal / not identical."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    string1 = InputSocket(datatype=String, name="String 1", description="The first string to compare.")
    string2 = InputSocket(datatype=String, name="String 2", description="The second string to compare.")

    result = OutputSocket(datatype=Boolean, name="Result", description="True if the strings are not identical.")

    def run(self):
        self.result = self.string1 != self.string2


class Newline(Node):
    node_type = NodeType.GENERATOR
    name: str = "Newline (\\n)"
    description: str = "A newline character."
    hyperlink: typing.List[str] = ["https://en.wikipedia.org/wiki/Newline"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = OutputSocket(datatype=String, name="Value", description="The newline (\\n) character.")

    def run(self):
        self.value = "\n"


class AppendNewlineToString(Node):
    name: str = "Append Newline To String"
    description: str = "Append a newline (\\n) onto the provided string. You do not need to provide the newline character itself in the 'String' inputbox."
    hyperlink: typing.List[str] = ["https://en.wikipedia.org/wiki/Newline"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    string = InputSocket(datatype=String, name="String", description="The base string to append a newline to.")

    result = OutputSocket(datatype=String, name="Result", description="The resulting string (Base String + New Line (\\n)).")

    def run(self):
        self.result = self.string + "\n"


class CarriageReturn(Node):
    node_type = NodeType.GENERATOR
    name: str = "Carriage Return (\\r)"
    description: str = "A carriage return character."
    hyperlink: typing.List[str] = ["https://en.wikipedia.org/wiki/Carriage_return"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = OutputSocket(datatype=String, name="Value", description="The carriage return (\\r) character.")

    def run(self):
        self.value = "\r"


class TabCharacter(Node):
    node_type = NodeType.GENERATOR
    name: str = "Tab (\\t)"
    description: str = "A tab character."
    hyperlink: typing.List[str] = ["https://en.wikipedia.org/wiki/Tab_key"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = OutputSocket(datatype=String, name="Value", description="The tab (\\t) character.")

    def run(self):
        self.value = "\t"


class CRLF(Node):
    node_type = NodeType.GENERATOR
    name: str = "CRLF (\\r\\n)"
    description: str = "The CRLF (\\r\\n) sequence."
    hyperlink: typing.List[str] = ["https://en.wikipedia.org/wiki/Carriage_return", "https://en.wikipedia.org/wiki/Newline"]
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = OutputSocket(datatype=String, name="Value", description="The CRLF (\\r\\n) sequence.")

    def run(self):
        self.value = "\r\n"


class StringContainsSubstring(Node):
    name: str = "String Contains Substring"
    description: str = "Outputs True if the substring is found inside of the string."
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string being searched.")
    substring_input = InputSocket(datatype=String, name="Substring", description="The (sub)string to search for.")

    output = OutputSocket(datatype=Boolean, name="Contains?", description="True if the substring is found inside of the string.")

    def run(self):
        self.output = self.substring_input in self.input


class StringContainsAnySubstring(Node):
    name: str = "String Contains Any Substring"
    description: str = "Outputs True if any of the given substrings are found inside of the string."
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string being searched.")
    substring_input = ListInputSocket(datatype=String, name="Substrings", description="The (sub)strings to search for.")

    output = OutputSocket(datatype=Boolean, name="Contains Any?", description="True if any of the substrings are found inside of the string.")

    def run(self):
        self.output = any([s in self.input for s in self.substring_input])


class StringContainsAllSubstring(Node):
    name: str = "String Contains All Substrings"
    description: str = "Outputs True if all of the given substrings are found inside of the string."
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string being searched.")
    substring_input = ListInputSocket(datatype=String, name="Substrings", description="The (sub)strings to search for.")

    output = OutputSocket(datatype=Boolean, name="Contains All?", description="True if all of the substrings are found inside of the string.")

    def run(self):
        self.output = all([s in self.input for s in self.substring_input])


class StringIsEmpty(Node):
    name: str = "String Is Empty"
    description: str = "Outputs True if the string is the empty string (different from white space)"
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string being checked.")
    output = OutputSocket(datatype=Boolean, name="Empty?", description="True if the string is empty.")

    def run(self):
        self.output = len(self.input) == 0


class StringIsEmptyOrWhitespace(Node):
    name: str = "String Is Empty Or Whitespace"
    description: str = "Outputs True if the string is the empty string or contains only whitespace."
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    input = InputSocket(datatype=String, name="String", description="The string being checked.")
    output = OutputSocket(datatype=Boolean, name="Empty or Whitespace?", description="True if the string is empty or contains only whitespace.")

    def run(self):
        self.output = len(self.input.strip()) == 0


class EmptyString(Node):
    node_type = NodeType.GENERATOR
    name: str = "Empty String"
    description: str = "A String with no characters in it (i.e. '')"
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = OutputSocket(datatype=String, name="Value", description="The empty string.")

    def run(self):
        self.value = ""


class SpaceString(Node):
    node_type = NodeType.GENERATOR
    name: str = "Space String"
    description: str = "A String representing a single space (i.e. ' ')"
    categories: typing.List[str] = ["Strings"]
    color: str = constants.COLOR_STRING

    value = OutputSocket(datatype=String, name="Value", description="The empty string.")

    def run(self):
        self.value = " "


class NamedFormatString(Node):
    name: str = "Named Format String"
    description: str = r"Format a string dynamically by adding input sockets wherever you want in a block of text. Within the provided string (textbox), use the formatting {Name} to provide a position in which to insert a value (e.g. You could type something like: 'My name is {name}'). When you are done templating your text box, left-click with your mouse somewhere outside of the textbox to cause your socket inputs to appear. You can escape curly braces using the standard escape backslash character: \ (i.e. \{ and \} can be used to escape from creating inputs.)"
    categories: typing.List[str] = ["Strings"]
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/stdtypes.html#str.format"]
    color: str = constants.COLOR_STRING

    result = OutputSocket(datatype=String, name="Result", description="The formatted string that you built in the 'template string' textbox below.")

    field = InputField(default_value="", name="Template String", multiline=True)

    @classmethod
    def get_templates(cls, s: str) -> typing.List[typing.Tuple[int, int, str]]:
        """
        Get templates from the given string.

        :param s: The string to parse templates from.

        :returns: A list of tuples (Start Index, End Index, Input Name)
        """
        template_regex = re.compile(r"(?<!\\)\{\s*.*?\s*(?<!\\)\}", flags=re.IGNORECASE)
        templates: typing.List[typing.Tuple[int, int, str]] = []
        for match in template_regex.finditer(s):
            input_name = match.group(0)[1:-1]
            if len(input_name.strip()) == 0:
                input_name = '{}'
            templates.append((match.start(0), match.end(0), input_name))

        return templates

    def run(self):
        field_value = self.field
        templates = self.get_templates(field_value)

        dynamic_attributes = self.dynamic_attributes(self._graph, self._instance_metadata)
        if dynamic_attributes.error:
            raise RuntimeError(dynamic_attributes.error)

        sockets = dynamic_attributes.sockets or []

        # Iterate and replace in reverse order
        # This makes it so that positions are not affected by the changing string size
        s = field_value
        for start, end, input_name in templates[::-1]:
            found_socket = next(
                iter(
                    [
                        socket
                        for socket in sockets
                        if socket.datatype and socket.name == input_name
                    ]
                ),
                None,
            )

            if not found_socket:
                raise RuntimeError(f"No matching input socket for template '{s[start:end]}' ... (name was: '{input_name}')")

            s = s[0:start] + str(found_socket.get_value(self)) + s[end:]

        self.result = s.replace('\{', '{').replace('\}', '}')

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            field_value = str(instance_metadata.get("fieldValue", ""))
            templates = cls.get_templates(field_value)

            sockets: typing.List[_BaseSocket] = []
            for start, end, input_name in templates:
                if any([socket.name == input_name for socket in sockets]):
                    continue

                # conflict = next(iter([t for t in templates if t[2] == input_name]), None)
                # if conflict:
                #     raise RuntimeError(f"Conflicting template for '{input_name}' ( {field_value[start:end]} conflicts with {field_value[conflict[0]: conflict[1]]} )")

                sockets.append(InputSocket(datatype=String, name=input_name, description=f"Value for the '{field_value[start:end]}' template."))

            return NodeDynamicAttributes(sockets, None, None, None)
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))


class ListToString(DynamicInputTemplateNode):
    name: str = "List to String"
    description: str = "Converts a list of any datatype into a single string. The contents of the string will depend upon what the 'String' representation of the input datatype. If the input datatype is an object and for some reason can't be converted to a string, an error could occur. Also see the 'Concatenate Strings' node."
    categories: typing.List[str] = ["Strings", "Conditionals"]
    color: str = constants.COLOR_STRING

    list_items = ListInputSocket(
        datatype=Dynamic,
        name="List",
        description="The list to iterate over and turn into a single String. This can be a list of any type.",
    )
    separator = InputSocket(datatype=String, name="Separator", description="The separator between joined (concatenated) items.", input_field=", ")
    result = OutputSocket(datatype=String, name="String Representation", description="The string representation of the input list.")

    def run(self):
        dynamic_attributes = self.dynamic_attributes(self._graph, self._instance_metadata)
        if dynamic_attributes.error:
            raise RuntimeError(dynamic_attributes.error)
        
        sep = self.separator if self.separator else ""
        self.result = sep.join([str(e) for e in self.list_items])
    
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
                        description="The list to iterate over and turn into a single String. This can be a list of any type.",
                    )
                ],
                description=f"Iterate/loop for each item in a '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, error=str(e))
