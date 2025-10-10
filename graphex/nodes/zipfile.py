from graphex import String, Node, InputSocket, OptionalInputSocket, constants
import typing
import zipfile


class CompressFile(Node):
    name: str = "Compress (Zip) File"
    description: str = (
        "Adds a single file to a zip archive. If the archive does not exist, it will be created. Otherwise, the file will be added to the existing archive."
    )
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/io.html#io.BufferedIOBase.write"]
    categories: typing.List[str] = ["Files", "Archives"]
    color: str = constants.COLOR_FILES

    zip_path = InputSocket(datatype=String, name="Archive File Path", description="The path to the output archive file to create or append.")
    filepath_value = InputSocket(datatype=String, name="File Path to Add", description="The path to the file to archive/zip/compress (add to the zip file).")

    def run(self):
        self.log(f"Adding {self.filepath_value} to zip archive {self.zip_path}")
        with zipfile.ZipFile(self.zip_path, "a", zipfile.ZIP_DEFLATED) as zfile:
            zfile.write(self.filepath_value)


class UnzipArchive(Node):
    name: str = "Decompress (Unzip) Archive"
    description: str = "Decompress / Extract a zip file archive."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/zipfile.html"]
    categories: typing.List[str] = ["Files", "Archives"]
    color: str = constants.COLOR_FILES

    zip_path = InputSocket(datatype=String, name="Archive File Path", description="The path to the zip archive file to unzip.")
    filepath = InputSocket(datatype=String, name="Output Directory", description="The path to extract the zip contents to.")
    password = OptionalInputSocket(datatype=String, name="Password", description="Password to provide if the archive is encrypted.")

    def run(self):
        self.log(f"Extracting zip archive {self.zip_path} to {self.filepath}")
        password = str.encode(self.password) if self.password else None
        with zipfile.ZipFile(self.zip_path, "r") as zip_ref:
            zip_ref.extractall(self.filepath, pwd=password)
