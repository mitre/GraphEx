import base64
import gzip
import importlib.resources as pkg_resources
import json
import logging
import multiprocessing
import multiprocessing.process
import os
import shutil
import signal
import time
import typing
from datetime import datetime
from re import findall as re_findall
from urllib import parse

import flask
from cryptography.fernet import InvalidToken
from flask_socketio import SocketIO, emit
from git import Actor, GitCommandError, InvalidGitRepositoryError, Repo

from graphex.config import GraphConfig
from graphex.git_resolution import (
    git_branches_containing_hash,
    git_diff_gx,
    git_merge_log,
    identify_merge_conflict_causes,
    reconstruct_merge_conflicted_file,
)
from graphex.graph import Graph
from graphex.graphfile import FILE_EXTENSION, GraphFile, GraphInputValueMetadata
from graphex.inventory import GraphInventory
from graphex.plugin_doc_generator import generate_plugin_doc
from graphex.registry import GraphRegistry
from graphex.util import node_id_from_file_content, node_name_from_file_content
from graphex.vault import decryptSecret, handle_ssl_context


class MessageData(typing.TypedDict):
    msg: str
    type: typing.Literal[
        "debug", "info", "notice", "warning", "error", "critical", "control", "image"
    ]


class GraphStartMessage(typing.TypedDict):
    id: str
    """Unique ID for this execution."""

    name: str
    """The name of this execution. This is typically the graph name."""

    filepath: typing.Optional[str]
    """The path to the graph on disk for this execution, if available."""


class RunningGraph(typing.TypedDict):
    name: typing.Optional[str]
    """Name of the graph."""

    filepath: typing.Optional[str]
    """The path to the graph on disk for this execution, if available."""

    process: multiprocessing.process.BaseProcess
    """Underlying process associated with this running graph."""

    history: typing.List[MessageData]
    """Log history for this graph."""

    finished: bool
    """Whether this graph has finished executing (either successfully or not)"""


def _graph_process(
    message_queue: multiprocessing.Queue,
    root: str,
    plugins: typing.List[str],
    serialized_graph: str,
    graph_name: typing.Optional[str],
    input_values: typing.Dict[str, typing.Any],
    log_level: str,
    verbose_errors: bool,
    show_inputs: bool,
    hide_secret_names: typing.List[str],
    inventory_path: typing.Optional[str],
    graph_filepath: typing.Optional[str],
):
    """
    Process function for running a graph from the UI.
    """
    import sys

    from graphex import GraphexLogger, GraphRegistry, GraphRuntime, NodeRuntimeError

    def log_callback(msg: str, formatted_msg: str, level: str):
        if level == "DEBUG":
            message_queue.put(MessageData(msg=msg, type="debug"))
        elif level == "NOTICE":
            message_queue.put(MessageData(msg=msg, type="notice"))
        elif level == "WARNING":
            message_queue.put(MessageData(msg=msg, type="warning"))
        elif level == "ERROR":
            message_queue.put(MessageData(msg=msg, type="error"))
        elif level == "CRITICAL":
            message_queue.put(MessageData(msg=msg, type="critical"))
        elif level == "IMAGE":
            message_queue.put(MessageData(msg=msg, type="image"))
        else:
            message_queue.put(MessageData(msg=msg, type="info"))

    logger = GraphexLogger(level=log_level, azure_integration=False)
    logger.callback = log_callback
    try:
        registry = GraphRegistry(root=root)
        registry.register_all(plugins=plugins, log=False)
        if inventory_path:
            inv = GraphInventory(inventory_path, registry, print_loading_msg=False)
            inv.create_content_nodes(auto_register=True, print_registered_amount=False)
        graph = registry.load_graph(serialized_graph, name=graph_name)
        if graph_filepath:
            graph.filepath = graph_filepath

        runtime = GraphRuntime(
            graph,
            logger,
            input_values,
            azure_integration=False,
            verbose_errors=verbose_errors,
            print_graph_inputs=show_inputs,
            hide_secret_names=hide_secret_names,
            composite_inputs=list(input_values.keys()),
        )

        errors = runtime.run()
        for err in errors:
            logger.critical(str(err))

        sys.exit(1 if errors else 0)
    except Exception as e:
        logger.critical(str(e))
        # sys.exit(1) hangs here (probably because its a separate process), so I switched to the more forceful os._exit(1) (should only be used from thread-like situations)
        # raising error here will not work great either: it doesn't propagate properly back to the server process
        time.sleep(0.1)
        os._exit(1)


class GraphServer:
    """
    Server for the GraphEX web UI.

    :param registry: The registry to serve on this server.
    """

    def __init__(
        self,
        registry: GraphRegistry,
        config: typing.Optional[GraphConfig],
        ssl_certs_path: typing.Optional[str],
        vault_password: typing.Optional[str],
        inventory: typing.Optional[GraphInventory] = None,
        log_rollover_amount: int = 20
    ):
        assert isinstance(
            registry, GraphRegistry
        ), f"'registry' must be an instance of GraphRegistry"

        self.registry: GraphRegistry = registry
        """The registry for this server."""

        self.config: typing.Optional[GraphConfig] = config
        """Config file for this server."""

        self.ssl_context: tuple[str, str] = handle_ssl_context(ssl_certs_path)
        """The variation of SSL certificates to use in the server"""

        self.vault_password = vault_password
        """The password to decrypt secrets from the vault"""

        self.decryptedSecrets: typing.Dict[str, str] = self.decryptSecrets()
        """Plaintext values of the secrets from the config file to supply to the graph at runtime. These unencrypted values should NEVER leave the backend server."""

        self.secret_key_names: typing.List[str] = []
        """The names of the secrets held in the configuration file"""

        self.inventory: typing.Optional[GraphInventory] = inventory
        """An optional inventory to populate the sidebar in the UI"""

        # populate the internal reference to the secret names
        if self.config:
            self.secret_key_names = list(self.config.get_all_encrypted_secrets().keys())

        # Set up server
        website_path = None
        try:
            with pkg_resources.path("graphex", "website") as p:
                website_path = str(p)
        except Exception as e:
            print(e)

        app = flask.Flask(__name__, static_url_path="", static_folder=website_path)
        self.app = app
        """The Flask server."""

        logging.getLogger("werkzeug").setLevel(logging.WARNING)

        socketio = SocketIO(
            app,
            path="/api/socket.io",
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
        )
        self.socketio = socketio
        """The framework for Flask socket support"""

        self.socketio_connected_sids: typing.Set[str] = set()
        """List of connected socket SIDs"""

        self.running_graphs: typing.Dict[str, RunningGraph] = {}
        """All running graphs on this server (ID mapped to RunningGraph)"""

        self.num_log_files = log_rollover_amount
        """How many of the last graph runs to save the logs for."""

        self.log_dir = os.path.abspath(os.path.join(".", "logs"))
        """The path to where graphex log files are stored"""

        # create the log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_count = self.getLogCount()
        """The current log file count"""

        generate_plugin_doc(
            os.path.dirname(__file__),
            "./website/docs/html/plugin_docs/",
            self.registry.plugin_docs_index_paths,
        )

        # # # git specific init
        # setup a reference to our git repo
        try:
            self.git_repo_obj = Repo(self.registry.root, search_parent_directories=True)
        except InvalidGitRepositoryError as ge:
            print(
                "\033[93m WARNING: No local git repositories could be found in or above the provided root directory:",
                self.registry.root,
                " ... All git features will be disabled in the UI! \033[0m",
            )
            self.git_repo_obj = None
        # # #

        # Set up routes
        ## GET
        app.route("/")(self.index)
        app.route("/docs/<path:path>")(self.docs)
        app.route("/api/title")(self.title)
        app.route("/api/file")(self.file)
        app.route("/api/rawfile")(self.rawfile)
        app.route("/api/baseSixtyFourFile")(self.baseSixtyFourFile)
        app.route("/api/duplicateFile")(self.duplicateFile)
        app.route("/api/files")(self.files)
        app.route("/api/metadata")(self.metadata)
        app.route("/api/runningGraphs")(self.runningGraphs)
        app.route("/api/packageInfo")(self.packageInfo)
        app.route("/api/absoluteFilePath")(self.fileAbsolutePath)
        app.route("/api/log")(self.getLogContents)
        app.route("/api/logs")(self.listLogFiles)
        app.route("/api/search")(self.searchFiles)
        app.route("/api/git/branch")(self.gitBranch)
        app.route("/api/git/branches")(self.gitBranches)
        app.route("/api/git/remoteBranches")(self.gitRemoteBranches)
        app.route("/api/git/commitMessage")(self.gitCommitMsg)
        app.route("/api/git/status")(self.gitStatus)
        app.route("/api/git/mergeConflictBranches")(self.gitBranchesForMergeConflict)
        app.route("/api/git/formatGitFilepath")(self.formatGitFilepath)

        ## POST
        app.route("/api/updateNode", methods=["POST"])(self.updateNode)
        app.route("/api/file", methods=["POST"])(self.writeFile)
        app.route("/api/movePath", methods=["POST"])(self.movePath)
        app.route("/api/configGraphInputValues", methods=["POST"])(
            self.getConfigGraphInputValues
        )
        app.route("/api/directory", methods=["POST"])(self.createDirectory)
        app.route("/api/git/branch", methods=["POST"])(self.gitBranchChange)
        app.route("/api/git/push", methods=["POST"])(self.gitPush)
        app.route("/api/git/add", methods=["POST"])(self.gitAdd)
        app.route("/api/git/addAll", methods=["POST"])(self.gitAddAll)
        app.route("/api/git/unstage", methods=["POST"])(self.gitUnstage)
        app.route("/api/git/commit", methods=["POST"])(self.gitCommit)
        app.route("/api/git/pull", methods=["POST"])(self.gitPull)
        app.route("/api/git/fetch", methods=["POST"])(self.gitFetch)
        app.route("/api/git/diff", methods=["POST"])(self.gitDiff)
        app.route("/api/git/merge", methods=["POST"])(self.gitMerge)
        app.route("/api/git/cancelMerge", methods=["POST"])(self.cancelGitMerge)
        app.route("/api/git/mergeConflict", methods=["POST"])(self.gitMergeConflict)
        app.route("/api/git/resolveMergeConflict", methods=["POST"])(
            self.gitResolveMergeConflict
        )
        app.route("/api/search", methods=["POST"])(self.searchFiles)
        app.route("/api/nodeIdFromFile", methods=["POST"])(self.nodeIdFromFile)

        ## DELETE
        app.route("/api/file", methods=["DELETE"])(self.deleteFile)

        # Socket events
        socketio.on_event("connect", self.socketConnect)
        socketio.on_event("disconnect", self.socketDisconnect)  # type: ignore
        socketio.on_event("startGraph", self.socketStartGraph)
        socketio.on_event("stopGraph", self.socketStopGraph)
        socketio.on_event("killGraph", self.socketKillGraph)
        socketio.on_event("graphOutput", self.socketGraphOutput)
        socketio.on_event("beginHeartbeat", self.socketHeartbeat)

    def index(self):
        """
        Serves up the GraphEx UI
        """
        return flask.redirect("/index.html")

    def docs(self, path: str):
        """
        " "/docs/<path:path>" "
        this function is unique amongst the Flask server functions in that it serves up the HTML for the docs
        """
        return flask.send_from_directory("./website/docs/html/", path)

    def title(self) -> typing.Tuple[str, int]:
        """
        "/api/title" (method is GET)
        """
        title = (self.config.get_title() or "") if self.config else ""
        return title, 200

    def metadata(self):
        """
        "/api/metadata" (method is GET)
        """
        data = {
            "datatypes": [
                datatype.metadata() for datatype in self.registry.datatypes.values()
            ],
            "nodes": [
                node.metadata(None, None) for node in self.registry.nodes.values()
            ],
            "compositeInputs": [
                composite_input.metadata()
                for composite_input in self.registry.composite_inputs.values()
            ],
            "inventory": self.inventory.as_dict() if self.inventory else {},
        }

        content = gzip.compress(json.dumps(data).encode("utf8"), 5)
        response = flask.make_response(content)
        response.headers["Content-length"] = str(len(content))
        response.headers["Content-Encoding"] = "gzip"
        return response

    def updateNode(self):
        """
        "/api/updateNode" (method is POST)
        Update a node's metadata based on graph context. This is used by dynamic nodes to update their metadata as needed.
        """
        try:
            data = flask.request.get_json()

            # Load the data
            graph = Graph(data["graph"], registry=self.registry)
            node_id = data["id"]

            # Get the metadata
            instance_metadata = graph.get_node(node_id)
            node = self.registry.get_node(instance_metadata["name"])
            new_metadata = node.metadata(graph, instance_metadata)

            return new_metadata
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def packageInfo(self):
        """
        "/api/packageInfo" (method is GET)
        """
        from importlib.metadata import version

        info_dict = {}
        for plugin in self.registry.plugins:
            info_dict[plugin] = version(plugin)

        config = (
            f"Configuration file loaded from: {self.config.path}"
            if self.config
            else "Configuration file not provided"
        )
        venv = GraphRegistry.find_venv_name()
        if venv == "":
            venv = "No virtual environment is in use"
        else:
            venv = venv
        branch = ""
        repo = ""
        if self.git_repo_obj:
            branch = self.git_repo_obj.active_branch.name
            repo = self.git_repo_obj.remotes.origin.url
        if branch == "":
            branch = "Not currently serving a directory managed by git"
        else:
            branch = branch

        if repo == "":
            repo = "Not currently serving a directory managed by git"
        else:
            repo = repo

        return {
            "graphex": str(version("mitre-graphex")),
            "plugins": info_dict,
            "config": config,
            "venv": venv,
            "branch": branch,
            "repo": repo,
        }

    def files(self):
        """
        "/api/files" (method is GET)
        """
        RESTRICTED_DIRS = ["__pycache__", "node_modules", ".git"]
        RESTRICTED_FILES = [".DS_Store"]

        def gather_files(abspath: str) -> typing.List[dict]:
            files = []
            for filename in os.listdir(abspath):
                file_abspath = os.path.join(abspath, filename)
                is_dir = os.path.isdir(file_abspath)

                if filename in RESTRICTED_DIRS and is_dir:
                    continue

                if filename in RESTRICTED_FILES and not is_dir:
                    continue

                files.append(
                    {
                        "name": filename,
                        "isDir": is_dir,
                        "children": gather_files(file_abspath) if is_dir else [],
                    }
                )

            return files

        files = gather_files(self.registry.root)
        content = gzip.compress(json.dumps(files).encode("utf8"), 5)
        response = flask.make_response(content)
        response.headers["Content-length"] = str(len(content))
        response.headers["Content-Encoding"] = "gzip"
        return response

    def file(self):
        """
        "/api/file" (method is GET)
        Expects the query parameter 'path': e.g. /api/file?path=./filepath.gx
        Returns: (file_data, 200) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # join with root folder
            f_abspath: str = self.registry.resolve_path(filepath)

            # check that the file exists and is a file
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            if not os.path.isfile(f_abspath):
                return GraphServer.not_a_file(f_abspath)

            # read in the file and return its contents
            with open(f_abspath, "rb") as file:
                data = file.read()

            content = gzip.compress(data, 5)
            response = flask.make_response(content)
            response.headers["Content-length"] = str(len(content))
            response.headers["Content-Encoding"] = "gzip"
            return response
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def baseSixtyFourFile(self):
        """
        "/api/baseSixtyFourFile (method is GET)
        Returns the contents of a file after base64 encoding them
        Expects the query parameter 'path': e.g. /api/baseSixtyFourFile?path=./filepath.gx
        Returns: (file_data, 200) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # join with root folder
            f_abspath: str = self.registry.resolve_path(filepath)

            # check that the file exists and is a file
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            if not os.path.isfile(f_abspath):
                return GraphServer.not_a_file(f_abspath)

            # read in the file, base64 encode it, and return its contents
            with open(f_abspath, "rb") as file:
                encoded_string = base64.b64encode(file.read())

            content = gzip.compress(encoded_string, 5)
            response = flask.make_response(content)
            response.headers["Content-length"] = str(len(content))
            response.headers["Content-Encoding"] = "gzip"
            return response
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def rawfile(self):
        """
        "/api/rawfile" (method is GET)
        Expects the query parameter 'path': e.g. /api/rawfile?path=./filepath.gx
        Returns: (file_data, 200) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # join with root folder
            f_abspath: str = self.registry.resolve_path(filepath)

            # check that the file exists and is a file
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            if not os.path.isfile(f_abspath):
                return GraphServer.not_a_file(f_abspath)

            return flask.send_file(f_abspath)
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def getLogContents(self):
        """
        "/api/log" (method is GET)
        Expects the query parameter 'path': e.g. /api/file?path=./logs/logfilename.log
        Returns: (file_data, 200) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # get absolute path (could be outside of root folder)
            f_abspath: str = os.path.abspath(filepath)

            # check that the file exists and is a file
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            if not os.path.isfile(f_abspath):
                return GraphServer.not_a_file(f_abspath)

            # read in the file and return its contents
            with open(f_abspath, "rb") as file:
                data = file.read()

            content = gzip.compress(data, 5)
            response = flask.make_response(content)
            response.headers["Content-length"] = str(len(content))
            response.headers["Content-Encoding"] = "gzip"
            return response
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def writeFile(self) -> typing.Tuple[str, int]:
        """
        "/api/file", methods=["POST"]
        Expects the query parameter 'path': e.g. /api/file?path=./filepath.gx and the contents as the body.
        An error will be returned if the file already exists and no write will occur, unless the query parameter `overwrite=true` is specified (in which
        case, the file will be overwritten).

        Returns: (created_file_absolute_path, 201) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            overwrite_param = flask.request.args.get("overwrite", type=str)
            overwrite = (
                False
                if overwrite_param is None or overwrite_param.lower() != "true"
                else True
            )

            f_abspath: str = self.registry.resolve_path(filepath)
            if os.path.basename(f_abspath).strip().lower() == FILE_EXTENSION:
                return f"Empty file name: {f_abspath}", 400

            if os.path.exists(f_abspath) and not os.path.isfile(f_abspath):
                return GraphServer.not_a_file(f_abspath)

            if os.path.exists(f_abspath) and not overwrite:
                return GraphServer.file_exists(f_abspath)

            with open(f_abspath, "wb") as file:
                file.write(flask.request.data)

            return f_abspath, 201
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def movePath(self) -> typing.Union[typing.Tuple[str, int], typing.Tuple[dict, int]]:
        """
        "/api/movePath", methods=["POST"]
        Expects the query parameters 'path': e.g. /api/file?path=./filepath.gx
        Expects a JSON body with the key 'newPath'
        Moves a file or directory on the filesystem.
        Returns: (new_absolute_path_to_file, 200) on success
        """
        try:
            # Make sure the body is JSON and check it
            if flask.request.headers.get("Content-Type") != "application/json":
                GraphServer.no_json_header()

            json_body = flask.request.json
            if json_body is None:
                return GraphServer.no_json_body()

            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            if "newPath" not in json_body:
                return GraphServer.missing_json_param("newPath")

            # Join with root folder
            from_abspath: str = self.registry.resolve_path(filepath)
            to_abspath: str = self.registry.resolve_path(json_body["newPath"])

            # Check that the path to move exists
            if not os.path.exists(from_abspath):
                return GraphServer.file_does_not_exist(from_abspath)

            # Ensure that the target path does not already exist
            if os.path.exists(to_abspath):
                return GraphServer.file_exists(to_abspath)

            # Perform the Move
            shutil.move(from_abspath, to_abspath)

            return to_abspath, 200

        except Exception as e:
            return GraphServer.internal_server_error(e)

    def deleteFile(self) -> typing.Tuple[str, int]:
        """
        "/api/file", methods=["DELETE"]
        Expects the query parameter 'path': e.g. /api/file?path=./filepath.gx
        Deletes a file or directory from disk. Directories will be deleted recursively.
        Requires the file to be located under the root directory.
        Returns: (deleted_absolute_path, 200) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # join with root folder
            f_abspath: str = self.registry.resolve_path(filepath)

            # check that the file exists and is a file
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            # Delete the file or directory
            if os.path.isfile(f_abspath):
                os.remove(f_abspath)
            elif os.path.isdir(f_abspath):
                shutil.rmtree(f_abspath)
            return f_abspath, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def duplicateFile(
        self,
    ) -> typing.Union[typing.Tuple[str, int], typing.Tuple[dict, int]]:
        """
        "/api/duplicateFile" (method is GET)
        Expects the query parameter 'path': e.g. /api/duplicateFile?path=./filepath.gx
        Creates a copy of the file on the filesystem.
        Follows the template: 'originalFilename-#.originalFileExt'. Where # designates the first available number (>=1).
        Returns: (relative_path_to_duplicated_file, 200) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # join with root
            f_abspath: str = self.registry.resolve_path(filepath)

            # check that the file exists and is a file
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)
            if not os.path.isfile(f_abspath):
                return GraphServer.not_a_file(f_abspath)

            # format the new path
            path_parts: typing.Tuple[str, str] = os.path.split(f_abspath)
            base_path: str = path_parts[0]
            original_file: str = path_parts[1]
            extension_index: int = original_file.rfind(".")
            file_number: int = 1

            def generate_new_filename() -> str:
                return (
                    original_file[:extension_index]
                    + "-"
                    + str(file_number)
                    + original_file[extension_index:]
                )

            new_path: str = os.path.join(base_path, generate_new_filename())
            # check if the path already exists and continue to generate a new filename for as long as one does exist
            while os.path.exists(new_path):
                file_number += 1
                new_path = os.path.join(base_path, generate_new_filename())

            # duplicate the file
            shutil.copy(f_abspath, new_path)

            # Return the relative path to the new file
            return new_path[len(self.registry.root) :].strip("/"), 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def createDirectory(self) -> typing.Tuple[str, int]:
        """
        "/api/directory", methods=["POST"]
        Expects the query parameter 'path': e.g. /api/file?path=./folderPath.
        Creates a directory/folder on disk by the given relative path.
        Returns: (created_directory_absolute_path, 201) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            d_abspath: str = self.registry.resolve_path(filepath)

            # error if this path exists already
            if os.path.exists(d_abspath):
                return GraphServer.file_exists(d_abspath)

            os.makedirs(d_abspath)

            return d_abspath, 201
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def listLogFiles(self):
        """
        "/api/logs" (method is GET)
        Returns: (file_list_json, 200) on success
        """
        try:
            d_abspath = self.log_dir
            # list the files and the paths and return them
            filename_path_dict = {}
            for fn in os.listdir(d_abspath):
                if fn.endswith(".log"):
                    filename_path_dict[fn] = os.path.join(d_abspath, fn)

            data = {"filename_filepath": filename_path_dict}
            content = gzip.compress(json.dumps(data).encode("utf8"), 5)
            response = flask.make_response(content)
            response.headers["Content-length"] = str(len(content))
            response.headers["Content-Encoding"] = "gzip"
            return response
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def fileAbsolutePath(self) -> typing.Tuple[str, int]:
        """
        "/api/fileAbsolutePath" (method is GET)
        Expects the query parameter 'path': e.g. /api/file?path=./filepath
        Returns the absolute path to the provided relative file path
        Returns: (created_file_absolute_path, 201) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # if this is a file opened from source_directory
            f_abspath: str = self.registry.resolve_path(filepath)
            return f_abspath, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def runningGraphs(self):
        """
        "/api/runningGraphs" (method is GET)
        Get information about running graphs.
        Returns: ([ { id: <context ID>, name: <context name>, filepath: <context filepath or null> }, ... ], 200) on success
        """
        try:
            data = []
            for key, dv in self.running_graphs.items():
                # push the ID of the graph (key) and the name of the graph
                data.append({"id": key, "name": dv["name"], "filepath": dv["filepath"]})
            return data, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def getConfigGraphInputValues(self):
        """
        "/api/configGraphInputValues" (method is POST)
        Get Graph Input values from the config file.

        The JSON body should contain:
        - names: The names of the graph inputs to get.
        - path: Optional file path to use for querying the config
        - includeWildcard: Optional boolean triggering the response to include all values from '*' in the config file

        :returns: ({ [name: string]: any }, 200) on success
        """
        body: typing.Optional[typing.Dict[str, typing.Any]] = flask.request.json
        if not body:
            return "Body not valid JSON", 400

        names: typing.Optional[typing.List[str]] = body.get("names", None)
        if names is None:
            return f"Key 'names' missing from body", 400
        path: typing.Optional[str] = body.get("path", None)
        include_wildcard: typing.Optional[bool] = body.get("includeWildcard", False)

        if self.config is None:
            # Config not available
            return {}, 200

        try:
            scope: typing.Optional[str] = None
            if path:
                scope = self.config.get_scope(root=self.registry.root, path=path)
            graph_input_values = self.config.get_graph_inputs(
                names=names, scope=scope, include_wildcard=include_wildcard
            )
            secret_names = self.secret_key_names if self.secret_key_names else []
            payload = {"inputs": graph_input_values, "secrets": secret_names}

            content = gzip.compress(json.dumps(payload).encode("utf8"), 5)
            response = flask.make_response(content)
            response.headers["Content-length"] = str(len(content))
            response.headers["Content-Encoding"] = "gzip"
            return response
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def start(self, port: int = 80):
        """
        Start the server.

        :param port: The port of the webserver.
        """
        print(f"GraphEx server starting on all network interfaces at port: {port}")
        self.socketio.run(app=self.app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True, ssl_context=self.ssl_context, debug=False)  # type: ignore

    #####
    # Static methods that return (error message, int status code) for various situations
    @staticmethod
    def no_json_header() -> typing.Tuple[str, int]:
        return "Provided body payload must have Content-Type of 'application/json'", 400

    @staticmethod
    def no_json_body() -> typing.Tuple[str, int]:
        return "You must provide the file data to save as a JSON body", 400

    @staticmethod
    def missing_json_param(param: str) -> typing.Tuple[str, int]:
        return f"You must provide this param in the JSON body: {param}", 400

    @staticmethod
    def file_does_not_exist(abspath: str) -> typing.Tuple[str, int]:
        return f"Path doesn't exist on server filesystem: {abspath}", 404

    @staticmethod
    def file_exists(abspath: str) -> typing.Tuple[str, int]:
        return f"Path already exists on server filesystem: {abspath}", 409

    @staticmethod
    def not_a_file(abspath: str) -> typing.Tuple[str, int]:
        return f"Path is not a file: {abspath}", 400

    @staticmethod
    def not_a_dir(abspath: str) -> typing.Tuple[str, int]:
        return f"Path is not a directory: {abspath}", 400

    @staticmethod
    def git_not_found() -> typing.Tuple[str, int]:
        return f"A git repo was not found when the server was stood up.", 400

    @staticmethod
    def internal_server_error(error: Exception) -> typing.Tuple[str, int]:
        print(error)
        return str(error), 500

    #
    #####
    def socketConnect(self, sid: str):
        """
        Invoked automatically when a client connects to the flask socket.
        """
        if hasattr(flask.request, "sid"):
            sid = getattr(flask.request, "sid")
            if sid:
                self.socketio_connected_sids.add(sid)

    def socketDisconnect(self):
        """
        Invoked automatically when a client disconnects from the flask socket.
        """
        if hasattr(flask.request, "sid"):
            sid = getattr(flask.request, "sid")
            if sid:
                self.socketio_connected_sids.remove(sid)

    def decrypt_composite_input(
        self,
        value_metadata: GraphInputValueMetadata,
    ):
        if "fromSecret" in value_metadata:
            value_metadata["value"] = self.decryptedSecrets[
                value_metadata["fromSecret"]
            ]
            value_metadata.pop("fromSecret")
        else:
            for child in value_metadata["childValues"].values():
                self.decrypt_composite_input(child)

    def socketStartGraph(self, data):
        """
        Invoked from socketio.emit(startGraph)
        Starts executing the graph with the provided JSON data.

        :param data:
            The JSON object emitted by the client. It should contain the following fields:
            - 'id': The ID of the execution context
            - 'name': The name of the graph
            - 'filepath': The path to the graph on disk for this execution, if available.
            - 'graph': The serialized graph to start executing
            - 'values': Input values for this graph's execution
            - 'debug': Whether to include debug logs when running this graph (i.e. verbose mode).
            - 'showInputs': Whether to show the graph inputs at the top of the terminal UI or not
        """
        context_id: str = ""
        try:
            context_id: str = data["id"]
            graph_name: str = data["name"]
            graph_filepath: typing.Optional[str] = data["filepath"]
            serialized_graph: GraphFile = data["graph"]

            input_values: typing.Dict[str, GraphInputValueMetadata] = data["values"]
            log_level = "DEBUG" if data["debug"] else "INFO"
            show_inputs = data["showInputs"]

            if context_id in self.running_graphs:
                raise RuntimeError(
                    f"An execution context already exists with ID {context_id}"
                )

            def decrypt_config_input(
                value_metadata: GraphInputValueMetadata,
            ):
                if "fromSecret" in value_metadata:
                    value_metadata["value"] = self.decryptedSecrets[
                        value_metadata["fromSecret"]
                    ]
                    value_metadata.pop("fromSecret")  # remove the value
                else:
                    for child in value_metadata["childValues"].values():
                        decrypt_config_input(child)

            for input in input_values.values():
                decrypt_config_input(input)

            # apply decrypted secret values to graph inputs
            for name, input in input_values.items():
                if len(input["childValues"]) == 0 and name in self.secret_key_names:

                    input["value"] = self.decryptedSecrets[name]
                    if "fromSecret" in input:
                        input.pop("fromSecret")

            # Run the graph runtime in a new process
            context = multiprocessing.get_context("spawn")
            queue: multiprocessing.Queue = context.Queue()
            graph_process_kwargs = {
                "message_queue": queue,
                "root": self.registry.root,
                "plugins": self.registry.plugins,
                "serialized_graph": serialized_graph,
                "graph_name": graph_name,
                "input_values": input_values,
                "log_level": log_level,
                "verbose_errors": self.registry.verbose_errors,
                "show_inputs": show_inputs,
                "hide_secret_names": self.secret_key_names,
                "inventory_path": self.inventory.dir_path if self.inventory else None,
                "graph_filepath": graph_filepath,
            }

            running_graph = RunningGraph(
                name=graph_name,
                filepath=graph_filepath,
                process=context.Process(
                    target=_graph_process, kwargs=graph_process_kwargs, daemon=True
                ),
                history=[],
                finished=False,
            )

            self.running_graphs[context_id] = running_graph
            process = running_graph["process"]

            # Broadcast to all clients that this graph is about to start
            # There is a 'listener socket' on each client responsible for monitoring for this message
            emit(
                "graphStart",
                GraphStartMessage(
                    id=context_id, name=graph_name, filepath=graph_filepath
                ),
                broadcast=True,
            )

            # Start executing the graph in the separate process
            process.start()

            # Give time for the client socket to init
            # In rare cases the server can start executing before the socket object has finished initializing
            # This is the simpliest way to sync the server and client without adding additional event chains
            # TODO: Remove the need for this sleep
            time.sleep(1)

            # Loop until the graph exits
            while process.exitcode is None or not queue.empty():
                # Check for output from the child process
                while not queue.empty():
                    running_graph["history"].append(queue.get())

                # Check if the process is still executing
                # if executing: this join will 'pass' and execute the next poll
                # if not executing: we will join the process and the loop should exit
                process.join(timeout=0.5)

        except Exception as e:
            # This block executes if something goes wrong during the setup and execution
            print(str(e))
            if context_id in self.running_graphs:
                self.running_graphs[context_id]["history"].append(
                    MessageData(
                        msg=f"[ERROR - PYTHON EXCEPTION (socketStartGraph)]: {str(e)}",
                        type="critical",
                    )
                )
            return

        # save the exitcode to a local variable for printing a little farther down
        # exit_code = process.exitcode

        # buffer to give the process time to exit safely
        time.sleep(0.1)

        # If something goes wrong during join, make sure we end the process
        # We inform the clients that we are attempting to cleanup the process

        # print(f"Cleaning up process for execution context: {context_id}")
        if process.is_alive():
            time.sleep(0.9)
            process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            time.sleep(0.1)
            process.join()
            time.sleep(1.9)
        if process.is_alive():
            process.kill()
            time.sleep(0.1)
            process.join()
            time.sleep(1.9)

        # release resources on this process
        process.close()
        running_graph["finished"] = True

        # print(f"Finished execution context: {context_id} (exit code {exit_code})")

        # save this run to the logs
        self.saveOutputToFile(graph_name, running_graph["history"])

        # Remove the reference to this ID from our dict
        # Python should eventually clean up the references that are no longer in use
        try:
            del self.running_graphs[context_id]
        except KeyError:
            pass

    def socketGraphOutput(self, data):
        """
        Invoked from socketio.emit(graphOutput)

        Get/track the graph output (historic and current)

        :param data:
            The JSON object emitted by the client. It should contain the following fields:
            - 'id': The ID of the context to kill
        """
        context_id = data["id"]
        try:
            if context_id not in self.running_graphs:
                raise RuntimeError(f"No execution context found with ID {context_id}")

            running_graph = self.running_graphs[context_id]

            sid = None
            if hasattr(flask.request, "sid"):
                sid = getattr(flask.request, "sid")

            # Output the history
            history_len = len(running_graph["history"])
            if history_len:
                emit(
                    "graphOutput", MessageData(msg="Start Log History:", type="control")
                )
                for i in range(history_len):
                    emit("graphOutput", running_graph["history"][i])
                emit("graphOutput", MessageData(msg="End Log History.", type="control"))

            # Track the live output
            message_index = history_len
            while True:
                if running_graph["finished"] and message_index == len(
                    running_graph["history"]
                ):
                    # End when the process is finished and there are no more messages
                    break

                if sid is not None and sid not in self.socketio_connected_sids:
                    # End when the client disconnects
                    break

                while message_index < len(running_graph["history"]):
                    emit("graphOutput", running_graph["history"][message_index])
                    message_index += 1
                time.sleep(0.5)

            # Done

        except Exception as e:
            print(str(e))

        finally:
            emit("graphComplete")

    def socketStopGraph(self, data):
        """
        Invoked from socketio.emit(stopGraph)
        Attempt to gracefully stop (SIGINT) the executing graph with the ID provided from the JSON data

        :param data:
            The JSON object emitted by the client. It should contain the following fields:
            - 'id': The ID of the context to kill
        """
        context_id = data["id"]
        try:
            if context_id not in self.running_graphs:
                raise RuntimeError(f"No execution context found with ID {context_id}")

            running_graph = self.running_graphs[context_id]
            process = running_graph["process"]

            if running_graph["finished"]:
                return

            # Try to gracefully kill first
            if process.is_alive() and process.pid:
                os.kill(process.pid, signal.SIGINT)
                running_graph["history"].append(
                    MessageData(msg=f"Sent interrupt signal...", type="control")
                )

        except Exception as e:
            # This block executes if something goes wrong while trying to kill the process
            print(str(e))
            if context_id in self.running_graphs:
                self.running_graphs[context_id]["history"].append(
                    MessageData(
                        msg=f"[ERROR - PYTHON EXCEPTION (socketStopGraph)]: {str(e)}",
                        type="critical",
                    )
                )
            return

    def socketKillGraph(self, data):
        """
        Invoked from socketio.emit(killGraph)
        Forcefully kill the executing graph with the ID provided from the JSON data

        :param data:
            The JSON object emitted by the client. It should contain the following fields:
            - 'id': The ID of the context to kill
        """
        context_id = data["id"]
        try:
            if context_id not in self.running_graphs:
                raise RuntimeError(f"No execution context found with ID {context_id}")

            running_graph = self.running_graphs[context_id]
            process = running_graph["process"]

            if running_graph["finished"]:
                return

            # Force kill the process if it is still alive
            process.kill()
            process.join()

            # Inform all monitoring clients that this graph has been killed prematurely
            running_graph["history"].append(
                MessageData(msg=f"Killed executing graph.", type="critical")
            )

        except Exception as e:
            # This block executes if something goes wrong while trying to kill the process
            print(str(e))
            if context_id in self.running_graphs:
                self.running_graphs[context_id]["history"].append(
                    MessageData(
                        msg=f"[ERROR - PYTHON EXCEPTION (socketKillGraph)]: {str(e)}",
                        type="critical",
                    )
                )
            return

    def socketHeartbeat(self, data):
        sleepTime = data
        while True:
            self.heartbeat_info()
            time.sleep(sleepTime)

    def getLogCount(self):
        return len([f for f in os.listdir(self.log_dir) if f.endswith(".log")])

    def saveOutputToFile(self, graphName: str, msgData: typing.List[MessageData]):
        file_ext = ".log"
        basename = os.path.basename(graphName)
        basename = basename[:-3] if basename.endswith(".gx") else basename
        filename: str = basename + "-" + str(time.time()) + file_ext
        with open(os.path.join(self.log_dir, filename), "w") as file:
            file.write(json.dumps(msgData))

        self.log_count = self.getLogCount()
        if self.log_count > self.num_log_files:
            files: typing.List[str] = []
            for r, ds, fs in os.walk(self.log_dir):
                for f in fs:
                    files.append(os.path.join(r, f))

            oldest = os.path.abspath(min(files, key=os.path.getctime))
            while not oldest.endswith(file_ext):
                if len(files) <= 0:
                    print(
                        f'ERROR: Unable to remove any log files. No log files end in: "{file_ext}" in the directory: "{self.log_dir}"'
                    )
                    return
                files.remove(oldest)
                oldest = os.path.abspath(min(files, key=os.path.getctime))
            os.remove(oldest)

    def gitBranch(self) -> typing.Tuple[str, int]:
        """
        "/api/git/branch" (method is GET)
        Gets the name of the current branch (if inside a git repo)
        Returns: (String with the graph name, 200) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()
            return self.git_repo_obj.active_branch.name, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitBranches(
        self,
    ) -> typing.Union[typing.Tuple[str, int], typing.Tuple[dict, int]]:
        """
        "/api/git/branches" (method is GET)
        Gets the names all local branches
        Returns: ({branch_names: ...}, 200) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()
            branch_names = [b.name for b in self.git_repo_obj.branches]
            return {"branch_names": branch_names}, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitRemoteBranches(
        self,
    ) -> typing.Union[typing.Tuple[str, int], typing.Tuple[dict, int]]:
        """
        "/api/git/remoteBranches" (method is GET)
        Gets the names all remote branches
        Returns: ({branch_names: ...}, 200) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            # List all remote branches
            remote_branches = self.git_repo_obj.remote().refs
            # Remove 'origin/' from the branch names
            branch_names = [
                b.name.split("/", 1)[1]
                for b in remote_branches
                if b.name.startswith("origin/")
            ]
            return {"branch_names": branch_names}, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitCommitMsg(self) -> typing.Tuple[str, int]:
        """
        "/api/git/commitMessage" (method is GET)
        Gets the message for the most recent commit of the current branch (if inside a git repo)
        Returns: (String with the commit message, 200) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()
            return self.git_repo_obj.active_branch.commit.message, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitBranchChange(self) -> typing.Tuple[str, int]:
        """
        "/api/git/branch", methods=["POST"]
        Expects the query parameter 'name': e.g. /api/git/branch?name=master
        Changes the current git branch to the provided one.
        If the branch doesn't exist, it will create a new branch
        Returns: (string for status of checkout, 200 OR 201) on success (201 if a new branch was created)
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            # extract the query arg 'name'
            branch_name = flask.request.args.get("name", type=str)
            if branch_name is None:
                return "'name' not provided", 400

            # see if this branch exists locally or not
            branch_names = [b.name for b in self.git_repo_obj.branches]
            if branch_name in branch_names:
                # branch already exists locally
                res = self.git_repo_obj.git.checkout(branch_name)
                return res, 200
            # else branch needs to be created
            res = self.git_repo_obj.git.checkout("-b", branch_name)
            if str(res).strip() == "":
                res = f"Created and checked out new local branch: {branch_name}"
            return res, 201
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitPush(self) -> typing.Tuple[str, int]:
        """
        "/api/git/push", methods=["POST"]
        Expects a JSON body with the username and password fields
        Pushs the current branch up to git
        Returns: (summary of assumed successful push, 201) on success
        """
        use_provided_password = True
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            data = flask.request.get_json()

            res = self.setup_git_username(data)
            if res[1] != 0:
                return res

            if "password" not in data or data["password"] == "":
                use_provided_password = False
            self.disable_git_password_prompt()

            if use_provided_password:
                GraphServer.remove_git_credential_file()
                GraphServer.write_git_credential_file(
                    self.build_password_strings(data["username"], data["password"])
                )

            remote = self.git_repo_obj.remote()

            try:
                push_info_obj_list = remote.push()
                push_summaries = [p.summary for p in push_info_obj_list]
                return str(push_summaries), 201
            except GitCommandError as ge:
                # Could be: stderr: 'fatal: The current branch test has no upstream branch.'
                push_response = self.git_repo_obj.git.push(
                    "--set-upstream", remote.name, self.git_repo_obj.active_branch.name
                )
                return push_response, 201
        except Exception as e:
            return GraphServer.internal_server_error(e)
        finally:
            # this is always executed before return
            self.remove_git_username()
            self.unset_git_password_prompt()
            if use_provided_password:
                GraphServer.remove_git_credential_file()

    def formatGitFilepath(self) -> typing.Tuple[str, int]:
        """
        "/api/git/formatGitFilepath", methods=["GET"]
        Expects the query parameter 'path': e.g. /api/git/formatGitFilepath?path=./somefile.gx
        Removes any root path values from the filepath
        Returns: (string response, 200) on success
        """
        try:
            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # Remove any root path values in the filepath
            path: str = self.formatFilepath(filepath)

            return path, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitAdd(self) -> typing.Tuple[str, int]:
        """
        "/api/git/add", methods=["POST"]
        Expects the query parameter 'path': e.g. /api/git/add?path=./somefile.gx
        Adds the provided path to the file to the git staging error
        Returns: (string response, 201) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # Remove any root path values in the filepath
            path: str = self.formatFilepath(filepath)

            # join with root folder
            f_abspath: str = self.registry.resolve_path(path)

            # check file exists
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            try:
                res = self.git_repo_obj.git.add(f_abspath)
            except GitCommandError as ge:
                return str(ge), 400

            if str(res).strip() == "":
                res = f"Added file to git staging area: {f_abspath}"

            return res, 201
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitAddAll(self) -> typing.Tuple[str, int]:
        """
        "/api/git/addAll", methods=["POST"]
        Adds all files in the git repo to the git staging area.
        Returns: (string response, 201) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            try:
                res = self.git_repo_obj.git.add(".")
            except GitCommandError as ge:
                return str(ge), 400

            if str(res).strip() == "":
                res = "Added all files to git staging area"

            return res, 201
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitUnstage(self) -> typing.Tuple[str, int]:
        """
        "/api/git/unstage", methods=["POST"]
        Expects the query parameter 'path': e.g. /api/git/unstage?path=./somefile.gx
        Removes the file from the git staging area
        Returns: (string response, 201) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            # extract the query arg 'path'
            filepath = flask.request.args.get("path", type=str)
            if filepath is None:
                return "'path' not provided", 400

            # Remove any root path values in the filepath
            path: str = self.formatFilepath(filepath)

            # join with root folder
            f_abspath: str = self.registry.resolve_path(path)

            # check file exists
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            try:
                res = self.git_repo_obj.git.reset("HEAD", f_abspath)
            except GitCommandError as ge:
                return str(ge), 400

            if str(res).strip() == "":
                res = f"Removed file from git staging area: {f_abspath}"

            return res, 201
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitCommit(self) -> typing.Tuple[str, int]:
        """
        "/api/git/commit", methods=["POST"]
        Expects JSON data with the following fields: 'msg', 'author_name', 'author_email'
        Commits all files in the staging area to the git history
        Returns: (string response for committed changes, 201) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            data = flask.request.get_json()

            if "msg" not in data or data["msg"] == "":
                return "'msg' not provided", 400
            if "author_name" not in data or data["author_name"] == "":
                return "'author_name' not provided", 400
            if "author_email" not in data or data["author_email"] == "":
                return "'author_email' not provided", 400

            try:
                author = Actor(data["author_name"], data["author_email"])
                committer = Actor(data["author_name"], data["author_email"])
                res = self.git_repo_obj.index.commit(
                    data["msg"], author=author, committer=committer
                )
            except GitCommandError as ge:
                return str(ge), 400

            return "Created commit with message: " + str(res.message), 201
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitPull(self) -> typing.Tuple[str, int]:
        """
        "/api/git/pull", method is POST
        Expects a JSON body with the username and password fields
        Pulls the latest changes for this branch from git
        Returns: (string response for pull, 200) on success
        """
        use_provided_password = True
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            data = flask.request.get_json()

            res = self.setup_git_username(data)
            if res[1] != 0:
                return res

            if "password" not in data or data["password"] == "":
                use_provided_password = False
            self.disable_git_password_prompt()

            if use_provided_password:
                GraphServer.remove_git_credential_file()
                GraphServer.write_git_credential_file(
                    self.build_password_strings(data["username"], data["password"])
                )

            remote = self.git_repo_obj.remote()

            try:
                res = self.git_repo_obj.git.pull(
                    remote.name, self.git_repo_obj.active_branch.name
                )
            except GitCommandError as ge:
                return str(ge), 400

            return res, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)
        finally:
            # this is always executed before return
            self.remove_git_username()
            self.unset_git_password_prompt()
            if use_provided_password:
                GraphServer.remove_git_credential_file()

    def gitDiff(self):
        """
        "/api/git/diff", method is POST
        Expects a JSON body with the 'other_branch_name' and 'path' fields (where 'path' is the path to the file being diff'd).
        The current branch will be used as the branch that is being diff'd against the provided 'other_branch_name'.
        The 'other_branch_name' must already exist on disk in order for the git module to read from it (e.g. a verbose fetch may be needed first)
        ( verbose fetch syntax: 'git fetch origin branch_name:branch_name' ) ( where 'origin' is the name of the remote ) ( see gitFetch(...) function)
        Performs a more sophisticated form of 'git diff' on the provided filepath between the two branches.
        For more information: read the comment for the function 'git_diff_gx'.
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        data = flask.request.get_json()

        if "other_branch_name" not in data or data["other_branch_name"] == "":
            return "'other_branch_name' not provided", 400
        if "path" not in data or data["path"] == "":
            return "'path' not provided", 400

        # returned regardless of success or not
        dict_of_changes = {}

        # the git module wants a relative path (absolute path will result in a git error)
        f_abspath: str = self.registry.resolve_path(data["path"])
        f_relpath: str = os.path.relpath(f_abspath)

        # Compute the changed nodes and graph inputs between the two branches
        try:
            dict_of_changes = git_diff_gx(
                git_repo=self.git_repo_obj,
                other_branch_name=data["other_branch_name"],
                filepath=f_relpath,
            )
        except GitCommandError as ge:
            return GraphServer.internal_server_error(ge)
        except Exception as e:
            return GraphServer.internal_server_error(e)

        return dict_of_changes, 200

    def gitMerge(self):
        """
        /api/git/merge, method is POST
        Expects a JSON body with the 'other_branch_name' key
        Attempts to run a 'git merge' from the other branch into the current one being tracked by git.
        Returns string?,200 if the merge happened and there are no conflicts (no conflict will say 'Already up to date.')
        Returns list,201 if the merge created conflicts (the list is the file paths (relative))
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        data = flask.request.get_json()

        if "other_branch_name" not in data or data["other_branch_name"] == "":
            return "'other_branch_name' not provided", 400

        try:
            return (
                self.git_repo_obj.git.merge(data["other_branch_name"], "--no-edit"),
                200,
            )
        except GitCommandError as ge:
            if "CONFLICT" in ge.stdout:
                """
                Example of a merge conflict error being caught (stdout):

                stdout: 'Auto-merging Graphs/Baseline-Build/Modules/Clean-VM.gx
                CONFLICT (content): Merge conflict in Graphs/Baseline-Build/Modules/Clean-VM.gx
                Automatic merge failed; fix conflicts and then commit the result.'
                """
                try:
                    conflicts: typing.List[str] = []
                    lines: typing.List[str] = ge.stdout.split("\n")
                    for line in lines:
                        if "CONFLICT" in line:
                            conflicts.append(line.split("conflict in")[1].strip())
                    return conflicts, 201
                except Exception as e:
                    return GraphServer.internal_server_error(e)
            raise ge
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def cancelGitMerge(self):
        """
        /api/git/cancelMerge, method is POST
        Attempts to run a 'git reset --merge' to cancel a merge
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        try:
            return (
                self.git_repo_obj.git.reset("--merge"),
                200,
            )
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def gitMergeConflict(self):
        """
        /api/git/mergeConflict, method is POST
        This endpoint is very similar to the 'gitDiff(self)' endpoint except that it REQUIRES the 'path' param to have a merge conflict in that file.
        Hit this endpoint to return options to the frontend on how to resolve the conflicts.
        Expects a JSON body with the 'other_branch_name' and 'path' fields (where 'path' is the path to the file being diff'd).
        The current branch will be used as the branch that is being diff'd against the provided 'other_branch_name'.
        The 'other_branch_name' must already exist on disk in order for the git module to read from it (e.g. a verbose fetch may be needed first)
        ( verbose fetch syntax: 'git fetch origin branch_name:branch_name' ) ( where 'origin' is the name of the remote ) ( see gitFetch(...) function)
        Performs a more sophisticated form of 'git diff' on the provided filepath between the two branches.
        For more information: read the comment for the function 'identify_merge_conflict_causes'.
        """

        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        data = flask.request.get_json()

        if "other_branch_name" not in data or data["other_branch_name"] == "":
            return "'other_branch_name' not provided", 400
        if "path" not in data or data["path"] == "":
            return "'path' not provided", 400

        # returned regardless of success or not
        dict_of_changes = {}

        # the git module wants a relative path (absolute path will result in a git error)
        # Remove any root path values in the filepath
        filepath: str = self.formatFilepath(data["path"])
        f_abspath: str = self.registry.resolve_path(filepath)
        f_relpath: str = os.path.relpath(f_abspath)

        # Compute the changed nodes and graph inputs between the two branches
        try:
            dict_of_changes = identify_merge_conflict_causes(
                git_repo=self.git_repo_obj,
                other_branch_name=data["other_branch_name"],
                filepath=f_relpath,
                gitpath=data["path"],
            )
        except GitCommandError as ge:
            return GraphServer.internal_server_error(ge)
        except Exception as e:
            return GraphServer.internal_server_error(e)

        return dict_of_changes, 200

    def gitResolveMergeConflict(self):
        """
        "/api/git/resolveMergeConflict", method is POST
        Hit this endpoint AFTER 'gitMergeConflict(self)' with the choices chosen by the user to resolve the conflict.
        This endpoint expects many keys in its JSON body (some of which you can simply reuse from 'gitMergeConflict(self)'):
        "other_branch_name" and "path" (strings) same as 'gitMergeConflict(self)',
        "identified_conflicts" and "current_branch_nodes_to_yaml" (reuse these keys from 'gitMergeConflict(self)'),
        "chosen_inputs" and "chosen_nodes" (dicts): these are both expected to be mappings of the name of the graph input -> entire YAML block chosen and node ID -> entire YAML block chosen,
        """

        # the string to return
        reconstructed_file_as_string: str = ""

        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        data = flask.request.get_json()

        # validate the various inputs
        if "other_branch_name" not in data or data["other_branch_name"] == "":
            return "'other_branch_name' not provided", 400
        if "path" not in data or data["path"] == "":
            return "'path' not provided", 400
        if "chosen_inputs" not in data:
            return "'chosen_inputs' not provided (can be empty)", 400
        if "chosen_nodes" not in data:
            return "'chosen_nodes' not provided (can be empty)", 400
        if "identified_conflicts" not in data:
            return "'identified_conflicts' not provided", 400
        if "current_branch_nodes_to_yaml" not in data:
            return "'current_branch_nodes_to_yaml' not provided", 400

        # Remove any root path values in the filepath
        filepath: str = self.formatFilepath(data["path"])

        # the git module wants a relative path (absolute path will result in a git error)
        f_abspath: str = self.registry.resolve_path(filepath)
        f_relpath: str = os.path.relpath(f_abspath)

        try:
            # run the code to "reconstruct" the merge conflict file (replaces the conflicts with a selection from one branch or the other)
            reconstructed_file_as_string = reconstruct_merge_conflicted_file(
                git_repo=self.git_repo_obj,
                other_branch_name=data["other_branch_name"],
                filepath=f_relpath,
                gitpath=data["path"],
                chosen_nodes_on_branch=data["chosen_nodes"],
                chosen_graph_inputs_on_branch=data["chosen_inputs"],
                identified_conflicts=data["identified_conflicts"],
                current_branch_nodes_to_yaml=data["current_branch_nodes_to_yaml"],
            )
        except GitCommandError as ge:
            print(f"git error.")
            return GraphServer.internal_server_error(ge)
        except Exception as e:
            print(f"error.")
            return GraphServer.internal_server_error(e)
        return reconstructed_file_as_string, 201

    def gitBranchesForMergeConflict(self):
        """
        "/api/git/mergeConflictBranches", method is GET
        Attempts to determine the names of both branches currently involved in a merge conflict.
        This function will likely fail for git related reasons if there isn't an unresolved git merge conflict on the current git repo.
        Will return a dictionary with two keys: "this_branch" and "other_branch" if successful
        Will fail if more than one branch name matches the most recent merge conflict commit hash or if either of the branches don't match
        """
        # dictionary to return at the end
        matching_branch_names: typing.Dict[str, str] = {}

        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        try:
            commit_info = git_merge_log(self.git_repo_obj)
            this_branches = git_branches_containing_hash(
                self.git_repo_obj, commit_info["this_branch_commit_hash"]
            )
            other_branches = git_branches_containing_hash(
                self.git_repo_obj, commit_info["other_branch_commit_hash"]
            )

            # possible TODO: don't fail if only one branch is found
            # frontend would need logic to account for this
            if len(this_branches) <= 0:
                return "'this_branch_commit_hash' does NOT match any local branch!", 400
            if len(other_branches) <= 0:
                return (
                    "'other_branch_commit_hash' does NOT match any local branch!",
                    400,
                )
            if len(this_branches) > 1:
                return (
                    "'this_branch_commit_hash' matches more than one branch name!",
                    400,
                )
            if len(other_branches) > 1:
                return (
                    "'other_branch_commit_hash' matches more than one branch name!",
                    400,
                )

            matching_branch_names = {
                "this_branch": this_branches[0],
                "other_branch": other_branches[0],
            }
        except GitCommandError as ge:
            return GraphServer.internal_server_error(ge)
        except Exception as e:
            return GraphServer.internal_server_error(e)

        return matching_branch_names, 200

    def gitFetch(self) -> typing.Tuple[str, int]:
        """
        "/api/git/fetch", method is POST
        Expects a JSON body with the username and password fields
        Optionally the 'branch_name' field/key if a verbose fetch to origin on that branch is requested
        Queries the remote branches to find changes
        Returns: (string response for fetch, 200) on success
        """
        use_provided_password = True
        branch_name = ""
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            data = flask.request.get_json()

            res = self.setup_git_username(data)
            if res[1] != 0:
                return res

            self.disable_git_password_prompt()
            if "password" not in data or data["password"] == "":
                use_provided_password = False

            if "branch_name" in data and data["branch_name"] != "":
                branch_name = data["branch_name"]

            if use_provided_password:
                GraphServer.remove_git_credential_file()
                GraphServer.write_git_credential_file(
                    self.build_password_strings(data["username"], data["password"])
                )

            try:
                if branch_name == "":
                    res = self.git_repo_obj.git.fetch()
                else:
                    res = self.git_repo_obj.git.fetch(
                        "origin", branch_name + ":" + branch_name
                    )
            except GitCommandError as ge:
                return str(ge), 400

            if str(res).strip() == "":
                res = "No remote changes found that required update."
                if branch_name != "":
                    res += " You can assume this means your branch specific fetch was successful."

            return res, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)
        finally:
            # this is always executed before return
            self.remove_git_username()
            self.unset_git_password_prompt()
            if use_provided_password:
                GraphServer.remove_git_credential_file()

    def gitStatus(self) -> typing.Tuple[str, int]:
        """
        "/api/git/status", method is GET
        Returns a string showing the git status output
        Returns: (string response for git status, 200) on success
        """
        try:
            if not self.git_repo_obj:
                return GraphServer.git_not_found()

            try:
                res = self.git_repo_obj.git.status()
            except GitCommandError as ge:
                return str(ge), 400

            return res, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def setup_git_username(self, json_data) -> typing.Tuple[str, int]:
        """
        Utility function to handle adding username to git config file.
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        # check the username field was provided
        if "username" not in json_data or json_data["username"] == "":
            return "'username' not provided", 400

        # enable credential store
        self.git_repo_obj.config_writer().set_value(
            "credential", "helper", value="store"
        ).release()
        # set the username in .gitconfig
        self.git_repo_obj.config_writer().set_value(
            "credential", "username", value=parse.quote_plus(json_data["username"])
        ).release()

        return "", 0

    def disable_git_password_prompt(self) -> typing.Tuple[str, int]:
        """
        Utility function to fail immediately if git doesn't have a password and needs to prompt one in the terminal
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        # set the core askpass policy in the config
        self.git_repo_obj.config_writer().set_value(
            "core", "askPass", value="true"
        ).release()

        return "", 0

    def unset_git_password_prompt(self) -> typing.Tuple[str, int]:
        """
        Utility function to reset changes made by 'disable_git_password_prompt()'
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        # remove the core askpass policy in the config
        writer = self.git_repo_obj.config_writer()
        try:
            writer.remove_option("core", "askPass")
        except Exception:
            pass
        finally:
            writer.release()

        return "", 0

    def remove_git_username(self) -> typing.Tuple[str, int]:
        """
        Utility function to handle removing of username from git config file
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        writer = self.git_repo_obj.config_writer()
        try:
            writer.remove_option("credential", "username")
        except Exception:
            pass
        finally:
            writer.release()

        return self.remove_git_credential_store_option()

    def remove_git_credential_store_option(self) -> typing.Tuple[str, int]:
        """
        Utility function to handle removing of 'credential store' from config file
        """
        if not self.git_repo_obj:
            return GraphServer.git_not_found()

        writer = self.git_repo_obj.config_writer()

        try:
            writer.remove_option("credential", "store")
        except Exception:
            pass
        finally:
            writer.release()

        return "", 0

    def build_password_strings(self, username: str, password: str) -> typing.List[str]:
        """
        Utility function to create 'git style' username:passwords for temporary placement in .git-credentials files
        """
        if not self.git_repo_obj:
            return []

        remote = self.git_repo_obj.remote()

        strings = []
        for url in remote.urls:
            split_url = url.split("//")
            protocol = split_url[0]
            location = split_url[1].split("/")[0]
            strings.append(
                protocol
                + "//"
                + parse.quote_plus(username)
                + ":"
                + parse.quote_plus(password)
                + "@"
                + location
            )

        return strings

    def heartbeat_info(self):
        venv = GraphRegistry.find_venv_name()
        if venv == "":
            venv = "No virtual environment is in use"
        else:
            venv = venv

        branch = ""
        if self.git_repo_obj:
            branch = self.git_repo_obj.active_branch.name
        if branch == "":
            branch = "Not currently serving a directory managed by git"
        else:
            branch = branch

        currentTime = datetime.now().strftime(r"%H:%M:%S")

        gitStatus = self.gitStatus()
        gitBranches = self.gitBranches()
        emit(
            "heartbeatInfo",
            {
                "venv": venv,
                "branch": branch,
                "currentTime": currentTime,
                "gitStatus": gitStatus,
                "gitBranches": gitBranches,
            },
        )

    @staticmethod
    def write_git_credential_file(strings_to_write: typing.List[str]):
        """
        Helper function to write credentials to the git credential file in the home of the user hosting the GraphEx server.
        """
        path_to_file = os.path.abspath(os.path.expanduser("~/.git-credentials"))
        with open(path_to_file, "w") as f:
            for s in strings_to_write:
                f.write(s + "\n")

    @staticmethod
    def remove_git_credential_file():
        """
        Helper function to remove a git credential file in the home repo of the user hosting the GraphEx server.
        """
        path_to_file = os.path.abspath(os.path.expanduser("~/.git-credentials"))
        try:
            os.remove(path_to_file)
        except FileNotFoundError:
            pass

    def searchFiles(self):
        """
        "/api/search", method is POST
        Expects a JSON body with the 'query' field and optionally the 'include_filenames' field
        Searches all files in the server's 'root' directory for strings matching the provided query.
        Returns: ({"query": original_query, "list_of_matches": list_of_matches}, 200) on success
        See 'create_search_match_dict()' for the structure of each list item
        """
        try:
            data = flask.request.get_json()

            include_filenames = False
            case_sensitive = False
            node_deep_search = False
            stop_on_first_match = True
            extract_node_name = False
            extensions_to_include = []
            extensions_to_exclude = []

            if "query" not in data or data["query"] == "":
                return "'query' not provided", 400

            if "include_filenames" in data and data["include_filenames"] == True:
                include_filenames = True

            if "case_sensitive" in data and data["case_sensitive"] == True:
                case_sensitive = True

            if "node_deep_search" in data and data["node_deep_search"] == True:
                node_deep_search = True

            if "stop_on_first_match" in data and data["stop_on_first_match"] == False:
                stop_on_first_match = False

            if "include_extensions_string" in data:
                temp = data["include_extensions_string"]
                # Removes whitespace, forces lowercase, splits on commas and filters out empty array indices
                extensions_to_include = [
                    e for e in "".join(str(temp).split()).lower().split(",") if e
                ]

            if "extract_node_name" in data and data["extract_node_name"] == True:
                extract_node_name = True

            if "exclude_extensions_string" in data:
                temp = data["exclude_extensions_string"]
                # Removes whitespace, forces lowercase, splits on commas and filters out empty array indices
                extensions_to_exclude = [
                    e for e in "".join(str(temp).split()).lower().split(",") if e
                ]

            list_of_matches = self.walk_search(
                self.registry.root,
                str(data["query"]),
                include_filenames,
                case_sensitive=case_sensitive,
                extensions_to_include=extensions_to_include,
                extensions_to_exclude=extensions_to_exclude,
                node_deep_search=node_deep_search,
                stop_on_first_match=stop_on_first_match,
                extract_node_name=extract_node_name,
            )
            return {
                "query": data["query"],
                "list_of_matches": list_of_matches,
                "root_dir": self.registry.root,
            }, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    def walk_search(
        self,
        current_dir_path: str,
        search_query: str,
        match_filenames: bool,
        case_sensitive: bool,
        extensions_to_include: typing.List[str],
        extensions_to_exclude: typing.List[str],
        node_deep_search: bool,
        stop_on_first_match: bool,
        extract_node_name: bool,
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Searches once through directories in the provided 'current_dir_path' (recursively) to find files that match search_query on either content or filename (if specified).
        Returns a list of dicts created by 'create_search_match_dict()'
        """
        # holds the results to return to the frontend
        results = []

        # max size of results array
        # the actual size could be up to 2x larger, this just marks the cutoff point between reading more files
        # the size will be even larger if deep search is enabled
        results_max_size = 1000

        # format the search string
        sq_case = (
            search_query.strip() if case_sensitive else search_query.lower().strip()
        )

        ## GX Node Deep/Smart search variables
        # holds this structure: { node_name: { absolute_file_path: [id1, id2, idn] } }
        deep_search_directory: typing.Dict[str, typing.Dict[str, typing.List[str]]] = {}
        ##

        # walk the provided directory
        for dir_path, dir_names, filenames in os.walk(current_dir_path):
            if len(results) >= results_max_size:
                break
            for fn in filenames:
                # check if we are supposed to match on this file extension
                if not GraphServer.search_file_ext_is_included(
                    fn.lower(),
                    extensions_to_include,
                    extensions_to_exclude,
                    search_only_gx_files=node_deep_search,
                ):
                    continue
                fn_case = fn.strip() if case_sensitive else fn.strip().lower()
                if match_filenames and sq_case in fn_case:
                    results.append(
                        GraphServer.create_search_match_dict(os.path.join(dir_path, fn))
                    )
                abs_path = os.path.join(dir_path, fn)
                matches = GraphServer.search_file_for_match(
                    abs_path,
                    sq_case,
                    case_sensitive=case_sensitive,
                    stop_on_first_match=stop_on_first_match,
                    results_max_size=results_max_size,
                )
                if len(matches):
                    results.extend(matches)
                if node_deep_search:
                    GraphServer.getNodesFromGxFile(abs_path, deep_search_directory)
                if len(results) >= results_max_size:
                    break
        # end for loop walking directory

        # Try to find the nodes with the smart deep search
        if node_deep_search and len(deep_search_directory.keys()):
            # for each node that exists in our root directory
            for node_name in deep_search_directory.keys():
                # get the metadata for that node name
                node_data = self.registry.find_node(node_name)
                if node_data is None:
                    # this could happen if the plugin associated with the node isn't installed or provided to the GraphEx server instance
                    print(
                        f"ERROR: node with name: {node_name} not found in node registry! (during global search)"
                    )
                    continue
                # check the description field for a match
                node_description = (
                    node_data.description.strip()
                    if case_sensitive
                    else node_data.description.strip().lower()
                )
                if sq_case in node_description:
                    for absolute_filepath in deep_search_directory[node_name].keys():
                        for node_id in deep_search_directory[node_name][
                            absolute_filepath
                        ]:
                            results.append(
                                GraphServer.create_search_match_dict(
                                    absolute_filepath,
                                    -2,
                                    line_content=node_data.description,
                                    node_id=node_id,
                                )
                            )
                    # end for filepath in deep search registry
                # endif description name match
                # check the socket names for a match
                for base_socket in node_data.sockets(None, None):
                    if base_socket.is_input:
                        # input sockets are all explicitly provided in the GX file
                        continue
                    socket_name = (
                        base_socket.name.strip()
                        if case_sensitive
                        else base_socket.name.strip().lower()
                    )
                    if socket_name == "_forward" or socket_name == "_backward":
                        continue
                    if sq_case in socket_name or sq_case == socket_name:
                        for absolute_filepath in deep_search_directory[
                            node_name
                        ].keys():
                            for node_id in deep_search_directory[node_name][
                                absolute_filepath
                            ]:
                                results.append(
                                    GraphServer.create_search_match_dict(
                                        absolute_filepath,
                                        -3,
                                        line_content=base_socket.name,
                                        node_id=node_id,
                                    )
                                )
                        # end for filepath in deep search registry
                    # endif socket name match
                # end for socket in node data
            # end for node_name in available nodes
        # end if statement for deep/smart search

        if extract_node_name:
            for r_dict in results:
                r_dict["node_name"] = ""
                if (
                    "line_number" in r_dict
                    and r_dict["line_number"] >= 0
                    and "filepath" in r_dict
                ):
                    f_abspath: str = self.registry.resolve_path(r_dict["filepath"])
                    with open(f_abspath, "r") as file:
                        r_dict["node_name"] = node_name_from_file_content(
                            file.readlines(), r_dict["line_number"]
                        )

        return results

    @staticmethod
    def create_search_match_dict(
        filepath: str, line_number: int = -1, line_content: str = "", node_id: str = ""
    ) -> typing.Dict[str, typing.Any]:
        """
        Creates a tuple in a standardized form to be added to the list returned by 'walk_search'
        Returns a dict in the form: (matching file, line number or -1, matching line content or "", matching node_id or "")
        """
        return {
            "filepath": filepath,
            "line_number": line_number,
            "line_content": line_content,
            "node_id": node_id,
        }

    @staticmethod
    def search_file_for_match(
        filepath: str,
        sq_case: str,
        case_sensitive: bool,
        stop_on_first_match: bool,
        results_max_size: int,
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Opens the provided filepath in read-only mode and searches for a line that matches the provided search_query.
        Will ignore files that can't be read as plaintext strings (files containing binary data).
        returns None if not found or a dict created by 'create_search_match_dict()'
        """
        matches = []
        try:
            with open(filepath, "r") as f:
                for line_number, line_content in enumerate(f, 1):
                    content_case = (
                        line_content.strip()
                        if case_sensitive
                        else line_content.strip().lower()
                    )
                    if sq_case in content_case:
                        matches.append(
                            GraphServer.create_search_match_dict(
                                filepath, line_number, line_content
                            )
                        )
                        if stop_on_first_match:
                            break
                        if len(matches) >= results_max_size:
                            break
        except UnicodeDecodeError:
            # this file isn't text
            pass
        return matches

    @staticmethod
    def search_file_ext_is_included(
        filename: str,
        included_extensions: typing.List[str],
        excluded_extensions: typing.List[str],
        search_only_gx_files: bool,
    ) -> bool:
        """
        Returns True if this file has an extension allowed by the filters of the search
        """
        # short circuit this whole function if we are only matching on GX files
        if search_only_gx_files:
            return True if filename.endswith("gx") else False
        # Any match that ends with an excluded extension should not be allowed
        for exc_ext in excluded_extensions:
            exc_ext = exc_ext if exc_ext.startswith(".") else "." + exc_ext
            if filename.endswith(exc_ext):
                return False
        # Any match the ends with an included extensions should be allowed
        for inc_ext in included_extensions:
            inc_ext = inc_ext if inc_ext.startswith(".") else "." + inc_ext
            if filename.endswith(inc_ext):
                return True
        # If we didn't find a match on an included extensions and the user specified some, then we shouldn't allow this match
        if len(included_extensions) > 0:
            return False
        # Else this match is fine
        return True

    def nodeIdFromFile(self):
        """
        "/api/nodeIdFromFile", method is POST
        Expects a JSON body with the 'path' field and the 'line_number' field.
        Searches a file on the backend for the line in the YAML file containing the ID of the node
        returns { "nodeId": ID } , ID will be a string (empty if not found)
        """
        try:
            data = flask.request.get_json()

            if "path" not in data or data["path"] == "":
                return "'path' not provided", 400

            if "line_number" not in data or data["line_number"] == "":
                return "'line_number' not provided", 400

            # join with root folder
            f_abspath: str = self.registry.resolve_path(data["path"])
            # retrieve the line number
            line_number: int = int(data["line_number"])

            # check that the file exists and is a file
            if not os.path.exists(f_abspath):
                return GraphServer.file_does_not_exist(f_abspath)

            if not os.path.isfile(f_abspath):
                return GraphServer.not_a_file(f_abspath)

            node_id = ""

            with open(f_abspath, "r") as file:
                node_id = node_id_from_file_content(file.readlines(), line_number)

            return {"nodeId": node_id}, 200
        except Exception as e:
            return GraphServer.internal_server_error(e)

    @staticmethod
    def getNodesFromGxFile(
        filepath: str,
        deep_search_directory: typing.Dict[str, typing.Dict[str, typing.List[str]]],
    ) -> None:
        """
        Retrieve all the nodes from a GX file by parsing the file for the lines that contain the ID of each node.
        Adds results to the deep_search_directory by reference, which should be of the form:
        { node_name: { absolute_file_path: [id1, id2, idn] } }
        """
        combined_matches = []
        with open(filepath, "r") as f:
            combined_matches = re_findall(r"name: .+\n\s+id: \S+-\d+", f.read())
        # end with open file
        for m in combined_matches:
            # a newline character has to exist in the match specified by the regex above, so we won't check that array indexes are out of bounds here
            split_data = str(m).split("\n")
            node_name = split_data[0].strip()[6:].strip('"')
            node_id = split_data[1].strip()[4:].strip('"')
            if node_name not in deep_search_directory:
                deep_search_directory[node_name] = {}
            if filepath not in deep_search_directory[node_name]:
                deep_search_directory[node_name][filepath] = []
            deep_search_directory[node_name][filepath].append(node_id)
        # end for m in combined_matches

    def decryptSecrets(self) -> typing.Dict[str, str]:
        """
        Decrypts the secrets from the GraphEx configuration file.
        These unencrypted values should NEVER leave the backend server.

        :returns: Dictionary of secret_name -> plaintext_value
        """
        temp: typing.Dict[str, str] = {}
        if self.config and self.vault_password:
            for k, v in self.config.get_all_encrypted_secrets().items():
                try:
                    temp[k] = decryptSecret(v, self.vault_password)
                except InvalidToken:
                    raise Exception(
                        f"The vault password provided to decrypt the secrets on the server is incorrect! Unable to decrypt the secret named: {k} ... Please manually verify the password is correct using the 'vault' mode of the GraphEx CLI."
                    )
        return temp

    # Returns the name of the filepath without any root prefixes
    def formatFilepath(self, filepath) -> str:
        filepath_parts = filepath.split("/")
        root_parts = self.registry.root.split("/")

        # Find the common part that needs to be removed
        substring_to_remove = None
        for part in root_parts:
            if part in filepath_parts:
                substring_to_remove = part
                break

        if substring_to_remove:
            result = filepath.replace(substring_to_remove, "")
        else:
            result = filepath

        # Remove leading slash if it exists
        result = result.lstrip("/")
        return result
