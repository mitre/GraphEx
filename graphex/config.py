import os
import typing

from graphex.util import parse_yml, dump_yml
from graphex.graphfile import GraphInputValueMetadata


class ConfigFile(typing.TypedDict):
    title: typing.Optional[str]
    """Custom title for the GraphEX UI."""

    plugins: typing.List[str]
    """Plugins to automatically load."""

    root: typing.Optional[str]
    """The default root directory to serve or reference files from"""

    ssl_certificates_path: typing.Optional[str]
    """The path to the certificates to use when serving the GraphEx server"""

    graph_inputs: typing.Dict[str, typing.Any]
    """Graph Input configuration"""

    secrets: typing.Dict[str, typing.Any]
    """Encrypted secrets that apply to all graphs as graph inputs under the '*' scope"""

    vault_password_path: typing.Optional[str]
    """The path to the password to decrypt the secrets in this configuration file."""

    inventory_path: typing.Optional[str]
    """The path to the inventory file to use in the GraphEx UI"""

    log_rollover_amount: typing.Optional[int]
    """The number of logs retain before rolling over the oldest one to write the latest one"""


class GraphConfig:
    """
    Object for the GraphEX configuration file. This file contains information such as default graph input values.

    :param path: The path to the config file.
    """

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        """The path to the config."""

        self.contents: ConfigFile = {
            "title": None,
            "plugins": [],
            "root": None,
            "ssl_certificates_path": None,
            "graph_inputs": {},
            "secrets": {},
            "vault_password_path": None,
            "inventory_path": None,
            "log_rollover_amount": None
        }
        """The contents of the config."""

        error = None
        file_contents = ""
        try:
            with open(path, mode="r") as f:
                file_contents = f.read()
        except Exception as e:
            error = RuntimeError(f'Failed to read config file contents "{path}": {str(e)}')

        if error:
            raise error

        try:
            self.contents = parse_yml(file_contents)
        except Exception as yaml_error:
            yaml_error_str = ("\n" + " " * 29).join(str(yaml_error).split("\n"))
            error = RuntimeError(
                f'Failed to parse config file "{path}":\n    - Not a valid YAML file: {str(yaml_error_str)}.'
            )

        if error:
            raise error

        if "title" not in self.contents:
            if "Title" in self.contents:
                self.contents["title"] = self.contents["Title"]
            else:
                self.contents["title"] = None

        if "plugins" not in self.contents:
            if "Plugins" in self.contents:
                self.contents["plugins"] = self.contents["Plugins"]
            else:
                self.contents["plugins"] = []

        if "root" not in self.contents:
            if "Root" in self.contents:
                self.contents["root"] = self.contents["Root"]
            else:
                self.contents["root"] = None

        if "ssl_certificates_path" not in self.contents:
            if "SSL_certificates_path" in self.contents:
                self.contents["ssl_certificates_path"] = self.contents["SSL_certificates_path"]
            elif "SSL_Certificates_Path" in self.contents:
                self.contents["ssl_certificates_path"] = self.contents["SSL_Certificates_Path"]
            elif "Ssl_Certificates_Path" in self.contents:
                self.contents["ssl_certificates_path"] = self.contents["Ssl_Certificates_Path"]
            else:
                self.contents["ssl_certificates_path"] = None

        if "graph_inputs" not in self.contents:
            if "Graph_Inputs" in self.contents:
                self.contents["graph_inputs"] = self.contents["Graph_Inputs"]
            else:
                self.contents["graph_inputs"] = {}

        if "secrets" not in self.contents:
            if "Secrets" in self.contents:
                self.contents["secrets"] = self.contents["Secrets"]
            else:
                self.contents["secrets"] = {}

        if "vault_password_path" not in self.contents:
            if "Vault_Password_Path" in self.contents:
                self.contents["vault_password_path"] = self.contents["Vault_Password_Path"]
            else:
                self.contents["vault_password_path"] = None

        if "inventory_path" not in self.contents:
            if "Inventory_Path" in self.contents:
                self.contents["inventory_path"] = self.contents["Inventory_Path"]
            elif "Inventory_path" in self.contents:
                self.contents["inventory_path"] = self.contents["Inventory_path"]
            else:
                self.contents["inventory_path"] = None

        if "log_rollover_amount" not in self.contents:
            if "Log_Rollover_Amount" in self.contents:
                self.contents["log_rollover_amount"] = self.contents["Log_Rollover_Amount"]
            else:
                self.contents["log_rollover_amount"] = None
            

        # When a filename is specified but no values are provided to it, remove it as an option
        graph_input_filenames = list(self.contents["graph_inputs"].keys())
        for key in graph_input_filenames:
            if self.contents["graph_inputs"][key] is None:
                del self.contents["graph_inputs"][key]

    def get_title(self):
        """
        Get the title value from the config.

        :returns: The title, or ``None`` if no custom title is configured.
        """
        return self.contents["title"]

    def get_scope(self, root: str, path: str):
        """
        Get the "scope" name for a file in the given root.

        :param root: The root of the graph file system.
        :param path: The path to the file to get the scope for.

        :returns: The scope.
        """
        base = os.path.abspath(root).rstrip(os.sep) + os.sep
        abspath = os.path.abspath(
            path if os.path.isabs(path) else os.path.join(base, path)
        )
        if not abspath.startswith(base):
            raise RuntimeError(
                f"{abspath} is not contained within the root directory {base}"
            )
        return abspath[len(base) :].replace(os.sep, "/").lstrip("/")

    def get_graph_inputs(
        self,
        names: typing.List[str],
        scope: typing.Optional[str] = None,
        include_wildcard: typing.Optional[bool] = False,
    ) -> typing.Dict[str, GraphInputValueMetadata]:
        """
        Get the values for graphs inputs as stored in this config file.

        :param names: The names of the graph inputs to get.
        :param scope: The scope to use for resolving the graph inputs.

        :returns: A dictionary mapping input name to value.
        """

        def process_value(value: typing.Any) -> GraphInputValueMetadata:
            if not isinstance(value, dict):
                return {
                    "value": value,
                    "childValues": {},
                    "datatype": get_datatype(value),
                }
            elif (
                "datatype" not in value
                and "Datatype" not in value
                and "fromConfig" not in value
                and "FromConfig" not in value
                and "from_config" not in value
                and "From_Config" not in value
                and "fromSecret" not in value
                and "FromSecret" not in value
                and "from_secret" not in value
                and "From_Secret" not in value
            ):
                raise ValueError(
                    'Config error: "datatype","fromConfig" or "fromSecret" must be present for non primitives'
                )
            elif "datatype" in value or "Datatype" in value:
                if "datatype" not in value:
                    value["datatype"] = value["Datatype"]
                return {
                    "childValues": (
                        {
                            child: process_value(value["values"][child])
                            for (child) in value["values"]
                        }
                        if "values" in value
                        else {}
                    ),
                    "datatype": str(value["datatype"]),
                }
            elif "fromSecret" in value or "FromSecret" in value or "from_secret" in value or "From_Secret" in value:
                if "fromSecret" not in value:
                    value["fromSecret"] = value["FromSecret"] if "FromSecret" in value else (value["from_secret"] if "from_secret" in value else value["From_Secret"])
                return {
                    "fromSecret": value["fromSecret"],
                    "childValues": {},
                    "datatype": "String",
                }
            elif "fromConfig" in value or "FromConfig" in value or "from_config" in value or "From_Config" in value:
                if "fromConfig" not in value:
                    value["fromConfig"] = value["FromConfig"] if "FromConfig" in value else (value["from_config"] if "from_config" in value else value["From_Config"])
                return {
                    "childValues": {},
                    "fromConfig": str(value["fromConfig"]),
                    "datatype": "String",
                }
            else:
                raise ValueError("Config if malformed")

        def get_datatype(value: typing.Any):
            if not isinstance(value, list):

                if isinstance(value, str):
                    return "String"

                if isinstance(value, bool):
                    return "Boolean"

                if isinstance(value, float) or isinstance(value, int):
                    return "Number"

                else:
                    return ""
            elif len(value) == 0:
                return ""
            else:
                return get_datatype(value[0])

        values: typing.Dict[str, GraphInputValueMetadata] = {}
        graph_inputs = self.contents["graph_inputs"]
        for name in names:
            if scope in graph_inputs and name in graph_inputs[scope]:
                values[name] = process_value(graph_inputs[scope][name])
            elif "*" in graph_inputs and name in graph_inputs["*"]:
                values[name] = process_value(graph_inputs["*"][name])
        if include_wildcard and "*" in graph_inputs:
            wildcard_inputs: typing.Dict[str, typing.Any] = graph_inputs["*"]
            for gi_name in wildcard_inputs.keys():
                if gi_name not in values:
                    values[gi_name] = process_value(wildcard_inputs[gi_name])

        return values

    def get_graph_input_filepaths(self):
        """
        Returns the 'top level' graph_inputs contained from the contents of this config file.
        This is typically the paths of the graph_files that have specfic config values and possibly the value '*' (representing applicability to all graph files)
        """
        return self.contents["graph_inputs"].keys()

    def get_graph_input_filenames_without_paths(self) -> typing.List[str]:
        """
        Returns get_graph_input_filepaths but with only the GX filenames (no paths).
        This explicitly ignores pathing created by the user in the configuration file.
        """
        fns: typing.List[str] = []
        for k in self.get_graph_input_filepaths():
            fns.append(os.path.basename(k))
        return fns

    def get_all_encrypted_secrets(self):
        """
        Returns all secrets stored in this configuration file as a dictionary of name -> encrypted_value
        """
        return self.contents["secrets"] if "secrets" in self.contents else {}

    def has_secrets(self):
        """
        Returns true if this config file object has secrets stored in it.
        """
        return len(self.contents["secrets"]) > 0

    def get_encrypted_secret(self, secret_name: str):
        """
        Retrieves the encrypted value associated with a name. If the name isn't found, returns None.
        """
        return self.contents["secrets"].get(secret_name, None)

    def has_secret_name(self, secret_name: str):
        """
        Returns True if the secret name exists in the config file
        """
        return secret_name in self.contents["secrets"]

    def add_secret(self, secret_name: str, secret_value: str) -> None:
        """
        Adds a secret to the config file. Overwrites existing values of the same secret name.
        """
        self.contents["secrets"][secret_name] = secret_value

    def remove_secret(self, secret_name: str):
        """
        Removes a secret from the config file. Returns the encrypted value of the removed name. Will return None if the name was not found in the config file.
        """
        if self.has_secret_name(secret_name):
            return self.contents["secrets"].pop(secret_name)
        return None

    def export_to_yaml(self):
        """
        Exports/dumps this python config object into a yml/yaml string that can be written to disk
        """
        return dump_yml(self._trim_missing_values())

    def _trim_missing_values(self):
        """
        Removes any key that has a value of 'None' or '{}' from the config and returns a deep copied object.
        """
        from copy import deepcopy

        temp = deepcopy(self.contents)
        for k, v in self.contents.items():
            if v == None or (isinstance(v, dict) and len(v) <= 0):
                temp.pop(k)  # type: ignore
        return temp

    def export_and_write_to_disk(self):
        """
        Calls the 'export_to_yaml' function to produce a yaml string and then overwrites the previous value of the file on disk.
        Uses the path provided when this object was created in order to determine the file to write to.
        """
        with open(self.path, mode="w") as f:
            f.write(self.export_to_yaml())
