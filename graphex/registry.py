import ast
import importlib
import inspect
import os
import shutil
import tempfile
import typing

import typeguard

from graphex.datatype import DataType
from graphex.graph import Graph, GraphValidationCache
from graphex.graphfile import GraphFile
from graphex.node import Node
from graphex.util import parse_yml
from graphex.compositeGraphInput import CompositeGraphInput
from graphex.git_resolution import check_file_for_merge_conflict


class GraphRegistry:
    """
    Registry of all nodes and datatypes available to a graph.

    :param root: Directory to treat at the root of the graph file system. This is used to resolve relative paths.
    :param cache_files: Whether to create a temporary directory for graphs at runtime or to use the original gx files.
    """

    def __init__(
        self, root: str, cache_files: bool = True, verbose_errors: bool = False
    ):
        if not os.path.isdir(root):
            raise NotADirectoryError(f"{root} is not a valid directory.")

        self.root = os.path.abspath(root)
        """Directory to treat at the root of the graph file system (absolute path)."""

        self.nodes: typing.Dict[str, typing.Type[Node]] = {}
        """Registered nodes available in this registry (Name -> Class)"""

        self.datatypes: typing.Dict[str, DataType] = {}
        """Registered data types available in this registry (Name -> Class)"""

        self.plugins: typing.List[str] = []
        """List of loaded plugins."""

        self.graphex_runtime_files_dir = self.root
        """Where the graphex files for this execution are stored."""

        self.verbose_errors = verbose_errors
        """Whether to increase the verbosity of error messages or not"""

        self.plugin_docs_index_paths: typing.Dict[str, str] = {}
        """Absolute path to each index.html provided by plugins"""

        self.composite_inputs: typing.Dict[str, typing.Type[CompositeGraphInput]] = {}

        if cache_files:
            self.tempdir = tempfile.TemporaryDirectory(prefix="graphex-runtime-")
            """Temporary directory object for the runtime graph files. On destruction of this object (i.e. garbage collection of the runtime), the temporary directory will be deleted."""

            self.graphex_runtime_files_dir = self.tempdir.name
            GraphRegistry.transfer_graph_files(
                self.root, self.graphex_runtime_files_dir
            )

    @staticmethod
    def transfer_graph_files(start_path: str, new_path: str):
        # for each filename in the starting directory (e.g. /root/)
        for filename in os.listdir(start_path):
            # join the filename with the current path (e.g. /root/a.gx or /root/dir_b/)
            filepath = os.path.join(start_path, filename)
            # join the filename with the new path
            new_dir = os.path.join(new_path, filename)
            # if the path is a directory (e.g. /root/dir_b/)
            if os.path.isdir(filepath):
                # don't include the new directory we are building (infinite loop)
                if filepath == new_path:
                    continue
                if filepath.startswith(".graphex"):
                    continue
                # don't include obvious directories missing .gx files
                if (
                    filepath == ".git"
                    or filepath == ".DS_Store"
                    or "__pycache__" in filepath
                ):
                    continue
                # create a new directory that matches the path of this one (e.g. /root/dir_b/ -> /root/.graphex_runtime/dir_b)
                os.mkdir(new_dir)
                # repeat this process for the new directories
                GraphRegistry.transfer_graph_files(filepath, new_dir)
            # else the path is a file ... (if it has the graphex extension (e.g. /root/a.gx))
            elif filepath.endswith(".gx"):
                # copy the file into the new_path (e.g. /root/.graphex_runtime/a.gx)
                shutil.copyfile(filepath, new_dir)

    @staticmethod
    def find_venv_name():
        """
        Returns the current venv in use by GraphEx.
        The venv will be an empty string if a venv is not currently in use.
        """
        import sys

        if sys.prefix == sys.base_prefix:
            return ""
        return os.path.basename(sys.prefix)

    def load_graph_file(
        self,
        path: str,
        validation_cache: typing.Optional[GraphValidationCache] = None,
        is_cli: bool = False,
    ) -> Graph:
        """
        Load a serialized graph from a file.

        :param filename: The path to the file (relative to the root directory).
        :param validation_cache: The validation cache to use during validation (if this graph should use an external validation cache).

        :return: The loaded graph.
        """
        if is_cli:
            path = self.resolve_cli_path(path)
        else:
            path = self.resolve_path(path)
        name = path[len(self.root) :] if path.startswith(self.root) else path
        if self.graphex_runtime_files_dir != self.root:
            if path.startswith(self.root):
                path = path.replace(self.root, self.graphex_runtime_files_dir)
        if not os.path.isfile(path):
            # try to figure out what graph file was trying to be loaded by the user
            temp_folder_index = path.find("graphex-runtime")
            path_estimate = path
            if temp_folder_index > -1:
                path_estimate = path[path.find("/", temp_folder_index + 1) + 1 :]

            # check if this is a simple joining error
            if os.path.basename(self.root) == path_estimate.split("/")[0]:
                # join on the duplicate folder
                path = os.path.join(os.path.dirname(self.root), path_estimate)

            if not os.path.isfile(path):
                raise ValueError(
                    f"{os.path.basename(path)} is not a file accessible by Graphex. Please make sure you are in the correct directory and that the root path ({self.root}) can reach the file path ({path_estimate})."
                )
        # print(f'Loading graph from file: {path}')
        with open(path, mode="r") as f:
            error = None
            try:
                g = self.load_graph(
                    f.read(), name=name, validation_cache=validation_cache
                )
                g.filepath = name if not name.startswith('/') else name.replace('/', '', 1)
                return g
            except Exception as e:
                error = e
            raise ValueError(f"Failed to load Graph from {path} ({str(error)})")

    def load_graph(
        self,
        serialized: str,
        name: typing.Optional[str] = None,
        validation_cache: typing.Optional[GraphValidationCache] = None,
    ) -> Graph:
        """
        Load a serialized graph from a string.

        :param serialized: The serialized graph contents.
        :param name: The name to give to this graph.
        :param validation_cache: The validation cache to use during validation (if this graph should use an external validation cache).

        :return: The loaded graph.
        """
        try:
            graph_file: GraphFile = parse_yml(serialized)
        except Exception as ye:
            if check_file_for_merge_conflict(serialized, parse_yml=False):
                raise RuntimeError(
                    f"The provided graph with name: {name} ... Contains one or more merge conflicts. Please open this file in the UI to work towards resolving the error."
                )
            else:
                raise ye
        if graph_file is None:
            raise RuntimeError(f"Not a valid YAML file")
        return Graph(graph_file, self, name=name, validation_cache=validation_cache)

    def resolve_path(self, path: str) -> str:
        """
        Resolve a relative path (from the server root) to an absolute path within the root folder of this registry. This does not check if the path actually exists.

        If the path does not exist within the root directory, this raises an error.

        :param path: The path.

        :returns: The absolute path within the root directory.
        :throws RuntimeError: If the path is not contained within the root directory.
        """
        base = self.root.rstrip(os.sep) + os.sep
        base = base.strip()
        abspath = os.path.abspath(
            path if os.path.isabs(path) else os.path.join(base, path)
        )
        if not abspath.startswith(base) and not (abspath + "/").startswith(base):
            raise RuntimeError(
                f"{abspath} is not contained within the root directory {base}"
            )
        return abspath

    def resolve_cli_path(self, path: str) -> str:
        """
        Resolve a relative path to an absolute path within the root folder of this registry. This does not check if the path actually exists.

        If the path does not exist within the root directory, this raises an error.

        :param path: The path.

        :returns: The absolute path within the root directory.
        :throws RuntimeError: If the path is not contained within the root directory.
        """
        # path is the file you want to run -> turns into path_abspath
        # root_base is the root directory
        root_base = self.root.rstrip(os.sep) + os.sep
        root_base = os.path.abspath(os.path.expanduser(root_base.strip()))
        path_abspath = (
            path if os.path.isabs(path) else os.path.abspath(os.path.expanduser(path))
        )
        if not path_abspath.startswith(root_base) and not (
            path_abspath + "/"
        ).startswith(root_base):
            path_abspath = os.path.abspath(
                os.path.expanduser(os.path.join(root_base, path))
            )
            if not path_abspath.startswith(root_base) and not (
                path_abspath + "/"
            ).startswith(root_base):
                raise RuntimeError(
                    f"{path_abspath} is not contained within the root directory {root_base}"
                )
        return path_abspath

    def find_node(self, name: str) -> typing.Optional[typing.Type[Node]]:
        """Find a node and return ``None`` if it does not exist."""
        return self.nodes.get(name, None)

    def find_graph_input(
        self, name: str
    ) -> typing.Optional[typing.Type[CompositeGraphInput]]:
        """Find a composite Graph input and return ``None`` if it does not exist."""
        return self.composite_inputs.get(name, None)

    def get_node(self, name: str) -> typing.Type[Node]:
        """Get a node and raise an exception if it does not exist."""
        if name not in self.nodes:
            raise ValueError(f"Node with the name '{name}' does not exist.")
        return self.nodes[name]

    def find_datatype(self, name: str) -> typing.Optional[DataType]:
        """Find a datatype and return ``None`` if it does not exist."""
        return self.datatypes.get(name, None)

    def get_datatype(self, name: str) -> DataType:
        """Get a datatype and raise an exception if it does not exist."""
        if name not in self.datatypes:
            raise ValueError(f"A data type with the name '{name}' does not exist.")
        return self.datatypes[name]

    def find_datatypes_for_type(
        self, dtype: typing.Type, strict: bool = True
    ) -> typing.List[DataType]:
        """
        Find all datatypes that accept ``dtype`` as a valid instance (i.e. find all datatypes that have ``dtype`` as an underlying type; Union datatypes are handled as well).

        For example, the call ``find_datatypes_for_type(int)`` should return (at the very least): ``[Number]``

        :param dtype: The Python datatype to search for.
        :param strict: Whether to use strict (exact equality) checking. If ``False``, subtyping will also be considered.

        :returns: A list of datatypes that have ``dtype`` as an underlying type.
        """
        valid_datatypes: typing.List[DataType] = []
        for datatype in self.datatypes.values():
            true_type = datatype.get_type()

            # Check type with Typeguard first to handle complex types
            if not strict:
                try:
                    typeguard.check_type(dtype, typing.Type[datatype.get_type()])
                    valid_datatypes.append(datatype)
                    continue
                except Exception:
                    pass

            # The above typeguard checking does not work with all types (e.g. TypedDict),
            # so if it fails we'll check for equality
            if getattr(true_type, "__origin__", None) == typing.Union:
                # Union type
                if not any(
                    [dtype == union_type for union_type in typing.get_args(true_type)]
                ):
                    # Not in union
                    continue
            elif dtype != true_type:
                # Data type does not match
                continue

            valid_datatypes.append(datatype)

        return valid_datatypes

    def find_composite_input_from_datatype(
        self, datatype: DataType
    ) -> typing.Type[typing.Optional[CompositeGraphInput]]:
        return self.composite_inputs.get(datatype.name, None)  # type: ignore

    def register_node(self, node: typing.Type[Node], plugin_name: str = "GraphEx"):
        """Register a new node in this registry."""
        assert (
            issubclass(node, Node) and node != Node
        ), f"'node' must be a subclass of Node"
        if node._is_template:
            raise ValueError(f"Cannot register template node '{node.name}'.")
        if node.name in self.nodes:
            raise ValueError(
                f"A node is already registered under the name '{node.name}'"
            )
        # assign plugin_name
        node.original_plugin = plugin_name
        self.nodes[node.name] = node

    def register_composite_input(self, input: typing.Type[CompositeGraphInput]):
        assert (
            issubclass(input, CompositeGraphInput) and input != CompositeGraphInput
        ), f"'input' must be a subclass of CompositeGraphInput"
        if input.datatype.name in [c.datatype.name for c in self.composite_inputs.values()]:  # type: ignore
            raise ValueError(f"A composite input is already registered with datatype {input.datatype.name}")  # type: ignore
        self.composite_inputs[input.datatype.name] = input  # type: ignore

    def register_datatype(self, datatype: DataType):
        """Register a new data type in this registry."""
        assert isinstance(
            datatype, DataType
        ), f"'datatype' must be a instance of DataType"
        if datatype.name in self.datatypes:
            raise ValueError(
                f"A data type is already registered under the name '{datatype.name}'"
            )
        self.datatypes[datatype.name] = datatype

    def register_package(self, package: str):
        """
        Recursively walk the given package and register all nodes and data types found.

        :param package: The name of the package.
        """
        module = importlib.import_module(package)
        assert (
            len(module.__path__) == 1
        ), f"Unable to handle module path: {module.__path__}"

        # Search for all sub-packages available in this module
        path = module.__path__[0]
        remaining_files: typing.List[str] = [
            os.path.join(path, f) for f in os.listdir(path)
        ]
        packages_to_process: typing.List[typing.Tuple[str, str]] = []
        while remaining_files:
            file = remaining_files.pop(0)

            if os.path.isdir(file):
                if file.endswith("__pycache__"):
                    continue
                remaining_files.extend(
                    [os.path.join(file, f) for f in os.listdir(file)]
                )
                continue

            if os.path.isfile(file) and file.endswith("index.html"):
                self.plugin_docs_index_paths[package] = file
            if (
                not (os.path.isfile(file) and file.endswith(".py"))
                or "setup.py" in file
            ):
                continue

            relative_path = file[len(path) :].lstrip(os.sep)
            file_package = package + "." + ".".join(relative_path[:-3].split(os.sep))
            packages_to_process.append((file_package, file))

        # Sort this packages so that we load the __init__.py files first
        packages_to_process.sort(
            key=lambda x: 0 if os.path.basename(x[1]).lower() == "__init__.py" else 1
        )

        # Begin loading
        for package_name, file in packages_to_process:
            file_module = importlib.import_module(package_name)

            # Detect duplicate class names as this may be a source of errors
            class_occurences = {}
            with open(file, "r") as f:
                source = f.read()
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_occurences[node.name] = (
                            class_occurences.get(node.name, 0) + 1
                        )

            duplicate_classes = [
                class_name
                for class_name, count in class_occurences.items()
                if count > 1
            ]
            if len(duplicate_classes):
                raise RuntimeError(
                    f"Multiple definitions of class '{duplicate_classes[0]}' in file {file}."
                )

            # Run the '__graphex_init__' function, if it exists
            for _, obj in inspect.getmembers(file_module, predicate=inspect.isfunction):
                if obj.__name__ == "__graphex_init__":
                    obj(self)

            # Load all nodes/datatypes
            for _, obj in inspect.getmembers(file_module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, Node)
                    and obj != Node
                    and obj not in self.nodes.values()
                    and not obj._is_template
                ):
                    self.register_node(obj, plugin_name=package_name)

                if (
                    inspect.isclass(obj)
                    and issubclass(obj, CompositeGraphInput)
                    and obj != CompositeGraphInput
                    and obj not in self.composite_inputs.values()
                ):
                    self.register_composite_input(obj)

                if isinstance(obj, DataType) and obj not in self.datatypes.values():
                    self.register_datatype(obj)

    def register_plugin(self, plugin: str):
        """
        Register a plugin (by name). The plugin must be installed on the system and loadable as a package.

        :param plugin: The name of the plugin.
        """
        self.register_package(plugin)
        self.plugins.append(plugin)

    def register_defaults(self):
        """Register all default nodes and data types."""
        from graphex import data, nodes

        self.register_package(nodes.__package__)  # type: ignore
        self.register_package(data.__package__)  # type: ignore

    def register_dynamics(self):
        """
        Register dynamically-generated nodes from loaded data types.
        """
        for datatype in self.datatypes.values():
            for dynamic_node in datatype.create_nodes():
                self.register_node(dynamic_node)

    def assert_graph_input_valid(self, graphInput: CompositeGraphInput):

        for sub_input in graphInput.subInputs():
            if (
                sub_input.datatype not in ["Boolean", "String", "Number"]
                or sub_input not in self.composite_inputs
            ):
                raise ValueError(
                    f"Composite GraphInput for '{graphInput.datatype.name}' has input with data '{sub_input.datatype}'. Inputs can only be primitive or must of a CompositeGraphInput object defined. "
                )

    def register_all(self, plugins: typing.List[str], log: bool = False):
        """
        Register all available nodes and data types (defaults, plugins, and dynamics).

        :param plugins: List of plugins to register.
        :param log: Whether to log/print information while loading.
        """
        num_nodes = len(self.nodes)
        num_datatypes = len(self.datatypes)

        # Register defaults
        self.register_defaults()
        if log:
            print(
                f"Loaded {len(self.nodes) - num_nodes} built-in nodes ({len(self.nodes)} total)."
            )
            print(
                f"Loaded {len(self.datatypes) - num_datatypes} built-in data types ({len(self.datatypes)} total)."
            )
        num_nodes = len(self.nodes)
        num_datatypes = len(self.datatypes)

        # Register plugins
        for plugin in plugins:
            try:
                self.register_plugin(plugin)
            except ModuleNotFoundError:
                raise RuntimeError(f'No plugin found with name "{plugin}"')

            if log:
                print(
                    f'Loaded {len(self.nodes) - num_nodes} nodes from plugin "{plugin}" ({len(self.nodes)} total).'
                )
                print(
                    f'Loaded {len(self.datatypes) - num_datatypes} data types from plugin "{plugin}" ({len(self.datatypes)} total).'
                )
            num_nodes = len(self.nodes)
            num_datatypes = len(self.datatypes)

        # Register dynamics
        self.register_dynamics()
        if log:
            print(
                f"Loaded {len(self.nodes) - num_nodes} dynamic nodes ({len(self.nodes)} total)."
            )
