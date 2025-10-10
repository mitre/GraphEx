import typing

import yaml
from yaml import Dumper
from yaml import SafeLoader as YAMLLoader

try:
    from yaml import CDumper as Dumper
    from yaml import CSafeLoader as YAMLLoader
except ImportError:
    print(
        "\u001b[33mWarning: The PyYAML 'CLoader' could not be imported. To get better YAML loading performance, install the 'libyaml' package (or equivalent; e.g. 'apt-get install libyaml-dev').\u001b[0m"
    )


def parse_yml(ymlstr: str):
    """
    Parse a YAML string into a Python object.

    :param ymlstr: The YAML string.

    :return: The Python equivalent of the YAML.
    """
    return yaml.load(ymlstr, Loader=YAMLLoader)


def dump_yml(obj: typing.Any) -> str:
    """
    Dump a Python object to YAML.

    :param obj: The object.

    :return: The YAML string equivalent for the Python object.
    """
    return yaml.dump(obj, default_flow_style=False, Dumper=Dumper)


def node_id_from_file_content(
    lines: typing.List[str], line_number: int, stop_if_empty_line: bool = False
):
    """
    Searches a string for the line in the original YAML file containing the ID of the node
    :param file_content_lines: The content of the file to search
    :param line_number: the line number to search around in the file

    :returns: the ID of the node in the file or the empty string if not found
    """

    node_id = ""
    search_key = "id: "

    # the index is always one less than the line number
    line_index = line_number - 1

    if stop_if_empty_line and lines[line_index].replace("\n", "").strip() == "":
        return ""

    if line_index < 0:
        line_index = line_number
    # first check if the line itself contains the ID
    provided_line = lines[line_index]
    if provided_line.strip() == "":
        line_index = line_number
        provided_line = lines[line_index]
    if provided_line.strip().startswith(search_key):
        node_id = extract_node_id_from_line(provided_line)
    # next check if we are on the "first line" of the node information (the ID line is the second one)
    elif (
        provided_line.strip().startswith("- name: ")
        and line_index + 1 < len(lines)
        and lines[line_index + 1].strip().startswith(search_key)
    ):
        node_id = extract_node_id_from_line(lines[line_index + 1])
    # else we will search backwards until empty string or match
    else:
        previous_index = line_index - 1
        while previous_index > 0 and lines[previous_index].strip() != "":
            previous_line = lines[previous_index]
            if previous_line.strip().startswith(search_key):
                node_id = extract_node_id_from_line(previous_line)
                break
            previous_index = previous_index - 1
        # end while
    # end else
    return node_id


def find_graph_inputs_line_number(file_content_lines: typing.List[str]):
    """
    Searches the provided list of file contents backwards to find the line number where the graph inputs start.
    :param file_content_lines: the contents of the file to search (broken up into individual lines)

    :returns: The line number where the graph inputs key is found or -1 if the key isn't found
    """
    key_name: str = "inputs:"
    # step backwards in the file contents to find the input key
    last_index = len(file_content_lines) - 1
    for i in range(last_index, 0, -1):
        line = file_content_lines[i].strip().lower().strip("\r").strip("\n")
        next_lines: typing.List[str] = [
            file_content_lines[i - 1].strip().lower().strip("\r").strip("\n"),
            file_content_lines[i - 2].strip().lower().strip("\r").strip("\n"),
        ]
        if line == key_name:
            if any("xy:" in element for element in next_lines):
                continue
            return i + 1
    # there are no graph inputs in the file
    return -1


def find_graph_input_data_from_line_number(
    file_content_lines: typing.List[str], line_number: int
) -> typing.Tuple[str, str]:
    """
    Searchs through the provided file contents line by line until it finds the name of the graph input associated with the line number.
    Starts its search at the provided line_number.

    :param file_content_lines: the contents of the file to search
    :param line_number: the line number to start searching from

    :returns: tuple of (the name of the graph input associated with the line number in the file, the yaml block for this graph input). An empty string is returned for one of the tuple values if the search failed.
    """
    # setup variables
    key_name: str = "- name: "
    line_index: int = line_number
    provided_line: str = (
        file_content_lines[line_index].replace("\r", "").replace("\n", "").strip()
    )

    # values to populate and return
    graph_input_name: str = ""
    yaml_block: str = ""

    # loop through the lines backwards until we reach a gap in the file
    # this typically denotes the end of an individual graph input
    while provided_line != "":
        # here we check if the line matches the key_name and that the previous line is either blank or the key "inputs:"
        if provided_line.strip().startswith(key_name) and (
            file_content_lines[line_index - 1]
            .replace("\r", "")
            .replace("\n", "")
            .strip()
            == ""
            or file_content_lines[line_index - 1].lower().startswith("inputs:")
        ):
            # this is a match, record the name
            graph_input_name = extract_graph_input_name_from_line(provided_line)
            # record the yaml block
            while provided_line != "":
                yaml_block += file_content_lines[line_index] + "\n"  # keep spacing
                # stop early if there is no newline at the end of the file
                if line_index + 1 >= len(file_content_lines):
                    break
                line_index += 1
                provided_line = (
                    file_content_lines[line_index]
                    .replace("\r", "")
                    .replace("\n", "")
                    .strip()
                )
            return (graph_input_name, yaml_block)
        line_index -= 1
        provided_line = (
            file_content_lines[line_index].replace("\r", "").replace("\n", "").strip()
        )
    # we failed to find what we were searching for
    # this ideally shouldn't happen unless the provided line number is somewhere outside where the graph inputs start
    # (always the last items in the file)
    return (graph_input_name, yaml_block)


def find_yaml_blocks_for_node_ids(
    file_content_lines: typing.List[str],
    node_ids: typing.Union[typing.List[str], typing.Set[str]],
) -> typing.Dict[str, str]:
    """
    Iterates through the provided file contents and collects the "yaml block" text corresponding to the provided ID in the list of node IDs.

    :param file_content_lines: the contents of the file to search
    :param node_ids: the list or set of node_ids you would like the yaml content for

    :return: a dictionary mapping node_id -> yaml block content
    """
    # this dictionary will contain a mapping of node_id -> yaml block in the file content
    node_id_to_content: typing.Dict[str, str] = {}
    # this prefix will be appended to the front of each node ID to match what the yaml file looks like
    search_key_prefix: str = "id: "
    # these will be the actual keys we compare when searching (as opposed to the node_ids variable in the function header)
    search_keys: typing.List[str] = []
    # to exit the loop earlier
    matches_found: int = 0

    # create the search keys to match on
    for node_id in node_ids:
        search_keys.append(search_key_prefix + node_id)

    # variable to track the current yaml block
    capture = ""
    # variable to hold the ID of the node currently being matched on
    found_id = ""
    # iterate through each line in the file content
    for line in file_content_lines:
        stripped_line = line.replace("\n", "").strip()
        # reset the capture and move on when the line becomes a "blank" line (empty string)
        if stripped_line == "":
            if found_id != "":
                node_id_to_content[found_id] = capture
                found_id = ""
                matches_found += 1
                # exit early if we find all our matches
                if matches_found >= len(search_keys):
                    break
            capture = ""
            continue
        # don't capture the 'nodes:' line
        if stripped_line == "nodes:":
            continue
        # start recording this text block
        capture += line
        # re-insert newlines if the were stripped previously
        if not capture.endswith("\n"):
            capture += "\n"
        # check if the current line matches any of the IDs we are looking for
        for k in search_keys:
            if k in line:
                found_id = k.split(search_key_prefix)[1].strip()
                break
        # end inner for each
    # end outer for each

    # at the end of the file its possible there isn't a blank line
    # finish saving the final node ID in this case
    if found_id != "":
        node_id_to_content[found_id] = capture

    return node_id_to_content


def find_graph_input_yml_by_name(
    graph_input_name: str, file_content_lines: typing.List[str], inputs_start_line: int
) -> str:
    """
    Returns the yaml block associated with a graph input by name.

    :param graph_input_name: the name of the graph input to search for
    :param file_content_lines: the contents of the file to search
    :param inputs_start_line: the line in which the 'inputs:' key first appears. If there is no 'inputs' key in the '.gx' file: then there is nothing to search (see find_graph_inputs_line_number(...) )

    :return: the entire yml block for the graph input with the provided name (as a string). Will return an empty string if the name doesn't exist in the file (underneath the 'inputs' key).
    """
    # setup variables
    key_name: str = "- name: "
    lines_length: int = len(file_content_lines)
    recording_lines: bool = False

    # remember that line_number is the index number + 1
    if inputs_start_line >= lines_length or inputs_start_line < 0:
        # there are no graph inputs in this file contents
        return ""

    # values to populate and return
    yaml_block: str = ""

    # remember that line_number is the index number + 1
    for line_number in range(inputs_start_line, lines_length):
        provided_line = (
            file_content_lines[line_number].replace("\r", "").replace("\n", "").strip()
        )
        if recording_lines:
            if provided_line == "":
                return yaml_block
            # else
            yaml_block += provided_line + "\n"
            continue
        elif (
            provided_line.strip().startswith(key_name)
            and extract_graph_input_name_from_line(provided_line) == graph_input_name
        ):
            recording_lines = True
            yaml_block += provided_line + "\n"
            continue

    # we failed to find a graph input with that name in the provided file contents
    return ""


def extract_graph_input_name_from_line(line_content: str):
    """
    Strips out the key 'name' from the provided line_content and returns just the name of the graph input.
    """
    return "".join(line_content.split())[len("- name: ") - 2 :]


def extract_node_id_from_line(line_content: str):
    """
    Strips out the key 'id' from the provided line_content and returns just the ID of the node
    """
    return "".join(line_content.split())[3:]


def extract_node_name_from_line(line_content: str):
    """
    Strips out the key 'name' from the provided line_content and returns just the name of the node
    """
    return line_content[line_content.find("- name: ") + len("- name: ") :].strip()


def node_name_from_file_content(
    lines: typing.List[str], line_number: int, stop_if_empty_line: bool = False
):
    """
    Searches a string for the line in the original YAML file containing the name of the node
    :param file_content_lines: The content of the file to search
    :param line_number: the line number to search around in the file

    :returns: the name of the node in the file or the empty string if not found
    """

    node_name = ""
    search_key = "  - name:"

    # the index is always one less than the line number
    line_index = line_number - 1

    if stop_if_empty_line and lines[line_index].replace("\n", "").strip() == "":
        return ""

    if line_index < 0:
        line_index = line_number
    # first check if the line itself contains the ID
    provided_line = lines[line_index]
    if provided_line.strip() == "":
        line_index = line_number
        provided_line = lines[line_index]
    if provided_line.startswith(search_key):
        node_name = extract_node_name_from_line(provided_line)
    # else we will search backwards until empty string or match
    else:
        previous_index = line_index - 1
        while previous_index > 0 and lines[previous_index].strip() != "":
            previous_line = lines[previous_index]
            if previous_line.startswith(search_key):
                node_name = extract_node_name_from_line(previous_line)
                break
            previous_index = previous_index - 1
        # end while
    # end else
    return node_name
