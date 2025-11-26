import os
import re
import shutil
import sys
import typing
from dataclasses import dataclass

from graphex import (
    FILE_EXTENSION,
    Graph,
    GraphConfig,
    GraphexLogger,
    GraphRegistry,
    GraphRuntime,
    GraphServer,
    vault,
    GraphInputValueMetadata,
    GraphInventory
)

from cryptography.fernet import InvalidToken
from getpass import getpass


@dataclass
class Argument:
    value: typing.Any
    flags: typing.List[str]
    description: str
    toggle: bool = False
    multiple: bool = False


@dataclass
class GraphInput:
    name: str
    value: typing.Any
    description: str
    datatype: str
    is_list: bool
    is_password: bool
    enum_options: typing.Optional[
        typing.List[str]
    ]  # This may not be in the list due to previous graphs.
    is_secret: bool


HELP = Argument(
    value=False, flags=["-h", "--help"], description="Show this help menu.", toggle=True
)
VERBOSE = Argument(
    value=False,
    flags=["-v", "--verbose"],
    description="Increase verbosity (enable debug logs).",
    toggle=True,
)
VERBOSE_ERRORS = Argument(
    value=False,
    flags=["-e", "--errors"],
    description="Increase verbosity of error messages (enables developer stack trace).",
    toggle=True,
)
AZURE_MODE = Argument(
    value=False,
    flags=["-a", "--azure"],
    description="Enable Azure DevOps Pipeline integration.",
    toggle=True,
)
VALIDATE_ONLY = Argument(
    value=False,
    flags=["-o", "--validate_only"],
    description="Checks the provided graph file for errors and then exits instead of running the graph",
    toggle=True,
)
PLUGINS = Argument(
    value=None,
    flags=["-l", "--plugins"],
    description="List of installed plugins to load (comma-separated list).",
    multiple=True,
)
CONFIG = Argument(
    value=None,
    flags=["-c", "--config"],
    description="Configuration file to use for pre-populating graph inputs and some other graphex flags.",
)
ROOT = Argument(
    value=None,
    flags=["-r", "--root"],
    description="Directory to use as the root of the graph file system (used to resolve relative paths).",
)
FILE = Argument(
    value=None, flags=["-f", "--file"], description="Graph file to execute."
)
PORT = Argument(
    value=8080, flags=["-p", "--port"], description="Port for the webserver."
)
SSL_CERTIFICATES = Argument(
    value=None,
    flags=["-s", "--ssl_certificates_path"],
    description="Path to a folder containing 'cert.pem' and 'key.pem' files to load into the GraphEx server.",
)
SHOW_INPUTS = Argument(
    value=False,
    flags=["-i", "--show_inputs"],
    description="Log the graph inputs provided to the graph at the top of the terminal before execution. Password strings will be replaced with asterisks of the appropriate length.",
    toggle=True,
)
INVENTORY = Argument(
    value=None,
    flags=["-inv", "--inventory_path"],
    description="An inventory file (YML) to populate the inventory sidebar in the GraphEx UI.",
)
LOG_ROLLOVER = Argument(
    value=20, flags=["-lr", "--log_rollover_amount"], description="How many local logs to keep before deleting the oldest log when starting a new one (rollover)."
)

MODE = None

# 'vault' mode only arguments:
ENCRYPT = Argument(
    value=False,
    flags=["-x", "-e", "-s", "--encrypt", "--store"],
    description="Save + encrypt a provided plaintext message into a secret.",
    toggle=True,
)
DECRYPT = Argument(
    value=False,
    flags=["-d", "--decrypt"],
    description="Decrypt a stored + encrypted secret using the same password you used to encrypt it.",
    toggle=True,
)
REMOVE = Argument(
    value=False,
    flags=["-r", "--remove", "--delete"],
    description="Removes a stored + encrypted secret from the provided configuration file.",
    toggle=True,
)
NAME_OF_SECRET = Argument(
    value=None,
    flags=["-n", "--name", "--secret"],
    description="The name to assign to the secret. Will not overwrite a secret with the same name in a config file.",
)
OVERWRITE = Argument(
    value=False,
    flags=["-o", "--overwrite", "--force"],
    description="Overrides the default behavior and overwrites a secret that already exists in a configuration file with the same name.",
    toggle=True,
)
PASSWORD_PATH = Argument(
    value=None,
    flags=["-pf", "--passwordFile", "--passwordPath", "--vault_password_path"],
    description="An optional path to a plaintext file containing the password to use when interacting with vault options.",
)
HASHED_SECRET = Argument(
    value=None,
    flags=["-v", "--value", "--hash", "--hashedSecret"],
    description="When not using a configuration file, the value/hash to decrypt.",
)
HIDE_SECRET_INPUT = Argument(
    value=False,
    flags=["--hide", "--hideInput"],
    description="Hides the terminal input for the value you provide for the secret. Will require you to enter the secret value twice.",
    toggle=True,
)
PASSWORD = None


def get_terminal_width(default: int = 120, max_width: int = 240) -> int:
    """
    Return a terminal width that is safe to use in headless/non-TTY environments.
    Clamps to a sensible range to avoid excessively large widths from environment variables.
    """
    try:
        if sys.stdout.isatty():
            width = shutil.get_terminal_size(fallback=(default, 24)).columns
        else:
            width = int(os.environ.get("COLUMNS", default))
    except Exception:
        width = default
    return max(40, min(width, max_width))  


def fit_text_to_width(text: str, width: int) -> typing.List[str]:
    """
    Wrap the given text such that it fits into the given width.

    :param text: The text to wrap.
    :param width: The width to fit.

    :returns: A list of strings such that each string is a line of text that fits the given width.
    """
    lines = []
    line = ""

    def push_line():
        nonlocal lines, line
        lines.append(line.strip())
        line = ""

    for input_line in re.split(r"\n+", text):
        words = re.split(r"\s+", input_line)

        for word in words:
            word = word + " "
            if len(word) > width:
                # Word itself extends beyond the width of the line, we need to break the word
                if len(line) / width > 0.5:
                    push_line()
                while word:
                    line += word[0:width]
                    word = word[width:]
                    if len(line) >= width:
                        push_line()
                continue

            if len(line) + len(word) > width:
                # Word will cause the line to be too long, wrap
                push_line()
                line += word
                continue

            line += word

        if len(line):
            push_line()

    return lines


def print_table(
    titles: typing.List[str],
    rows: typing.List[typing.Tuple[str, ...]],
    widths: typing.List[int],
):
    """
    Format the given information as a table.

    :param titles: The titles of the table.
    :param rows: The data for each row of the table.
    :param widths: The widths of each column of the table.
    """
    # Print titles
    for i in range(len(titles)):
        print(titles[i].ljust(widths[i]), end="")
    print()

    # Print divider
    print("─" * sum(widths))

    # Print rows
    for row in rows:
        entries = [
            fit_text_to_width(entry, width=widths[i]) for i, entry in enumerate(row)
        ]
        max_lines = max([len(lines) for lines in entries])

        for row_index in range(max_lines):
            for i, entry in enumerate(entries):
                line = (
                    entry[row_index].ljust(widths[i])
                    if row_index < len(entry)
                    else (" " * widths[i])
                )
                print(line, end="")
            print()


def print_help_and_exit(
    mode: typing.Optional[str],
    args: typing.List[Argument],
    graph_inputs: typing.List[GraphInput],
    errors: typing.List[str] = [],
    composite_inputs: typing.List[str] = [],
) -> typing.NoReturn:
    """
    Print the help menu and exit. This will exit with a status code of `1` if any errors are provided, otherwise `0`.

    :param mode: The mode for this help menu.
    :param args: Arguments available to this help menu.
    :param graph_inputs: Graph inputs available to this help menu.
    :param errors: Error messages to print alongside this help menu.
    """

    def process_composite(input: GraphInputValueMetadata) -> typing.Union[str, dict]:

        if "value" in input:
            return input["value"]
        else:
            return {
                name: process_composite(value)
                for name, value in input["childValues"].items()
            }

    TERMINAL_WIDTH = get_terminal_width()

    if errors:
        for error in errors:
            print("\u001b[1m\u001b[31mError: " + error + "\u001b[0m")
        print()

    if mode == "run":
        print(f"Usage: python3 -m graphex run <file> [args...] [GraphInput=Value...]")
    elif mode == "serve":
        print(f"Usage: python3 -m graphex serve [args...]")
    elif mode == "vault":
        print(f"Usage: python3 -m graphex vault [args...]")
    else:
        print(f"Usage: python3 -m graphex <mode>")
        print()
        print_table(
            titles=["MODE", "DESCRIPTION"],
            rows=[
                ("serve", "Start the GraphEX webserver."),
                ("run", "Directly run a graph file."),
                ("vault", "Store, retrieve, or remove GraphEx secrets"),
            ],
            widths=[10, TERMINAL_WIDTH - 10],
        )

    if args:
        FLAGS = []
        VALUES = []
        DESCRIPTIONS = []
        for arg in args:
            flagstr = ", ".join(arg.flags)
            if arg.toggle:
                FLAGS.append(flagstr)
            elif arg.multiple:
                FLAGS.append(flagstr + " <value(,)...>")
            else:
                FLAGS.append(flagstr + " <value>")

            if isinstance(arg.value, list):
                VALUES.append(str(arg.value)[1:-1])
            elif arg.value is not None and arg.value != False:
                VALUES.append(str(arg.value))
            else:
                VALUES.append("")

            DESCRIPTIONS.append(arg.description)

        FLAGS_WIDTH = (
            max(8, min(int(TERMINAL_WIDTH * 0.3), max([len(flag) for flag in FLAGS])))
            + 4
        )
        VALUES_WIDTH = (
            max(8, min(int(TERMINAL_WIDTH * 0.3), max([len(val) for val in VALUES])))
            + 4
        )
        DESCRIPTION_WIDTH = TERMINAL_WIDTH - FLAGS_WIDTH - VALUES_WIDTH

        print()
        print_table(
            titles=["ARGUMENT", "VALUE", "DESCRIPTION"],
            rows=[(FLAGS[i], VALUES[i], DESCRIPTIONS[i]) for i in range(len(args))],
            widths=[FLAGS_WIDTH, VALUES_WIDTH, DESCRIPTION_WIDTH],
        )
        print()

    if graph_inputs:
        NAMES = [gi.name for gi in graph_inputs]
        DATATYPES = [
            gi.datatype + (" (List)" if gi.is_list else "") for gi in graph_inputs
        ]
        ACCEPTED_VALUES = [
            f'({", ".join(gi.enum_options)})' if gi.enum_options else "ANY"
            for gi in graph_inputs
        ]
        VALUES = [
            (
                str(process_composite(gi.value))
                if gi.name in composite_inputs
                else str(gi.value) if gi.value is not None else ""
            )
            for gi in graph_inputs
        ]
        DESCRIPTIONS = [gi.description for gi in graph_inputs]

        NAMES_WIDTH = (
            max(8, min(int(TERMINAL_WIDTH * 0.3), max([len(name) for name in NAMES])))
            + 4
        )
        DATATYPES_WIDTH = (
            max(8, min(int(TERMINAL_WIDTH * 0.3), max([len(dt) for dt in DATATYPES])))
            + 4
        )
        ACCEPTED_VALUES_WIDTH = (
            max(
                26,
                min(
                    int(TERMINAL_WIDTH * 0.3), max([len(av) for av in ACCEPTED_VALUES])
                ),
            )
            + 4
        )
        VALUES_WIDTH = (
            max(8, min(int(TERMINAL_WIDTH * 0.3), max([len(val) for val in VALUES])))
            + 4
        )
        DESCRIPTION_WIDTH = (
            TERMINAL_WIDTH
            - NAMES_WIDTH
            - DATATYPES_WIDTH
            - VALUES_WIDTH
            - ACCEPTED_VALUES_WIDTH
        )

        print_table(
            titles=[
                "GRAPH-INPUT",
                "DATATYPE",
                "VALUE",
                "ACCEPTED-VALUES",
                "DESCRIPTION",
            ],
            rows=[
                (NAMES[i], DATATYPES[i], VALUES[i], ACCEPTED_VALUES[i], DESCRIPTIONS[i])
                for i in range(len(graph_inputs))
            ],
            widths=[
                NAMES_WIDTH,
                DATATYPES_WIDTH,
                VALUES_WIDTH,
                ACCEPTED_VALUES_WIDTH,
                DESCRIPTION_WIDTH,
            ],
        )
        print()

    if mode == "run" and not FILE.value and os.path.isdir(ROOT.value):
        # Print available files
        gx_files: typing.List[typing.Tuple[str, str]] = []
        registry = GraphRegistry(root=ROOT.value, cache_files=False)
        for root, _, files in os.walk(str(ROOT.value)):
            for file in files:
                if not file.lower().endswith(FILE_EXTENSION):
                    continue
                abs_path = os.path.abspath(os.path.join(root, file))
                gx_path = abs_path[len(os.path.abspath(ROOT.value)) :].lstrip(os.sep)
                graph_file = registry.load_graph_file(gx_path, is_cli=True)
                if not graph_file.is_executable():
                    continue
                gx_files.append((gx_path, graph_file.file.get("description", "")))

        min_width = (
            min(int(TERMINAL_WIDTH * 0.5), max([len(f[0]) for f in gx_files]))
            if gx_files
            else int(TERMINAL_WIDTH * 0.5)
        )
        FILES_WIDTH = max(8, min_width) + 4
        DESCRIPTION_WIDTH = TERMINAL_WIDTH - FILES_WIDTH

        print()
        print_table(
            titles=["FILE", "DESCRIPTION"],
            rows=gx_files,
            widths=[FILES_WIDTH, DESCRIPTION_WIDTH],
        )
        print()

    sys.exit(1 if errors else 0)


def load_arguments(
    args: typing.List[Argument], cli_values: typing.List[str]
) -> typing.Tuple[typing.List[str], typing.List[str]]:
    """
    Load arguments from the given CLI-provided values.

    :param args: The arguments to load. These will be populated in-place.
    :param cli_values: The CLI values to use to load the given arguments.

    :returns: A tuple:
    - Errors (strings) encountered while parsing.
    - CLI values remaining after loading arguments. These are the values from `cli_values` that were not used in any argument (neither a flag nor a flag value).
    """
    cli_values = [*cli_values]
    errors: typing.List[str] = []
    unused_cli_values: typing.List[str] = []
    while cli_values:
        current = cli_values.pop(0)
        found_arg = next(iter([arg for arg in args if current in arg.flags]), None)
        if found_arg is None:
            unused_cli_values.append(current)
            continue

        if found_arg.toggle:
            found_arg.value = True
            continue

        if found_arg.multiple:
            # Load values until the end or until there's a value without a ","
            values = []
            while cli_values:
                if len([arg for arg in args if cli_values[0] in arg.flags]):
                    break
                value = cli_values.pop(0)
                if value.endswith(","):
                    values.extend(value.split(",")[0:-1])
                elif "," in value:
                    values.extend(value.split(","))
                else:
                    values.append(value)
                    break

            if len(values) == 0:
                errors.append(f'Flag "{current}" was not provided with a value.')
                continue
            found_arg.value = values
        else:
            # Load the next value if it's not a flag
            if len(cli_values) == 0 or len(
                [arg for arg in args if cli_values[0] in arg.flags]
            ):
                errors.append(f'Flag "{current}" was not provided with a value.')
                continue
            found_arg.value = cli_values.pop(0)

    return errors, unused_cli_values


def load_graph_inputs(
    graph_inputs: typing.List[GraphInput], cli_values: typing.List[str]
) -> typing.Tuple[typing.List[str], typing.List[str]]:
    """
    Load graph inputs from the given CLI-provided values.

    :param graph_inputs: The graph inputs to load. These will be populated in-place.
    :param cli_values: The CLI values to use to load the given graph inputs.

    :returns: A tuple:
    - Errors (strings) encountered while parsing.
    - CLI values remaining after loading graph inputs. These are the values from `cli_values` that were not used in any graph input.
    """
    # flattens the cli values in to a list?
    cli_values = [*cli_values]
    errors: typing.List[str] = []
    unused_cli_values: typing.List[str] = []

    def parse_commas(s: str):
        """
        Remove commas, split, add individual values.
        Regex will ignore commas escaped with two backslashes and then a comma
        """
        return re.sub(r"(?<!\\),", " ", s).replace("\,", ",").split()  # type: ignore

    while cli_values:
        current = cli_values.pop(0)
        # test to see if the provided name for the graph input matches what is expected by the graph being executed
        found = next(
            iter([x for x in graph_inputs if current.startswith(x.name + "=")]), None
        )
        if not found:
            unused_cli_values.append(current)
            continue

        # Parse values for this graph input
        values: typing.List[str] = []
        current_split = current.split("=", maxsplit=1)
        # if there is exactly one equal sign in current and the length of the values assigned to graph_input is greater than zero
        if len(current_split) == 2 and len(current_split[1]):
            if found.is_list:
                elements = parse_commas(current_split[1])
                for e in elements:
                    values.append(e)
            else:
                values.append(current_split[1])

        # Keep parsing values if we need to
        max_values = len(cli_values) + len(values) if found.is_list else 1
        while cli_values and len(values) < max_values:
            if any([cli_values[0].startswith(x.name + "=") for x in graph_inputs]):
                break
            if found.is_list:
                elements = parse_commas(cli_values.pop(0))
                for e in elements:
                    values.append(e)
            else:
                values.append(cli_values.pop(0))

        # Save the values
        if len(values) == 0 and not found.is_list:
            errors.append(f'Graph Input "{found.name}" was not provided with a value.')
            continue

        if len(values) > 1 and not found.is_list:
            errors.append(
                f'Graph Input "{found.name}" was provided with too many values ({len(values)} provided when only 1 is expected).'
            )
            continue

        processed_values = []
        for value in values:

            if found.enum_options:
                # Find the case sensitive match
                match = next(
                    (en for en in found.enum_options if en.upper() == value.upper()),
                    None,
                )
                if not match:
                    errors.append(
                        f'Value "{value}" for Graph Input "{found.name}" is not ({", ".join(found.enum_options)}); match does not need to be case sensitive.'
                    )
                # We need t
                elif found.datatype == "String":
                    processed_values.append(match)

            elif found.datatype == "String":
                processed_values.append(value)
                continue

            elif found.datatype == "Number":
                try:
                    processed_values.append(int(value))
                    continue
                except ValueError:
                    pass

                try:
                    processed_values.append(float(value))
                    continue
                except ValueError:
                    pass

                errors.append(
                    f'Value "{value}" for Graph Input "{found.name}" is not a number.'
                )
                continue

            elif found.datatype == "Boolean":
                if value.lower() not in [
                    "true",
                    "false",
                    "t",
                    "f",
                    "0",
                    "1",
                    "yes",
                    "no",
                ]:
                    errors.append(
                        f'Value "{value}" for Graph Input "{found.name}" is not a boolean (True/False, T/F, Yes/No, 1/0).'
                    )
                    continue
                processed_values.append(
                    value.lower() == "true"
                    or value.lower() == "t"
                    or value.lower() == "1"
                    or value.lower() == "yes"
                )
                continue
        
        if type(found.value)==dict:
            if found.is_list:
                found.value['value'] = processed_values
            elif len(processed_values):
                found.value['value'] = processed_values[0]
        else:
            if found.is_list:
                found.value = processed_values
            elif len(processed_values):
                found.value = processed_values[0]

    return errors, unused_cli_values


def get_vault_password(pass_path: str):
    """
    Loads the vault password from the provided path
    :pass_path: the path to the file containing the vault password

    :returns: a tuple of: (vault password as a string or None, Error message as a string or None)
    """
    p = None
    if not os.path.exists(pass_path):
        return (None, f"Path provided for --passwordPath does not exist: {pass_path}")
    if not os.path.isfile(pass_path):
        return (None, f"Path provided for --passwordPath is not a file: {pass_path}")
    with open(pass_path, "r") as f:
        p = f.readline().replace("\n", "").replace("\r", "")
    if len(p) <= 0:
        return (
            None,
            f"Path provided for --passwordPath does not have a plaintext string on the first line of the file: {pass_path}",
        )
    return (p, None)


def decrypt_vault_password_prompt(
    encrypted_string: str, prompt_msg: typing.Optional[str] = None
):
    """
    Prompts the user to enter the vault password required to decrypt the provided string. Will loop several times before throwing an exception.
    :param encrypted_string: the encrypted string that needs to be decrypted

    :raises Exception: when the number of retries is exceeded for password input
    :returns: a tuple of: (the decrypted string, the password used to decrypt the string)
    """
    attempts = 0
    max_attempts = 3
    msg = (
        prompt_msg if prompt_msg else "Enter the password used to encrypt this secret: "
    )
    while True:
        try:
            password = getpass(msg)
            decrypted = vault.decryptSecret(encrypted_string, password)
            return (decrypted, password)
        except InvalidToken:
            attempts += 1
            if attempts < max_attempts:
                print(
                    f"The password was incorrect. Please try again. This is attempt {attempts}.",
                    flush=True,
                )
            else:
                raise Exception(
                    f"You've incorrectly entered the password {max_attempts} times"
                )


#########################
# Parse
#########################
args = sys.argv[1:]
load_arguments([HELP], args)
if len(args) == 0:
    print_help_and_exit(
        mode=None,
        args=[HELP],
        graph_inputs=[],
        errors=[] if HELP.value else ["No mode specified."],
    )

DEFAULT_CONFIG_FILEPATH = os.path.join(
    os.path.expanduser(os.getcwd()), "graphex-config.yml"
)

# Get the mode
MODE = args.pop(0)

# Handle serve
if MODE == "serve":
    SERVE_ARGUMENTS = [
        PLUGINS,
        CONFIG,
        ROOT,
        PORT,
        HELP,
        VERBOSE_ERRORS,
        SSL_CERTIFICATES,
        PASSWORD_PATH,
        INVENTORY,
        LOG_ROLLOVER
    ]
    errors, args = load_arguments(SERVE_ARGUMENTS, args)
    if len(args) > 0:
        errors.append(f"Unrecognized/extraneous values: {str(args)[1:-1]}")

    # Load the config
    config: typing.Optional[GraphConfig] = None

    if CONFIG.value:
        # A config file was specified, use that one
        try:
            config = GraphConfig(CONFIG.value)
        except Exception as e:
            errors.append(str(e))
            if VERBOSE_ERRORS:
                raise e
    else:
        # A config file was not specified, look for the default one
        try:
            config = GraphConfig(DEFAULT_CONFIG_FILEPATH)
        except Exception:
            pass

    # Use the config to populate arguments as needed
    if config and not PLUGINS.value:
        PLUGINS.value = config.contents["plugins"]

    # Stop here if the help menu was requested
    if HELP.value:
        print_help_and_exit(mode=MODE, args=SERVE_ARGUMENTS, graph_inputs=[], errors=[])

    if not ROOT.value:
        ROOT.value = (
            os.path.abspath(os.path.expanduser(config.contents["root"]))
            if config and config.contents["root"]
            else "./"
        )

    # Validate arguments
    if not os.path.isdir(ROOT.value):
        errors.append(
            f'Provided root directory "{ROOT.value}" is not a valid directory.'
        )

    try:
        PORT.value = int(PORT.value)
        assert PORT.value > 0 and PORT.value <= 65535
    except Exception:
        errors.append(f"{PORT.value} is not a valid port.")
        if re.match(r"[^0-9]", PORT.value, re.MULTILINE):
            raise Exception(
                "Non-numeric characters provided to the --port flag (-p). Did you mean to provide the vault password path (-pf)?"
            )

    if PASSWORD_PATH.value == None and config:
        PASSWORD_PATH.value = config.contents["vault_password_path"]

    if PASSWORD_PATH.value:
        PASSWORD_PATH.value = os.path.expanduser(PASSWORD_PATH.value)

    vault_password = None
    if PASSWORD_PATH.value:
        vault_password, error_msg = get_vault_password(PASSWORD_PATH.value)
        if error_msg:
            errors.append(error_msg)
    elif config and config.has_secrets():
        test_decrypted_string, vault_password = decrypt_vault_password_prompt(
            next(iter(config.get_all_encrypted_secrets().values())),
            prompt_msg="Enter the password used to encrypt all secrets in the configuration file: ",
        )

    # Setup the registry
    registry = GraphRegistry(
        root=ROOT.value, cache_files=False, verbose_errors=VERBOSE_ERRORS.value
    )
    try:
        registry.register_all(plugins=PLUGINS.value or [], log=True)
    except Exception as e:
        errors.append(str(e))
        if VERBOSE_ERRORS:
            raise e

    inv: typing.Optional[GraphInventory] = None

    if INVENTORY.value == None and config:
        INVENTORY.value = config.contents["inventory_path"]

    if INVENTORY.value:
        try:
            inv = GraphInventory(INVENTORY.value, registry)
            inv.create_content_nodes(auto_register=True, print_registered_amount=True)
        except Exception as e:
            errors.append(str(e))
            if VERBOSE_ERRORS:
                raise e

    if errors:
        print_help_and_exit(
            mode=MODE, args=SERVE_ARGUMENTS, graph_inputs=[], errors=errors
        )

    # See if the flag for SSL certs was provided on the command line when serving the server
    ssl_certs_path = SSL_CERTIFICATES.value
    # if it wasn't provided, assign it to the value given to it in the config file (which could still be none)
    if ssl_certs_path == None and config:
        ssl_certs_path = config.contents["ssl_certificates_path"]
    # if a value was found for either of the above assignments, check that the path exists and contains the proper cert filenames
    if ssl_certs_path:
        ssl_certs_path = os.path.abspath(os.path.expanduser(ssl_certs_path))
        print(f"Searching for and using SSL Certficates at path: {ssl_certs_path}")
        if not os.path.exists(ssl_certs_path):
            errors.append(f"Path to SSL certificates: {ssl_certs_path} doesn't exist!")
        else:
            cert_pem_found = False
            key_pem_found = False
            for f in os.listdir(ssl_certs_path):
                f = str(f).strip().lower()
                if f == "cert.pem":
                    cert_pem_found = True
                elif f == "key.pem":
                    key_pem_found = True
            if not cert_pem_found:
                errors.append(
                    f"Certificate file for SSL with name: 'cert.pem' not found in provided SSL Certificate directory: {ssl_certs_path}"
                )
            if not key_pem_found:
                errors.append(
                    f"Certificate file for SSL with name: 'key.pem' not found in provided SSL Certificate directory: {ssl_certs_path}"
                )
    # else: server will generate new certs using pyopenssl when ssl_certs_path is 'None'

    if errors:
        print_help_and_exit(
            mode=MODE, args=SERVE_ARGUMENTS, graph_inputs=[], errors=errors
        )

    # Handle the log rollover precendence
    log_rollover_amount: int = int(LOG_ROLLOVER.value)
    if config and config.contents["log_rollover_amount"]:
        log_rollover_amount = int(config.contents["log_rollover_amount"])

    # Start the server
    if config:
        print(f"Using configuration file from: {config.path}")
    server = GraphServer(
        registry=registry,
        config=config,
        ssl_certs_path=ssl_certs_path,
        vault_password=vault_password,
        inventory=inv,
        log_rollover_amount=log_rollover_amount
    )
    server.start(port=PORT.value)

    sys.exit(0)


if MODE == "run":
    RUN_ARGUMENTS = [
        FILE,
        PLUGINS,
        CONFIG,
        ROOT,
        VERBOSE,
        AZURE_MODE,
        HELP,
        VERBOSE_ERRORS,
        VALIDATE_ONLY,
        SHOW_INPUTS,
        PASSWORD_PATH,
        INVENTORY
    ]
    errors, args = load_arguments(RUN_ARGUMENTS, args)

    # Load the config
    config: typing.Optional[GraphConfig] = None

    # Set this variable to None to prevent unbound error in other exceptions
    config_graph_input_values = None

    if CONFIG.value:
        # A config file was specified, use that one
        try:
            config = GraphConfig(CONFIG.value)
        except Exception as e:
            errors.append(str(e))
            if VERBOSE_ERRORS:
                raise e
    else:
        # A config file was not specified, look for the default one
        try:
            config = GraphConfig(DEFAULT_CONFIG_FILEPATH)
        except Exception:
            pass

    # Use the config to populate arguments as needed
    if config and not PLUGINS.value:
        PLUGINS.value = config.contents["plugins"]

    if PASSWORD_PATH.value == None and config:
        PASSWORD_PATH.value = config.contents["vault_password_path"]

    if PASSWORD_PATH.value:
        PASSWORD_PATH.value = os.path.expanduser(PASSWORD_PATH.value)

    if not ROOT.value:
        ROOT.value = (
            os.path.abspath(os.path.expanduser(config.contents["root"]))
            if config and config.contents["root"]
            else "./"
        )

    # Validate arguments
    if not os.path.isdir(ROOT.value):
        errors.append(
            f'Provided root directory "{ROOT.value}" is not a valid directory.'
        )
    if not FILE.value:
        flags = ", ".join(FILE.flags)
        errors.append(f'Argument "{flags}" is required.')

    if errors:
        print_help_and_exit(
            mode=MODE,
            args=RUN_ARGUMENTS,
            graph_inputs=[],
            errors=[] if HELP.value else errors,
        )

    # Load graph file
    registry = GraphRegistry(root=ROOT.value)
    graph_inputs: typing.List[GraphInput] = []
    graph: typing.Optional[Graph] = None

    try:
        graph = registry.load_graph_file(FILE.value, is_cli=True)
    except Exception as e:
        errors.append(str(e))
        if VERBOSE_ERRORS:
            raise e

    if errors or graph is None:
        print_help_and_exit(
            mode=MODE,
            args=RUN_ARGUMENTS,
            graph_inputs=graph_inputs,
            errors=[] if HELP.value else errors,
        )

    # Setup graph inputs
    for input_metadata in graph.inputs:
        name = input_metadata["name"]
        description = input_metadata.get("description", "")
        datatype = input_metadata["datatype"]
        is_list = input_metadata.get("isList", False)
        default_value = input_metadata.get("defaultValue", None)
        is_password = input_metadata.get("isPassword", False)
        enum_options = input_metadata.get("enumOptions", None)

        graph_inputs.append(
            GraphInput(
                name=name,
                value=default_value,
                description=description,
                datatype=datatype,
                is_list=is_list,
                is_password=is_password,
                enum_options=enum_options,
                is_secret=False,
            )
        )

        def decryptConfigInput(
            value_metadata: GraphInputValueMetadata,
            config: GraphConfig,
        ):

            if "fromSecret" in value_metadata:
                value_metadata["value"] = decrypt_value(
                    value_metadata["fromSecret"], config
                )
                value_metadata.pop("fromSecret")  # remove the value
            else:
                for child in value_metadata["childValues"].values():
                    decryptConfigInput(child, config)

        def decrypt_value(name: str, config: GraphConfig) -> str:

            global PASSWORD

            # get the encrypted value from the config file
            encrypted_value = config.get_encrypted_secret(name)

            # handle prompting for the password or retreving the password from a path (if the password hasn't yet been collected)
            # then attempt the decryption of the vault secret
            # If a password is needed, we wil ask and remember it
            if PASSWORD:
                try:
                    return vault.decryptSecret(encrypted_value, PASSWORD)
                except InvalidToken:
                    raise Exception(
                        f"The password provided to decrypt the secret name: {name} ... is incorrect!"
                    )
            else:
                if PASSWORD_PATH.value:
                    PASSWORD, error_message = get_vault_password(PASSWORD_PATH.value)
                    if error_message:
                        raise Exception(error_message)
                    if PASSWORD is None:
                        raise Exception(
                            "ERROR: Failed to get vault password from provided password file. No specific error was provided by the code (value is 'None')."
                        )
                    try:
                        return vault.decryptSecret(encrypted_value, PASSWORD)
                    except InvalidToken:
                        raise Exception(
                            f"The password provided to decrypt the secret name: {name} ... is incorrect!"
                        )
                else:
                    decrypted, PASSWORD = decrypt_vault_password_prompt(
                        encrypted_value,
                        prompt_msg="Enter the password used to encrypt all secrets in the configuration file: ",
                    )
                    return decrypted

    # Set config file values
    if config:
        try:

            # scope will return a relative path without the leading './'
            scope = config.get_scope(ROOT.value, FILE.value)
            # easier to compare the scope to the relative path for root than the absolute one
            relative_root = os.path.relpath(ROOT.value)
            # the filename trying to be executed (no pathing)
            gx_filename = os.path.basename(FILE.value)
            # All scopes specified by the user in the configuration file
            all_config_scope_paths = config.get_graph_input_filepaths()
            # All filenames (no pathing) stripped from the paths provided in the configuration file
            all_config_scope_filenames = (
                config.get_graph_input_filenames_without_paths()
            )

            # check if the specified file is actually contained within root (a valid relative path wasn't really given here)
            # e.g. the relative bath is ./Graphs/Baseline/Baseline.gx but we were given -r Graphs/ and -f Baseline/Baseline.gx (see that -f isn't a real relpath, but the user assumed it would be appended to -r)
            if (
                scope not in all_config_scope_paths
                and gx_filename in all_config_scope_filenames
            ):
                # This adjust primarily handles if the root is one level away from where the config file specfies (e.g. assumption that root is joined with config file scope)
                if scope.startswith(relative_root):
                    scope = scope[scope.find(relative_root) + len(relative_root) :]
                    if scope.startswith("/"):
                        scope = scope[1:]

                    # The adjustment failed, see if the root is actually nested one layer too deep (e.g. root is in the same directory that the config file starts specifying from)
                    if scope not in all_config_scope_paths:
                        last_part_of_root = ROOT.value.split("/")[-1]
                        root_deeper_than_config_values = False
                        for fn in all_config_scope_paths:
                            if fn.startswith(last_part_of_root):
                                root_deeper_than_config_values = True
                                break
                        if root_deeper_than_config_values:
                            scope = last_part_of_root + "/" + scope
                    # endif scope not in config.get_graph_input_filenames(): [inner]

                    print(f"Adjusted GX filename scope to: {scope}")
                # endif scope.startswith(relative_root):
            # endif scope not in config.get_graph_input_filenames() [1]
            if (
                scope not in all_config_scope_paths
                and gx_filename in all_config_scope_filenames
            ):
                print(
                    f"\033[93m WARNING: Provided root value: '{os.path.abspath(ROOT.value)}' is unable to join with any scope provided by the configuration file ({CONFIG.value}).\033[0m",
                    "\033[93mThe specified scope in the configuration file must be reachable from the root path. The following scopes are specified in the configuration file:\n \033[0m",
                )
                for input_filename in all_config_scope_paths:
                    print(f"\033[93m {input_filename} \033[0m")
                print(
                    "\n \033[93m This warning means NO GRAPH INPUTS specified for a SPECIFIC GRAPH in the CONFIGURATION FILE will be loaded! \033[0m"
                )
            # endif scope not in config.get_graph_input_filenames() [2]
            config_graph_input_values = config.get_graph_inputs(
                [gi.name for gi in graph_inputs], scope=scope
            )

            encrypted_secret_values = config.get_all_encrypted_secrets()
            password_value = None
            for graph_input in graph_inputs:
                # if the graph input is a normal graph input and has a value assigned from the config file:
                if (
                    graph_input.name in config_graph_input_values
                    and not graph_input.is_secret
                ):
                    graph_input.value = config_graph_input_values[graph_input.name]
                    # decrypt an secret values if fromSecret was used
                    decryptConfigInput(graph_input.value, config)
                # else if the graph input is a secret and has a value assigned from the 'secrets' section of the config file:
                elif (
                    graph_input.name in encrypted_secret_values
                    and graph_input.datatype == "String"
                ):
                    # update this graph input with the decrypted secret value
                    graph_input.value = decrypt_value(graph_input.name, config)
        except Exception as e:
            errors.append(str(e))

    if errors:
        print_help_and_exit(
            mode=MODE, args=RUN_ARGUMENTS, graph_inputs=graph_inputs, errors=errors
        )

    # Load graph inputs
    errors, args = load_graph_inputs(graph_inputs, args)
    if len(args) > 0:
        errors.append(f"Unrecognized/extraneous values: {str(args)[1:-1]}")

    # Stop here if the help menu was requested
    if HELP.value:
        print_help_and_exit(
            mode=MODE,
            args=RUN_ARGUMENTS,
            graph_inputs=graph_inputs,
            errors=[],
            composite_inputs=(
                [gi.name for gi in graph_inputs if gi.name in config_graph_input_values]
                if config_graph_input_values
                else []
            ),
        )

    if errors:
        print_help_and_exit(
            mode=MODE,
            args=RUN_ARGUMENTS,
            graph_inputs=graph_inputs,
            errors=errors,
            composite_inputs=(
                [gi.name for gi in graph_inputs if gi.name in config_graph_input_values]
                if config_graph_input_values
                else []
            ),
        )

    # Run
    runtime: GraphRuntime
    try:
        registry.register_all(plugins=PLUGINS.value or [], log=bool(VERBOSE.value))

        # Ensure all graph inputs have a value
        for gi in graph_inputs:
            if (
                gi.datatype not in ["String", "Number", "Boolean"]
                and gi.datatype not in registry.composite_inputs
            ):
                errors.append(
                    f"This graph cannot be directly executed from the CLI (unsupported datatype '{gi.datatype}' for graph input '{gi.name}')"
                )
            elif gi.value is None:
                errors.append(
                    f'Required value not provided for graph input "{gi.name}".'
                )

        inv: typing.Optional[GraphInventory] = None

        if INVENTORY.value == None and config:
            INVENTORY.value = config.contents["inventory_path"]

        if INVENTORY.value:
            try:
                inv = GraphInventory(INVENTORY.value, registry, print_loading_msg=False)
                inv.create_content_nodes(auto_register=True, print_registered_amount=False)
            except Exception as e:
                errors.append(str(e))
                if VERBOSE_ERRORS:
                    raise e

        logger = GraphexLogger(
            level="DEBUG" if VERBOSE.value else "INFO",
            azure_integration=AZURE_MODE.value,
        )

        if errors:
            print_help_and_exit(
                mode=MODE, args=RUN_ARGUMENTS, graph_inputs=graph_inputs, errors=errors
            )

        runtime = GraphRuntime(
            graph,
            logger=logger,
            input_values={gi.name: gi.value for gi in graph_inputs},
            azure_integration=AZURE_MODE.value,
            verbose_errors=VERBOSE_ERRORS.value,
            print_graph_inputs=SHOW_INPUTS.value,
            composite_inputs=(
                [gi.name for gi in graph_inputs if gi.name in config_graph_input_values]
                if config_graph_input_values
                else []
            ),
        )
    except Exception as e:
        if VERBOSE_ERRORS:
            raise e
        print_help_and_exit(
            mode=MODE,
            args=RUN_ARGUMENTS,
            graph_inputs=graph_inputs,
            errors=[str(e)],
            composite_inputs=(
                [gi.name for gi in graph_inputs if gi.name in config_graph_input_values]
                if config_graph_input_values
                else []
            ),
        )

    if VALIDATE_ONLY.value:
        runtime.validate()
        print(f"No pre-execution errors found in graph file: {FILE.value}")
        sys.exit(0)
    else:
        errors = runtime.run()
        for err in errors:
            logger.critical(str(err))
        sys.exit(1 if errors else 0)

if MODE == "vault":
    # define which arguments (top this file) are allowed for this mode
    VAULT_ARGUMENTS = [
        CONFIG,
        ENCRYPT,
        DECRYPT,
        REMOVE,
        NAME_OF_SECRET,
        PASSWORD_PATH,
        OVERWRITE,
        HASHED_SECRET,
        HIDE_SECRET_INPUT,
        HELP,
    ]
    errors, args = load_arguments(VAULT_ARGUMENTS, args)
    if len(args) > 0:
        errors.append(f"Unrecognized/extraneous values: {str(args)[1:-1]}")

    if HELP.value:
        print_help_and_exit(mode=MODE, args=VAULT_ARGUMENTS, graph_inputs=[], errors=[])

    ## handle user input verification
    if not ENCRYPT.value and not DECRYPT.value and not REMOVE.value:
        errors.append(
            "One of the following must be specified: --encrypt, --decrypt, or --remove !"
        )

    if (
        (ENCRYPT.value and DECRYPT.value)
        or (ENCRYPT.value and REMOVE.value)
        or (DECRYPT.value and REMOVE.value)
    ):
        errors.append(
            f"Only one of --encrypt or --decrypt or --remove arguments may be provided at once."
        )

    if CONFIG.value and HASHED_SECRET.value:
        errors.append(f"Only one of --config or --hashedSecret may be provided.")

    secret_name = NAME_OF_SECRET.value
    if ((ENCRYPT.value and CONFIG.value) or REMOVE.value) and not secret_name:
        errors.append(
            f"No value provided for the name of the secret to encrypt/remove (--name)!"
        )

    password_path = PASSWORD_PATH.value
    password_value = None
    if password_path:
        password_value, error_message = get_vault_password(password_path)
        if error_message:
            errors.append(error_message)

    config_path = CONFIG.value
    config_object = None
    if not CONFIG.value:
        try:
            config_object = GraphConfig(DEFAULT_CONFIG_FILEPATH)
            config_path = DEFAULT_CONFIG_FILEPATH
            print(
                f"Using default configuration file found at path: {DEFAULT_CONFIG_FILEPATH}",
                flush=True,
            )
        except Exception:
            config_path = None
            config_object = None
    if config_path:
        if not os.path.exists(config_path):
            errors.append(f"Path provided for --config does not exist: {config_path}")
        if not os.path.isfile(config_path):
            errors.append(f"Path provided for --config is not a file: {config_path}")
        if not config_object:
            config_object = GraphConfig(config_path)
    else:
        print(
            f"\033[93mWARNING: No configuration file was provided (--config).\033[0m Operations will be output to the terminal instead of a file."
        )

    if DECRYPT.value:
        if not config_object and not HASHED_SECRET.value:
            errors.append(
                f"One of --config or --hashedSecret must be provided alongside --decrypt"
            )

    if REMOVE.value and not config_object:
        errors.append(
            f"You specified --remove but did not give a path to a --config file to remove the secret from!"
        )
    ##

    # Print any found errors and exit this mode (if any)
    if errors:
        print_help_and_exit(
            mode=MODE, args=VAULT_ARGUMENTS, graph_inputs=[], errors=errors
        )

    ### Perform the operation desired by the user
    def determinePassword():
        """
        Determine the password to use for hashing the secret.
        Will not return unless a password is either found from file or entered twice correctly
        """
        p = ""
        if password_value:
            return password_value
        else:
            attempt1 = "1"
            attempt2 = "2"
            while attempt1 != attempt2:
                attempt1 = getpass("Enter the password to encrypt this secret with: ")
                attempt2 = getpass("Enter the password again: ")
                if attempt1 != attempt2:
                    print("Passwords did not match. Try again. ", flush=True)
            p = attempt1
        return p

    def promptSecretValue():
        """
        Prompts the user to enter the secret value they want to encrypt.
        """
        s = ""
        if HIDE_SECRET_INPUT.value:
            attempt1 = "1"
            attempt2 = "2"
            while attempt1 != attempt2:
                attempt1 = getpass(
                    f"Enter the secret value you want to encrypt under the name '{secret_name}': "
                )
                attempt2 = getpass("Enter the secret value again: ")
                if attempt1 != attempt2:
                    print("Secret value inputs did not match. Try again. ", flush=True)
            s = attempt1
        else:
            s = input("Enter the secret value you want to encrypt: ")
        return s

    if ENCRYPT.value:
        if config_object and config_object.has_secret_name(secret_name):
            if OVERWRITE.value:
                print(
                    f"\033[93mWARNING: Configuration file already has a stored secret with the name: {secret_name}\033[0m ... Storing a new value will overwrite the existing one (the overwrite flag was provided)."
                )
            if not OVERWRITE.value:
                raise Exception(
                    f"ERROR: Configuration file already has a stored secret with the name: {secret_name} ... Please remove the existing name or provide the overwrite flag: --overwrite"
                )

        # get the plaintext secret the user wants to encrypt
        # this will prompt either a normal input or a password input depending on the provided flags
        plaintext_secret_value = promptSecretValue()
        # grab the password either from the terminal or from a file if the file was provided
        # this will be reused further down in the loop if the user wants to continue encrypting
        password = determinePassword()
        # encrypt the string
        encrypted = vault.encryptString(plaintext_secret_value, password)

        # either store the string in the config or print the encrypted value to screen
        if config_object:
            config_object.add_secret(secret_name, encrypted)
            config_object.export_and_write_to_disk()
            print(
                f"Successfully encrypted and stored secret with name: {secret_name} to the config file located at: {config_path}"
            )
            if password_value:
                print(f"Encrypted using password from file at path: {password_path}")
        else:
            print(f"\nThe encrypted secret is:\n{encrypted}")

        # loop until the user wants to stop encrypting values
        response = ""
        # continue to prompt the user until they enter something that starts with y or n
        while not response.lower().strip().startswith(
            "y"
        ) and not response.lower().strip().startswith("n"):
            response = input(
                "Would you like to encrypt another secret with the same password? (y/n): "
            )
            # if the secret already exists in the config file: we will set this variable to True and try this loop again
            try_again = False
            # handle when the user says y...
            if response.lower().strip().startswith("y"):
                # we need to ask what the new name of the secret should be (normally -n argument)
                secret_name = ""
                while secret_name.strip() == "":
                    secret_name = input(
                        "What name do you want to give to this new secret?: "
                    )
                    if config_object and config_object.has_secret_name(secret_name):
                        # it would be annoying to kick the user out if the secret name already existing in the config file at this point
                        # ask if they want to overwrite and if they dont: return them to the original loop
                        if OVERWRITE.value:
                            print(
                                f"\033[93mWARNING: Configuration file already has a stored secret with the name: {secret_name}\033[0m ... Storing a new value will overwrite the existing one (the overwrite flag was provided)."
                            )
                        else:
                            overwrite_response = ""
                            while not overwrite_response.lower().strip().startswith(
                                "y"
                            ) and not overwrite_response.lower().strip().startswith(
                                "n"
                            ):
                                overwrite_response = input(
                                    f"Do you want to overwrite the secret that already exists with the name: '{secret_name}'?: "
                                )
                            if overwrite_response.lower().strip().startswith("n"):
                                try_again = True
                # end while (inner)
                # prompt the user again if the secret name would be overwritten and they chose not to overwrite
                if try_again:
                    response = ""
                    continue
                # perform the encryption and storage or logging
                encrypted = vault.encryptString(promptSecretValue(), password)
                if config_object:
                    config_object.add_secret(secret_name, encrypted)
                    config_object.export_and_write_to_disk()
                    print(
                        f"Successfully encrypted and stored secret with name: {secret_name} to the config file located at: {config_path}"
                    )
                    if password_value:
                        print(
                            f"Encrypted using password from file at path: {password_path}"
                        )
                else:
                    print(f"\nThe encrypted secret is:\n{encrypted}")
                # reset the loop
                response = ""
            # end if
        # end while (outer)
    elif REMOVE.value:
        if not config_object:
            raise Exception(
                f"ERROR: Remove was specified but no configuration file provided to remove from!"
            )
        if not config_object.has_secret_name(secret_name):
            print(
                f"\033[93mWARNING: Configuration file does not have a secret with the name: {secret_name} ... Program is exiting without removing anything.\033[0m"
            )
        else:
            encrypted = config_object.remove_secret(secret_name)
            if encrypted != None:
                config_object.export_and_write_to_disk()
            print(
                f"Successfully removed secret with name: {secret_name} ... from the configuration file located at: {config_path}"
            )
    elif DECRYPT.value:
        encrypted = ""
        if config_object:
            if not config_object.has_secret_name(secret_name):
                raise Exception(
                    f"ERROR: Configuration file does not have a secret stored under the name: {secret_name}"
                )
            encrypted = config_object.get_encrypted_secret(secret_name)
        elif HASHED_SECRET.value:
            encrypted = HASHED_SECRET.value
        else:
            raise Exception(
                "ERROR: Attempted DECRYPT but neither a config nor a HASH were provided!"
            )

        if password_value:
            try:
                decrypted = vault.decryptSecret(encrypted, password_value)
            except InvalidToken:
                raise Exception(
                    f"The password provided from the file path: {password_path} is incorrect!"
                )
        else:
            decrypted = decrypt_vault_password_prompt(encrypted)[0]
        # end while True
        print(f"\nThe decrypted secret value is:\n{decrypted}")
    ###

    # Cleanly exit this mode and the program itself
    sys.exit(0)

# The user didn't specify a mode that have programming logic for in this file
print_help_and_exit(
    mode=MODE,
    args=[HELP],
    graph_inputs=[],
    errors=[] if HELP.value else [f'Unrecognized mode "{MODE}".'],
)
