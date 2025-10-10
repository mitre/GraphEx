from graphex import Number, String, Node, NodeType, InputSocket, OptionalInputSocket, OutputSocket, constants
from dateutil import parser as dateutil_parser
from dateutil import tz as dateutil_tz
import datetime
import typing
import time


class Sleep(Node):
    name: str = "Sleep"
    description: str = "Wait for the given number of seconds."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/time.html#time.sleep"]
    categories: typing.List[str] = ["Miscellaneous", "Time"]
    color = constants.COLOR_TIME

    seconds = InputSocket(datatype=Number, name="Seconds", description="The number of seconds to sleep.", input_field=1)

    def run(self):
        time.sleep(self.seconds)


class CurrentUnixTime(Node):
    node_type = NodeType.GENERATOR
    name: str = "Current Unix Timestamp"
    description: str = "Outputs the current Unix timestamp (seconds since the Epoch). Fractions of a second may be present if the system clock provides them (as seconds.fractions_of_second)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/time.html#time.time"]
    categories: typing.List[str] = ["Miscellaneous", "Time"]
    color = constants.COLOR_TIME

    output = OutputSocket(datatype=Number, name="Unix Time", description="The current Unix timestamp.")

    def run(self):
        self.output = time.time()


class CurrentUnixTimeNanoseconds(Node):
    node_type = NodeType.GENERATOR
    name: str = "Current Unix Timestamp (nanoseconds)"
    description: str = "Outputs the current Unix timestamp (as nanoseconds since the Epoch)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/time.html#time.time_ns"]
    categories: typing.List[str] = ["Miscellaneous", "Time"]
    color = constants.COLOR_TIME

    output = OutputSocket(datatype=Number, name="Unix Time (ns)", description="The current Unix timestamp in nanoseconds.")

    def run(self):
        self.output = time.time_ns()


class CurrentLocalTime(Node):
    node_type = NodeType.GENERATOR
    name: str = "Current Local Date and Time"
    description: str = "Outputs a string representing the current local data and time."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/time.html#time.ctime"]
    categories: typing.List[str] = ["Miscellaneous", "Time"]
    color = constants.COLOR_TIME

    output = OutputSocket(datatype=String, name="Local Date + Time", description="The current local time.")

    def run(self):
        self.output = time.ctime()


class TimezoneName(Node):
    node_type = NodeType.GENERATOR
    name: str = "Timezone Name"
    description: str = "Outputs the name of the server's timezone. If the timezone can include a daylight savings time, will output in the form ('timezone_name', 'timezone_name_in_DST')"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/time.html#time.tzname"]
    categories: typing.List[str] = ["Miscellaneous", "Time"]
    color = constants.COLOR_TIME

    output = OutputSocket(datatype=String, name="Name", description="The name of the server's timezone.")

    def run(self):
        self.output = str(time.tzname)


class ParseDateString(Node):
    name: str = "Parse Date String"
    description: str = "Parse a date into a Unix timestamp (seconds since the Epoch)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/datetime.html#module-datetime"]
    categories: typing.List[str] = ["Miscellaneous", "Time"]
    color = constants.COLOR_TIME

    date_string = InputSocket(datatype=String, name="Date String", description="The date string to parse.")
    date_format = OptionalInputSocket(
        datatype=String,
        name="Date Format",
        description="The date format string used to parse the given date string. If not provided, the date string will be parsed according to known supported formats. In most cases, a custom format string will not need to be provided.\n\nSee https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes for information on valid format codes.",
    )
    timezone = OptionalInputSocket(
        datatype=String,
        name="Timezone",
        description="The timezone to use for parsing the date string. This is only applicable is the timezone cannot be parsed from the date string already (i.e. if the timezone is not included). (e.g. America/New_York)",
    )

    output = OutputSocket(datatype=Number, name="Unix Time", description="The parsed Unix timestamp (seconds since Epoch).")

    def run(self):
        parsed_time = None
        if self.date_format:
            parsed_time = datetime.datetime.strptime(self.date_string, self.date_format)
        else:
            parsed_time = dateutil_parser.parse(self.date_string)
        if parsed_time.tzname() is None and self.timezone:
            parsed_time = parsed_time.replace(tzinfo=dateutil_tz.gettz(self.timezone))
        self.output = parsed_time.astimezone(datetime.timezone.utc).timestamp()


class FormatTime(Node):
    name: str = "Format Unix Timestamp"
    description: str = "Format a Unix timestamp (seconds since the Epoch) into a date string."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/datetime.html#module-datetime"]
    categories: typing.List[str] = ["Miscellaneous", "Time"]
    color = constants.COLOR_TIME

    timestamp = InputSocket(datatype=Number, name="Unix Time", description="The Unix timestamp (seconds since Epoch).")
    date_format = InputSocket(
        datatype=String,
        name="Date Format",
        description="The date format string used to format the given date string. See https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes for information on valid format codes.",
        input_field=r"%Y-%m-%dT%H:%M:%S.%f%z",
    )

    output = OutputSocket(datatype=String, name="Date String", description="The formatted date string.")

    def run(self):
        dt = datetime.datetime.fromtimestamp(self.timestamp, datetime.timezone.utc)
        self.output = dt.strftime(self.date_format)
