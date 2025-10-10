from graphex import String, Boolean, Node, InputSocket, OutputSocket, constants
import typing
import os


class AbsolutePath(Node):
    name: str = "Create Absolute Path"
    description: str = (
        "Turns a relative path into an absolute path. If the relative path doesn't exist (or can't be found), then the input relative path is output again."
    )
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.abspath"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Relative Path", description="The relative path on the filesystem.")

    output = OutputSocket(datatype=String, name="Result", description="An attempt at the absolute path on the filesystem.")

    def run(self):
        self.output = os.path.abspath(self.input)


class RelativePath(Node):
    name: str = "Create Relative Path"
    description: str = "Turns a path into a relative path. If the path doesn't exist (or can't be found), then the input path is output again."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.relpath"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path on the filesystem.")

    output = OutputSocket(datatype=String, name="Result", description="An attempt at the relative path on the filesystem.")

    def run(self):
        self.output = os.path.relpath(self.input)


class ExpandPathHome(Node):
    name: str = "Expand Home Path"
    description: str = "Converts the home character (~ or ~user on Unix) into an actual path."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.expanduser"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="A path containing a reference to 'home' (~)")

    output = OutputSocket(datatype=String, name="Result", description="A path without the home character.")

    def run(self):
        self.output = os.path.expanduser(self.input)


class PathIsFile(Node):
    name: str = "Path is File"
    description: str = "Returns True if the path is a file"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.isfile"]
    categories: typing.List[str] = ["Files", "Pathing", "Conditionals"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the path is a file or not.")

    def run(self):
        self.output = os.path.isfile(self.input)


class PathIsDir(Node):
    name: str = "Path is Directory"
    description: str = "Returns True if the path is a directory (folder)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.isdir"]
    categories: typing.List[str] = ["Files", "Pathing", "Conditionals"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the path is a directory or not.")

    def run(self):
        self.output = os.path.isdir(self.input)


class PathIsLink(Node):
    name: str = "Path is Symbolic Link"
    description: str = "Returns True if the path is a symbolic link (symlink)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.islink"]
    categories: typing.List[str] = ["Files", "Pathing", "Conditionals"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the path is a sybolic link or not.")

    def run(self):
        self.output = os.path.islink(self.input)


class PathExists(Node):
    name: str = "Path Exists"
    description: str = "Returns True if the path exists"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.exists"]
    categories: typing.List[str] = ["Files", "Pathing", "Conditionals"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path to check.")

    output = OutputSocket(datatype=Boolean, name="Result", description="Whether the path exists or not.")

    def run(self):
        self.output = os.path.exists(self.input)


class PathBaseName(Node):
    name: str = "Path Base Name"
    description: str = "Returns 'filename component' part of the path. Assumes the path ends in a filename."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.basename"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path to extract the filename from.")

    output = OutputSocket(datatype=String, name="Result", description="The filename component of the path.")

    def run(self):
        self.output = os.path.basename(self.input)


class PathDirName(Node):
    name: str = "Path Directory Name"
    description: str = "Returns 'directory component' part of the path. If the path only contains directories: outputs the previous directory in the path."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.dirname"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path to extract the directory path from.")

    output = OutputSocket(datatype=String, name="Result", description="The directory component of the path.")

    def run(self):
        self.output = os.path.dirname(self.input)


class PathSplit(Node):
    name: str = "Split path"
    description: str = "Splits a path into the directory and the filename components."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.split"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    input = InputSocket(datatype=String, name="Path", description="The path to split into two components.")

    output_directory = OutputSocket(datatype=String, name="Directory Component", description="The directory portion of the path.")
    output_filename = OutputSocket(datatype=String, name="Filename", description="The filename portion of the path.")

    def run(self):
        parts: typing.Tuple[str, str] = os.path.split(self.input)
        self.output_directory = parts[0]
        if len(parts) > 1:
            self.output_filename = parts[1]
        else:
            self.output_filename = ""


class SplitExtension(Node):
    name: str = "Split Extension"
    description: str = "Split the extension from a pathname. The extension is everything from the last dot to the end, ignoring leading dots."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.splitext"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    path = InputSocket(datatype=String, name="Path", description="The path to split.")

    output_root = OutputSocket(datatype=String, name="Root", description="The root portion of the path.")
    output_ext = OutputSocket(
        datatype=String, name="Extension", description="The extension portion of the path. This may be an empty string if no extension exists."
    )

    def run(self):
        parts = os.path.splitext(self.path)
        self.output_root = parts[0]
        self.output_ext = parts[1]


class PathJoin(Node):
    name: str = "Join Paths"
    description: str = "Combines two pathlike strings into one path. Handles operating system specific characters (e.g. /, \\, etc.)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.path.html#os.path.join"]
    categories: typing.List[str] = ["Files", "Pathing"]
    color: str = constants.COLOR_PATH

    input_1 = InputSocket(datatype=String, name="Path 1", description="The first/beginning/prefix part of the new path to join.")
    input_2 = InputSocket(datatype=String, name="Path 2", description="The second/ending/suffix part of the new path to join.")

    output = OutputSocket(datatype=String, name="Joined Path", description="The joined path of 'Path 1' then 'Path 2'.")

    def run(self):
        self.output = os.path.join(self.input_1, self.input_2)
