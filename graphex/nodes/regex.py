from graphex import (
    String,
    Boolean,
    Number,
    Node,
    InputSocket,
    OutputSocket,
    ListOutputSocket,
    constants,
)
import typing
import re


class StringMatchesRegex(Node):
    name: str = "String Matches Regex"
    description: str = "Outputs True if the input string matches the regex."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/re.html"]
    categories: typing.List[str] = ["Strings", "Regex"]
    color: str = constants.COLOR_STRING

    string = InputSocket(datatype=String, name="String", description="The string to match against the regex.")
    regex_string = InputSocket(datatype=String, name="Regex", description="The regex to apply to the string.")
    multiline = InputSocket(
        datatype=Boolean,
        name="Multiline",
        description="When specified, the pattern character '^' matches at the beginning of the string and at the beginning of each line (immediately following each newline); and the pattern character '$' matches at the end of the string and at the end of each line (immediately preceding each newline).",
        input_field=True,
    )
    ignore_case = InputSocket(
        datatype=Boolean,
        name="Ignore Case",
        description="Perform case-insensitive matching; expressions like [A-Z] will also match lowercase letters.",
        input_field=False,
    )
    dot_all = InputSocket(
        datatype=Boolean,
        name="Dot-All",
        description="Make the '.' special character match any character at all, including a newline; without this flag, '.' will match anything except a newline.",
        input_field=False,
    )

    result = OutputSocket(datatype=Boolean, name="Result", description="Whether the string matches the regex or not.")

    def run(self):
        flags = 0
        if self.multiline:
            flags = flags | re.MULTILINE
        if self.ignore_case:
            flags = flags | re.IGNORECASE
        if self.dot_all:
            flags = flags | re.DOTALL
        regex = re.compile(self.regex_string, flags=flags)
        search_result = regex.search(self.string)
        if search_result:
            self.result = True
        else:
            self.result = False


class StringRegexReplace(Node):
    name: str = "String Regex Replace"
    description: str = "Replace regex matches in a string."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/re.html"]
    categories: typing.List[str] = ["Strings", "Regex"]
    color: str = constants.COLOR_STRING

    string = InputSocket(datatype=String, name="String", description="The string to replace matches within.")
    regex_string = InputSocket(datatype=String, name="Regex", description="The regex to apply to the string.")
    replacement = InputSocket(
        datatype=String,
        name="Replacement",
        description="The replacement string to replace regex matches with. \\g<number> will substitute in the substring matched by group 'number' (e.g., \\g<2> will reference and insert group 2). The backreference \\g<0> substitutes in the entire substring matched.",
    )
    num_replacements = InputSocket(
        datatype=Number,
        name="Maximum Replacements",
        description="The maximum number of replacements to make within the string. If 0, all matches will be replaced.",
        input_field=0,
    )
    multiline = InputSocket(
        datatype=Boolean,
        name="Multiline",
        description="When specified, the pattern character '^' matches at the beginning of the string and at the beginning of each line (immediately following each newline); and the pattern character '$' matches at the end of the string and at the end of each line (immediately preceding each newline).",
        input_field=True,
    )
    ignore_case = InputSocket(
        datatype=Boolean,
        name="Ignore Case",
        description="Perform case-insensitive matching; expressions like [A-Z] will also match lowercase letters.",
        input_field=False,
    )
    dot_all = InputSocket(
        datatype=Boolean,
        name="Dot-All",
        description="Make the '.' special character match any character at all, including a newline; without this flag, '.' will match anything except a newline.",
        input_field=False,
    )

    result = OutputSocket(datatype=String, name="Result", description="The input string with matches replaced.")

    def run(self):
        flags = 0
        if self.multiline:
            flags = flags | re.MULTILINE
        if self.ignore_case:
            flags = flags | re.IGNORECASE
        if self.dot_all:
            flags = flags | re.DOTALL
        regex = re.compile(self.regex_string, flags=flags)
        self.result = regex.sub(self.replacement, self.string, count=0 if self.num_replacements <= 0 else int(self.num_replacements))


class StringRegexFind(Node):
    name: str = "String Regex Find"
    description: str = "Find a regex match in a string."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/re.html"]
    categories: typing.List[str] = ["Strings", "Regex"]
    color: str = constants.COLOR_STRING

    string = InputSocket(datatype=String, name="String", description="The string to find a match within.")
    regex_string = InputSocket(datatype=String, name="Regex", description="The regex to apply to the string.")
    multiline = InputSocket(
        datatype=Boolean,
        name="Multiline",
        description="When specified, the pattern character '^' matches at the beginning of the string and at the beginning of each line (immediately following each newline); and the pattern character '$' matches at the end of the string and at the end of each line (immediately preceding each newline).",
        input_field=True,
    )
    ignore_case = InputSocket(
        datatype=Boolean,
        name="Ignore Case",
        description="Perform case-insensitive matching; expressions like [A-Z] will also match lowercase letters.",
        input_field=False,
    )
    dot_all = InputSocket(
        datatype=Boolean,
        name="Dot-All",
        description="Make the '.' special character match any character at all, including a newline; without this flag, '.' will match anything except a newline.",
        input_field=False,
    )

    has_match = OutputSocket(datatype=Boolean, name="Match Found?", description="Whether a match was found in the string.")
    match = OutputSocket(
        datatype=String, name="Match", description="The match found by the regex when searching 'String'. If no match was found, this will be an empty string."
    )

    def run(self):
        flags = 0
        if self.multiline:
            flags = flags | re.MULTILINE
        if self.ignore_case:
            flags = flags | re.IGNORECASE
        if self.dot_all:
            flags = flags | re.DOTALL
        regex = re.compile(self.regex_string, flags=flags)
        match = regex.search(self.string)
        if match:
            self.has_match = True
            self.match = match.group(0)
        else:
            self.has_match = False
            self.match = ""


class StringRegexFindGroups(Node):
    name: str = "String Regex Find Groups"
    description: str = "Find a regex match in a string and get all the groups of the match."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/re.html"]
    categories: typing.List[str] = ["Strings", "Regex"]
    color: str = constants.COLOR_STRING

    string = InputSocket(datatype=String, name="String", description="The string to find a match within.")
    regex_string = InputSocket(datatype=String, name="Regex", description="The regex to apply to the string.")
    multiline = InputSocket(
        datatype=Boolean,
        name="Multiline",
        description="When specified, the pattern character '^' matches at the beginning of the string and at the beginning of each line (immediately following each newline); and the pattern character '$' matches at the end of the string and at the end of each line (immediately preceding each newline).",
        input_field=True,
    )
    ignore_case = InputSocket(
        datatype=Boolean,
        name="Ignore Case",
        description="Perform case-insensitive matching; expressions like [A-Z] will also match lowercase letters.",
        input_field=False,
    )
    dot_all = InputSocket(
        datatype=Boolean,
        name="Dot-All",
        description="Make the '.' special character match any character at all, including a newline; without this flag, '.' will match anything except a newline.",
        input_field=False,
    )

    groups = ListOutputSocket(
        datatype=String,
        name="Match Groups",
        description="The match groups found by the regex when searching 'String'. Each index of this list corresponds to the matching group number. Group '0' will be the entire matched string. If no matches were found, this list will be empty.",
    )

    def run(self):
        flags = 0
        if self.multiline:
            flags = flags | re.MULTILINE
        if self.ignore_case:
            flags = flags | re.IGNORECASE
        if self.dot_all:
            flags = flags | re.DOTALL
        regex = re.compile(self.regex_string, flags=flags)
        match = regex.search(self.string)
        if match:
            self.groups = [match.group(0)]
            self.groups.extend([group for group in match.groups("")])
        else:
            self.groups = []


class StringRegexFindAll(Node):
    name: str = "String Regex Find All"
    description: str = "Find all non-overlapping regex matches in a string."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/re.html"]
    categories: typing.List[str] = ["Strings", "Regex"]
    color: str = constants.COLOR_STRING

    string = InputSocket(datatype=String, name="String", description="The string to find a match within.")
    regex_string = InputSocket(datatype=String, name="Regex", description="The regex to apply to the string.")
    multiline = InputSocket(
        datatype=Boolean,
        name="Multiline",
        description="When specified, the pattern character '^' matches at the beginning of the string and at the beginning of each line (immediately following each newline); and the pattern character '$' matches at the end of the string and at the end of each line (immediately preceding each newline).",
        input_field=True,
    )
    ignore_case = InputSocket(
        datatype=Boolean,
        name="Ignore Case",
        description="Perform case-insensitive matching; expressions like [A-Z] will also match lowercase letters.",
        input_field=False,
    )
    dot_all = InputSocket(
        datatype=Boolean,
        name="Dot-All",
        description="Make the '.' special character match any character at all, including a newline; without this flag, '.' will match anything except a newline.",
        input_field=False,
    )

    matches = ListOutputSocket(datatype=String, name="Matches", description="All matches of the regex pattern in string, in the order that they were found.")

    def run(self):
        flags = 0
        if self.multiline:
            flags = flags | re.MULTILINE
        if self.ignore_case:
            flags = flags | re.IGNORECASE
        if self.dot_all:
            flags = flags | re.DOTALL
        regex = re.compile(self.regex_string, flags=flags)

        self.matches = []
        for match in regex.finditer(self.string):
            self.matches.append(match.group(0))
