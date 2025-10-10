from graphex import String, Number, Boolean, Node, NodeType, InputSocket, OutputSocket, LinkOutputSocket, ListOutputSocket, constants
import tempfile
import hashlib
import typing
import shutil
import glob
import os


class GraphEXRoot(Node):
    node_type = NodeType.GENERATOR
    name: str = "GraphEX Root"
    description: str = "Get the GraphEX root directory. This can be used to create paths relative to the GraphEX directory structure."
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    root = OutputSocket(datatype=String, name="GraphEX Root Directory", description="The GraphEX root directory (root of the graph file systen).")

    def run(self):
        self.root = self._runtime.registry.root


class WriteToFile(Node):
    name: str = "Write String to File"
    description: str = (
        "Writes an input string to a file on the filesystem. Existing files will be overwritten or appended. Will output the number of characters written."
    )
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    string_value = InputSocket(datatype=String, name="String", description="The string to write to the filesystem.")
    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file to write to")
    append = InputSocket(
        datatype=Boolean,
        name="Append?",
        description="When set to True: Will add text to the bottom of an existing file instead of overwriting an existing file with the same path.",
        input_field=False,
    )

    output = OutputSocket(datatype=Number, name="Characters Written", description="How many characters were written to the file.")

    def run(self):
        write_char: str = "a" if self.append else "w"
        with open(self.filepath_value, mode=write_char) as w_file:
            self.output = w_file.write(self.string_value)


class ReadFromFile(Node):
    name: str = "Read File into String"
    description: str = "Reads a given file path and outputs a string containing the file's contents."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file to read from")

    output = OutputSocket(datatype=String, name="File Contents", description="The entire contents of the file.")

    def run(self):
        with open(self.filepath_value, "r") as r_file:
            self.output = r_file.read()


class FileSize(Node):
    name: str = "Size of File"
    description: str = "Outputs the size of a file in bytes"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.stat"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file to get the size of.")

    output = OutputSocket(datatype=Number, name="File Size", description="The size of the file.")

    def run(self):
        self.output = os.stat(self.filepath_value).st_size


class FileMode(Node):
    name: str = "File Mode"
    description: str = "Outputs the file type and file mode bits"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.stat"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file to get the size of.")

    output = OutputSocket(datatype=Number, name="Mode", description="The file type and file mode bits")

    def run(self):
        self.output = os.stat(self.filepath_value).st_mode


class FileOwner(Node):
    name: str = "Owner of File"
    description: str = "Outputs the owner of a file"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.stat"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file.")

    output = OutputSocket(datatype=Number, name="Owner", description="The owner of the file.")

    def run(self):
        self.output = os.stat(self.filepath_value).st_uid


class FileGroup(Node):
    name: str = "Group of File"
    description: str = "Outputs the owning group of a file"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.stat"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file.")

    output = OutputSocket(datatype=Number, name="Group", description="The group of the file.")

    def run(self):
        self.output = os.stat(self.filepath_value).st_gid


class FileAccessed(Node):
    name: str = "File Last Accessed Time"
    description: str = "The last time the file was accessed (in seconds)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.stat"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file.")

    output = OutputSocket(datatype=Number, name="Time", description="The last access time of the file.")

    def run(self):
        self.output = os.stat(self.filepath_value).st_atime


class FileModified(Node):
    name: str = "File Last Modified Time"
    description: str = "The last time the file was modified (in seconds)"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.stat"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path (including filename) to the file.")

    output = OutputSocket(datatype=Number, name="Time", description="The last modified time of the file.")

    def run(self):
        self.output = os.stat(self.filepath_value).st_mtime


class CreateDirectory(Node):
    name: str = "Create Directory (mkdir/makedirs)"
    description: str = "Calls 'makedirs' on the local machine to create the requested path. This will make all intermediate-level directories needed to contain the leaf directory. Will not error if the path already exists. May error if the provided path is invalid."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.makedirs"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="Directory Path", description="The directory path to create.")

    def run(self):
        os.makedirs(self.filepath_value, exist_ok=True)


class RemoveFile(Node):
    name: str = "Remove File"
    description: str = "Removes a file from the agent. Will not remove a directory."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.remove"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath_value = InputSocket(datatype=String, name="File Path", description="The path to the file to remove.")

    def run(self):
        if os.path.exists(self.filepath_value):
            os.remove(self.filepath_value)


class TemporaryDirectory(Node):
    node_type = NodeType.GENERATOR
    name: str = "Temporary Directory"
    description: str = "Create and get temporary directory on the local system. This directory will automatically be removed when the graph completes. A new temporary directory will be created each time this node is evaluated."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryDirectory"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    tempdir = OutputSocket(datatype=String, name="Temporary Directory", description="The absolute path to the created temporary directory.")

    def run(self):
        tempdir = tempfile.TemporaryDirectory(prefix="graphex-")
        self.tempdir = tempdir.name

        def remove_tempdir():
            tempdir.cleanup()

        self.defer(remove_tempdir)


class CreateTemporaryDirectory(Node, include_forward_link=False):
    name: str = "Create Temporary Directory"
    description: str = "Create a temporary directory on the local system. This directory will automatically be removed when the corresponding branch completes."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryDirectory"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    tempdir_branch = LinkOutputSocket(
        name="Use Temporary Directory",
        description="The branch of execution making use of the temporary directory. The temporary directory will be removed when this branch completes.",
    )
    tempdir = OutputSocket(datatype=String, name="Temporary Directory", description="The absolute path to the created temporary directory.")
    continue_branch = LinkOutputSocket(name="Continue", description="The branch of execution to continue to graph after making use of the temporary directory.")

    def run(self):
        with tempfile.TemporaryDirectory(prefix="graphex-") as tempdir:
            self.tempdir = tempdir

            # Continue down the 'Use Temporary Directory' line
            for node in self.forward("Use Temporary Directory"):
                self._runtime.execute_node(node)

    def run_next(self):
        for node in self.forward("Continue"):
            self._runtime.execute_node(node)


class FileHash(Node):
    name: str = "Hash File"
    description: str = "Get the hash / checksum for a file."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/hashlib.html#usage"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    filepath = InputSocket(datatype=String, name="File Path", description="The path to the file.")
    hash_type = InputSocket(
        datatype=String,
        name="Hash Function Name",
        description="The name of the hash function to use. One of: md5, sha1, sha224, sha256, sha384, sha512, sha3_224, sha3_256, sha3_384, sha3_512, shake_128, shake_256, blake2b, blake2s.",
        input_field="sha256",
    )

    hash_value = OutputSocket(datatype=String, name="Hash Value", description="The hash / digest value of the file.")

    def run(self):
        h: hashlib._Hash = getattr(hashlib, self.hash_type.lower())()
        with open(self.filepath, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                h.update(data)
        self.hash_value = h.hexdigest()


class ListFiles(Node):
    name: str = "List Paths"
    description: str = "List paths (files and directories) contained within the given directory. The result does not include the special entries '.' and '..' even if they are present in the directory."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.listdir"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    target_path = InputSocket(
        datatype=String,
        name="Path",
        description="The directory to list paths in.",
    )
    include_files = InputSocket(datatype=Boolean, name="Include Files", description="Whether to include files in the results.", input_field=True)
    include_directories = InputSocket(
        datatype=Boolean, name="Include Directories", description="Whether to include directories in the results.", input_field=True
    )
    include_symlinks = InputSocket(
        datatype=Boolean, name="Include Symbolic Links", description="Whether to include symbolic links in the results.", input_field=False
    )
    abspaths = InputSocket(datatype=Boolean, name="Absolute Paths", description="Whether to return the results as list of absolute paths.", input_field=False)

    found_paths = ListOutputSocket(datatype=String, name="Found Paths", description="The found paths.")

    def run(self):
        all_paths = [os.path.join(self.target_path, f) for f in os.listdir(self.target_path)]
        if self.abspaths:
            all_paths = [os.path.abspath(f) for f in all_paths]
        if not self.include_files:
            all_paths = [f for f in all_paths if not os.path.isfile(f)]
        if not self.include_directories:
            all_paths = [f for f in all_paths if not os.path.isdir(f)]
        if not self.include_symlinks:
            all_paths = [f for f in all_paths if not os.path.islink(f)]
        self.found_paths = sorted(all_paths)


class GlobFiles(Node):
    name: str = "Glob Paths"
    description: str = "List paths (files and directories) using a glob file pattern according to the rules used by the Unix shell. No tilde expansion is done, but *, ?, and character ranges expressed with [] will be correctly matched."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/glob.html#glob.glob"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    pattern = InputSocket(
        datatype=String,
        name="Pattern",
        description="The glob file pattern according to the rules used by the Unix shell. No tilde expansion is done, but *, ?, and character ranges expressed with [] will be correctly matched.",
    )
    include_files = InputSocket(datatype=Boolean, name="Include Files", description="Whether to include files in the results.", input_field=True)
    include_directories = InputSocket(
        datatype=Boolean, name="Include Directories", description="Whether to include directories in the results.", input_field=True
    )
    include_symlinks = InputSocket(
        datatype=Boolean, name="Include Symbolic Links", description="Whether to include symbolic links in the results.", input_field=False
    )
    abspaths = InputSocket(datatype=Boolean, name="Absolute Paths", description="Whether to return the results as list of absolute paths.", input_field=False)
    recursive = InputSocket(
        datatype=Boolean,
        name="Recursive",
        description="If True, the pattern '**' will match any files and zero or more directories and subdirectories.",
        input_field=False,
    )

    found_paths = ListOutputSocket(datatype=String, name="Found Paths", description="The found paths.")

    def run(self):
        all_paths = [f for f in glob.glob(self.pattern, recursive=self.recursive)]
        if self.abspaths:
            all_paths = [os.path.abspath(f) for f in all_paths]
        if not self.include_files:
            all_paths = [f for f in all_paths if not os.path.isfile(f)]
        if not self.include_directories:
            all_paths = [f for f in all_paths if not os.path.isdir(f)]
        if not self.include_symlinks:
            all_paths = [f for f in all_paths if not os.path.islink(f)]
        self.found_paths = sorted(all_paths)


class MovePath(Node):
    name: str = "Move Path"
    description: str = "Move/rename a path on the local file system. If the destination is an existing directory, then the target is moved inside that directory. If the destination already exists but is not a directory, it may be overwritten."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/shutil.html#shutil.move"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    src = InputSocket(datatype=String, name="Path", description="The path to rename.")
    dst = InputSocket(datatype=String, name="Destination", description="The destination to move to.")

    output_path = OutputSocket(datatype=String, name="New Path", description="The path to the moved file or directory (absolute).")

    def run(self):
        self.debug(f"Moving {self.src} to {self.dst}")
        self.output_path = os.path.abspath(shutil.move(self.src, self.dst))


class CopyPath(Node):
    name: str = "Copy Path"
    description: str = "Copy a path on the local file system to another. If the destination specifies a directory, the path will be copied into it using the base filename. If the target is a file and the destination also specifies a file that already exists, it will be replaced."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/shutil.html#shutil.copy", "https://docs.python.org/3/library/shutil.html#shutil.copytree"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    src = InputSocket(datatype=String, name="Path", description="The path to copy.")
    dst = InputSocket(datatype=String, name="Destination", description="The destination to copy to.")

    output_path = OutputSocket(datatype=String, name="New Path", description="The path to the copied file or directory (absolute).")

    def run(self):
        self.debug(f"Copying {self.src} to {self.dst}")
        if os.path.isdir(self.src):
            if os.path.isdir(self.dst):
                # shutil.copytree doesn't follow the behavior of copying a directory into another directory; implement it manually
                new_dst_path = os.path.join(self.dst, os.path.basename(self.src))
                self.output_path = os.path.abspath(shutil.copytree(self.src, new_dst_path))
            else:
                self.output_path = os.path.abspath(shutil.copytree(self.src, self.dst))
        else:
            self.output_path = os.path.abspath(shutil.copy(self.src, self.dst))


class DeletePath(Node):
    name: str = "Delete Path"
    description: str = "Delete a path on the local file system."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/os.html#os.remove", "https://docs.python.org/3/library/os.html#os.rmdir", "https://docs.python.org/3/library/shutil.html#shutil.rmtree"]
    categories: typing.List[str] = ["Files"]
    color: str = constants.COLOR_FILES

    target = InputSocket(datatype=String, name="Path", description="The path to delete.")
    recursive = InputSocket(
        datatype=Boolean,
        name="Recursive",
        description="If True, directories will be removed recursively, even if they are not empty.",
        input_field=False,
    )

    def run(self):
        self.debug(f"Deleting {self.target}")
        if os.path.isdir(self.target):
            if self.recursive:
                shutil.rmtree(self.target)
            else:
                os.rmdir(self.target)
        else:
            os.remove(self.target)
