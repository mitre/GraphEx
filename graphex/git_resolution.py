import os
import typing

from git import Repo

from graphex import util

# this is always 12 characters long
GIT_MERGE_HEAD_MARKER = "<<<<<<<"
# not sure about these ones
GIT_MERGE_CENTER_SEP = "======="
GIT_MERGE_END_MARKER = ">>>>>>>"  # branch_name would follow these symbols


def git_diff_changed_lines(git_repo: Repo, other_branch_name: str, filepath: str):
    """
    Compares a single file from two different git branches using the 'git diff' command.

    :param git_repo: the git repo object to use to interface with git. Will use the 'active_branch' as one of the two branches
    :param other_branch_name: the name of the other branch to compare against
    :param filepath: the path to the file on the filesystem to diff

    :returns: None if there are no changes between the branches. A tuple of (original_lines_changed, new_file_lines_changed) otherwise. Each returned item in the tuple is a list of tuples containing the start and end lines as reported by git, e.g.: ([(1, 3)], [(1, 4)])
    """
    # Validate that the other branch we are trying to compare exists
    if other_branch_name not in [b.name for b in git_repo.branches]:
        raise Exception(f"No git branch exists locally with name: {other_branch_name}")

    # Validate that the file we are trying to diff exists
    # git will not inform you if the file doesn't exist!
    if not os.path.exists(filepath):
        raise Exception(f"No file exists on server with name: {filepath}")

    if not os.path.isfile(filepath):
        raise Exception(f"Is not a 'file': {filepath}")

    # the name of the current branch tracked by the repo object
    this_branch_name: str = git_repo.active_branch.name

    # compute the diff between the current branch and the other branch
    # return None if there are no changes between the branches
    diff_string: str = git_repo.git.diff(
        "--unified=0", this_branch_name + ".." + other_branch_name, "--", filepath
    )
    if not diff_string or diff_string.strip() == "":
        return None

    # at this point we need to find the line numbers associated with the diff
    # there isn't a built in git command for this: so we will have to parse the string ourselves
    original_file_lines_changed: typing.List[
        typing.Tuple[int, typing.Optional[int]]
    ] = []
    new_file_lines_changed: typing.List[typing.Tuple[int, typing.Optional[int]]] = []
    for line in diff_string.split("\n"):
        formatted_line = line.strip()
        if formatted_line.startswith("@@ "):
            # sometimes git doesn't start AND end with the '@' character, so we have to force the result to look that way:
            formatted_line = formatted_line[0 : formatted_line.rfind("@")]
            # formatted_line is something like this: @@ -1,3 +1,4 @@ |OR| @@ -1 +1 @@ (... OR @@ -3,3 +3 @@ ...etc.)
            chunks: typing.List[str] = formatted_line.strip("@").strip().split("+")
            # chunks: ["-1,3 ", "1,4"] |OR| ["-1 ", "1"]
            original_lines: typing.List[str] = chunks[0].strip().split(",")
            new_lines: typing.List[str] = chunks[1].strip().split(",")
            # original_lines: ["-1", "3"] new_lines: ["1", "4"] |OR| ["-1"] and ["1"]
            original_line_start = -1 * int(original_lines[0])
            original_line_end = (
                int(original_lines[1])
                if len(original_lines) > 1 and int(original_lines[1]) > 0
                else None
            )
            new_lines_start = int(new_lines[0])
            new_lines_end = (
                int(new_lines[1])
                if len(new_lines) > 1 and int(new_lines[1]) > 0
                else None
            )
            original_file_lines_changed.append((original_line_start, original_line_end))
            new_file_lines_changed.append((new_lines_start, new_lines_end))
    # end for

    return (original_file_lines_changed, new_file_lines_changed)


def git_show_file_on_branch(git_repo: Repo, branch_name: str, filepath: str) -> str:
    """
    Invokes 'git show' on the provided branch and filepath. Doesn't valid the inputs.
    :param git_repo: the git repo object to use to interface with git.
    :param branch_name: the name of the other branch to show the file for
    :param filepath: the path to the file on the filesystem to retreive from

    :returns: the contents of the file for the specified branch
    """
    return git_repo.git.show(branch_name + ":" + filepath)


def git_diff_changed_gx_files(git_repo: Repo, other_branch_name: str, filepath: str):
    """
    Gathers the IDs of all the nodes that are different between two git branches.
    Performs this by first calling 'git diff' to figure out the line numbers that are different between the branches.
    Gathers the contents of both files on their respective branches using 'git show'.
    For each changed line number: searches the content of the branch around the line number for a node ID.
    THIS FUNCTION IS SPECIFIC TO .GX FILES.

    :param git_repo: the git repo object to use to interface with git. Will use the 'active_branch' as one of the two branches
    :param other_branch_name: the name of the other branch to gather against
    :param filepath: the path to the file on the filesystem to search

    :returns: 'None' if there are no changes between the branches. Otherwise, a dictionary with the following keys: "changed_nodes_this_branch" (nodeIds set),
    "changed_nodes_other_branch" (nodeIds set),
    "changed_graph_inputs_this_branch" (names -> yml string dict),
    "changed_graph_inputs_other_branch" (names -> yml string dict),
    "graph_inputs_start_line_this_branch" (int for line number),
    "graph_inputs_start_line_other_branch" (int for line number),
    """
    compiled_results: typing.Dict[str, typing.Any] = {}

    changed_lines = git_diff_changed_lines(git_repo, other_branch_name, filepath)
    if changed_lines is None:
        return None

    # the name of the current branch tracked by the repo object
    this_branch_name: str = git_repo.active_branch.name

    if this_branch_name == other_branch_name:
        raise Exception(
            f"Error: trying to run a GX git diff between two branches with the same name!: {this_branch_name}"
        )

    # load the contents of the file on each branch and split the contents into lines
    this_branch_lines: typing.List[str] = git_show_file_on_branch(
        git_repo, this_branch_name, filepath
    ).split("\n")
    other_branch_lines: typing.List[str] = git_show_file_on_branch(
        git_repo, other_branch_name, filepath
    ).split("\n")

    # find out on which line the graph inputs start:
    this_branch_inputs_line_num: int = util.find_graph_inputs_line_number(
        this_branch_lines
    )
    other_branch_inputs_line_num: int = util.find_graph_inputs_line_number(
        other_branch_lines
    )

    # create a set that will contain the IDs of all the nodes that are changed on each branch
    this_branch_changed_nodes: typing.Set[str] = set()
    other_branch_changed_nodes: typing.Set[str] = set()

    def add_node_to_set(
        _set: typing.Set[str], _lines: typing.List[str], _line_number: int
    ) -> bool:
        """
        Adds a found node ID to the appropriate set if it isn't the empty string

        :returns: True if the node was added, False if the line was not associated with a particular node
        """
        node_id = util.node_id_from_file_content(
            _lines, _line_number, stop_if_empty_line=True
        )
        if node_id != "":
            _set.add(node_id)
            return True
        return False

    def find_matches(
        _changed_lines_list: typing.List[typing.Tuple[int, typing.Optional[int]]],
        _set: typing.Set[str],
        _lines: typing.List[str],
    ):
        """
        Steps through each changed line number and attempts to determine the nodeID of the the node that owns the matching line
        """
        for tuple_range in _changed_lines_list:
            start_index = tuple_range[0]
            end_index = tuple_range[1]
            if not end_index:
                add_node_to_set(_set, _lines, start_index)
            else:
                for i in range(start_index, end_index + 1):
                    add_node_to_set(_set, _lines, i)

    find_matches(changed_lines[0], this_branch_changed_nodes, this_branch_lines)
    find_matches(changed_lines[1], other_branch_changed_nodes, other_branch_lines)
    this_branch_changed_gi: typing.Dict[str, str] = find_changed_graph_inputs(
        this_branch_inputs_line_num, this_branch_lines, changed_lines[0]
    )
    other_branch_changed_gi: typing.Dict[str, str] = find_changed_graph_inputs(
        other_branch_inputs_line_num, other_branch_lines, changed_lines[1]
    )

    compiled_results["changed_nodes_this_branch"] = this_branch_changed_nodes
    compiled_results["changed_nodes_other_branch"] = other_branch_changed_nodes
    compiled_results["changed_graph_inputs_this_branch"] = this_branch_changed_gi
    compiled_results["changed_graph_inputs_other_branch"] = other_branch_changed_gi
    compiled_results["graph_inputs_start_line_this_branch"] = (
        this_branch_inputs_line_num
    )
    compiled_results["graph_inputs_start_line_other_branch"] = (
        other_branch_inputs_line_num
    )
    compiled_results["line_content_for_this_branch"] = this_branch_lines
    compiled_results["line_content_for_other_branch"] = other_branch_lines
    return compiled_results


def find_changed_graph_inputs(
    graph_inputs_line_number: int,
    file_content_lines: typing.List[str],
    changed_lines: typing.List[typing.Tuple[int, typing.Optional[int]]],
) -> typing.Dict[str, str]:
    """
    Collects the graph inputs that were marked as changes by git. Returns a dictionary containing the changed graph input names and their yaml content on that branch.

    :param graph_inputs_line_number: The line at which the graph inputs start for this file (see util.find_graph_inputs_line_number(...) and git_diff_changed_gx_files(...))
    :param file_content_lines: The lines containing the content of the files (separated on newlines)
    :param changed_lines: The list of line numbers that git is saying are changes (see git_diff_changed_lines(...) and git_diff_changed_gx_files(...))
    """
    # create a dict that will hold the names of all the inputs that were changed (maps name -> yml_block)
    changed_graph_inputs: typing.Dict[str, str] = {}

    # We can return if there are no changes to graph inputs found
    if graph_inputs_line_number < 0:
        return changed_graph_inputs

    # assemble a set containing all the graph inputs that have changes
    relevant_lines: typing.Set[int] = set()

    def filter_and_add(_line_number: int):
        _formatted_line: str = (
            file_content_lines[_line_number]
            .strip()
            .replace("\n", "")
            .replace("\r", "")
            .strip()
            .lower()
        )
        if _formatted_line != "" and _formatted_line != "inputs:":
            relevant_lines.add(_line_number)

    for tuple_range in changed_lines:
        start_index = tuple_range[0]
        if start_index >= graph_inputs_line_number:
            filter_and_add(start_index)
            end_index = tuple_range[1]
            if end_index:
                for i in range(start_index + 1, end_index + 1):
                    filter_and_add(i)

    # we can return right away if none of the changes were beyond the key representing the start of the graph inputs
    # (the bottom of each file)
    if len(relevant_lines) <= 0:
        return changed_graph_inputs

    for ln in relevant_lines:
        gi_name, gi_yaml_block = util.find_graph_input_data_from_line_number(
            file_content_lines, ln
        )
        if gi_name:
            changed_graph_inputs[gi_name] = gi_yaml_block

    return changed_graph_inputs


def git_find_yaml_blocks_for_node_ids(
    git_repo: Repo,
    filepath: str,
    changed_nodes_this_branch: typing.Set[str],
    other_branch_name: str,
    changed_nodes_other_branch: typing.Set[str],
    this_branch_changed_lines: typing.Optional[typing.List[str]] = None,
    other_branch_changed_lines: typing.Optional[typing.List[str]] = None,
) -> typing.Tuple[typing.Dict[str, str], typing.Dict[str, str]]:
    """
    Searches the provided file on each git branch and returns a dictionary mapping of node_id -> "yaml block" of text.
    Will only map out the text blocks for node IDs that appear in both changed sets

    :param git_repo: the git repo object to use to interface with git. Will use the 'active_branch' as one of the two branches
    :param filepath: the path to the file on the filesystem to load the content of
    :param changed_nodes_this_branch: a set of node_ids that was previously identified as being changed on the current branch being tracked by the git_repo object (see git_diff_changed_gx_files(...) )
    :param other_branch_name: the name of the other branch to pull file data from
    :param changed_nodes_other_branch: a set of node_ids that was previously identified as being changed on the 'other_branch_name' (see git_diff_changed_gx_files(...) )
    :param this_branch_changed_lines: (optional) the contents of the filepath for this branch if already pulled from git in a previous function (separated on newlines)
    :param other_branch_changed_lines: (optional) the contents of the filepath for the other branch if already pulled from git in a previous function (separated on newlines)

    :returns: two dictionaries (in a tuple) containing a mapping of node_id -> yaml block. They are returned in the order: (this_branch, other_branch)
    """
    # the node IDs that changed on both branches (both branches reported them as changed)
    changed_both_branches: typing.List[str] = []

    # placeholders just to fix the python intellisense return type of this function
    this_branch_blocks: typing.Dict[str, str] = {}
    other_branch_blocks: typing.Dict[str, str] = {}

    # create the list of node_ids that changed on both branches
    for changed_node_id in changed_nodes_this_branch:
        if changed_node_id in changed_nodes_other_branch:
            changed_both_branches.append(changed_node_id)

    # return empty dicts if no changes line up between both branches
    if len(changed_both_branches) <= 0:
        return (this_branch_blocks, other_branch_blocks)

    # load the contents of the file on each branch and split by line
    this_branch_lines: typing.List[str] = (
        git_show_file_on_branch(git_repo, git_repo.active_branch.name, filepath).split(
            "\n"
        )
        if this_branch_changed_lines is None
        else this_branch_changed_lines
    )
    other_branch_lines: typing.List[str] = (
        git_show_file_on_branch(git_repo, other_branch_name, filepath).split("\n")
        if other_branch_changed_lines is None
        else other_branch_changed_lines
    )

    # create a dictionary of node_id -> yaml block content
    this_branch_blocks: typing.Dict[str, str] = util.find_yaml_blocks_for_node_ids(
        this_branch_lines, changed_nodes_this_branch
    )
    other_branch_blocks: typing.Dict[str, str] = util.find_yaml_blocks_for_node_ids(
        other_branch_lines, changed_nodes_other_branch
    )

    return (this_branch_blocks, other_branch_blocks)


def compare_yaml_blocks_for_nodes(
    this_branch_map: typing.Dict[str, str], other_branch_map: typing.Dict[str, str]
) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    """
    Compares the changes between the yaml blocks of two branches containing nodes with the same IDs.

    :param this_branch_map: A dict of node_id -> "yaml_block" text for the current git branch (see git_find_yaml_blocks_for_node_ids(...) )
    :param other_branch_map: A dict of node_id -> "yaml_block" text for the 'other' git branch (see git_find_yaml_blocks_for_node_ids(...) )

    :returns: Outputs a summary dict containing the following key structure: "node_id" -> dict{ "line_count_difference" (int), "x_coordinate_shift" (int), "y_coordinate_shift" (int), "node_inputs_current_branch_only" (list of dicts{"name"..."graphInputName"...etc.}), "node_inputs_other_branch_only" (list of dicts{"name"..."graphInputName"...etc.}), "field_value_changed" (bool), "field_value_this_branch_only" (bool), "field_value_other_branch_only" (bool), "field_value_this_branch" (str), "field_value_other_branch" (str) }. Also will contain a sub dict at the level: "node_id" -> "node_inputs_changed" -> *input_socket_name* -> dict{ "input_type_changed" (bool), "input_value_changed" (bool), input_value_this_branch (any?), input_value_other_branch (any?), "input_type_this_branch" (str), "input_type_other_branch" (str) } if the input socket data changed between branches (not all of these sub-dict key/values are guarenteed to be present: just the relevant ones (i.e. check the for the sub-dict, then the bools, then the values)). When comparing the coordinate shift values, the difference formula used was "current_branch" - "other_branch" (e.g. current x - other x). Additionally, the keys: "only_in_this_branch" (bool) and "only_in_other_branch" (bool): (node_id -> { here }) will only appear if the node_id is unique to the specified branch. A mapping of node_id -> {} (i.e. empty dict) indicates no detected changes between the node ids. This can happen if git marked the node as changed but it didn't actual have changes in values.
    """
    # to hold all the changes we find between the yaml blocks
    specific_changes = {}
    # iterate through one of the dicts
    for k, this_value in this_branch_map.items():
        # create a sub-dict to hold changes specific to this node_id between the two blocks
        specific_changes[k] = {}
        # compare if there is a difference between the two blocks
        if k not in other_branch_map:
            specific_changes[k]["only_in_this_branch"] = True
            specific_changes[k]["this_branch_yaml"] = this_value
            continue
        other_value = other_branch_map[k]

        # parse our yaml blocks into dicts
        # for some reason the parse_yml function can return a list of a single item
        # This records when nodes are the same. Sometimes git has a conflict when the yaml is exactly the same
        this_yaml: typing.Dict = util.parse_yml(this_value)
        other_yaml: typing.Dict = util.parse_yml(other_value)
        if isinstance(this_yaml, list):
            this_yaml = this_yaml[0]
        if isinstance(other_yaml, list):
            other_yaml = other_yaml[0]

        # record the entire yaml block for both branches
        specific_changes[k]["this_branch_yaml"] = this_value
        specific_changes[k]["other_branch_yaml"] = other_value

        # record if the length of the blocks are different
        specific_changes[k]["line_count_difference"] = abs(
            len(this_value.split("\n")) - len(other_value.split("\n"))
        )

        # compare xy coordinates
        this_xy = str(this_yaml["xy"]).split(",")
        other_xy = str(other_yaml["xy"]).split(",")
        specific_changes[k]["x_coordinate_shift"] = int(this_xy[0]) - int(other_xy[0])
        specific_changes[k]["y_coordinate_shift"] = int(this_xy[1]) - int(other_xy[1])

        # init vars for comparing node inputs
        inputs_key = "inputs"
        input_name_key = "name"
        field_value_key = "fieldValue"
        graph_input_key = "graphInputName"
        variable_key = "variableName"
        connections_key = "connections"

        # setup some dictionary entries to be there even if the if statement doesn't fire
        ## IMPORTANT: in the following loop: the name of the input will appear as a sub-dict key if changed
        ## (input_type_changed) or (input_value_changed)
        specific_changes[k]["node_inputs_current_branch_only"] = []
        specific_changes[k]["node_inputs_other_branch_only"] = []
        specific_changes[k]["node_inputs_changed"] = {}

        def determine_input_change(
            _key: str, _dict1: typing.Dict, _dict2: typing.Dict, _input_name: str
        ):
            """
            Assigns values to the 'specific_changes' dict based on whether the input socket type or input socket value changed.
            Will assign nothing if neither matches

            :returns: True if an assignment was made, False if no assignment was made
            """
            if _key in _dict1:
                if _key not in _dict2:
                    specific_changes[k]["node_inputs_changed"][_input_name][
                        "input_type_changed"
                    ] = True
                    specific_changes[k]["node_inputs_changed"][_input_name][
                        "input_type_this_branch"
                    ] = _key
                    _key2 = "Unknown"
                    if graph_input_key in _dict2:
                        _key2 = graph_input_key
                    elif variable_key in _dict2:
                        _key2 = variable_key
                    elif field_value_key in _dict2:
                        _key2 = field_value_key
                    elif connections_key in _dict2:
                        _key2 = connections_key
                    specific_changes[k]["node_inputs_changed"][_input_name][
                        "input_type_other_branch"
                    ] = _key2
                else:
                    specific_changes[k]["node_inputs_changed"][_input_name][
                        "input_value_changed"
                    ] = True
                    specific_changes[k]["node_inputs_changed"][_input_name][
                        "input_value_this_branch"
                    ] = _dict1[_key]
                    specific_changes[k]["node_inputs_changed"][_input_name][
                        "input_value_other_branch"
                    ] = _dict2[_key]
                return True
            return False

        # compare node inputs
        if inputs_key in this_yaml:
            if inputs_key in other_yaml:
                # both dicts have node inputs (look for changes)
                for this_input_dict in this_yaml[inputs_key]:
                    if this_input_dict in other_yaml[inputs_key]:
                        # this input is the same in both branches
                        continue
                    else:
                        # this input is different for any reason between the branches
                        # grab the name of the input and iterate through the other yaml to find its match
                        n = this_input_dict[input_name_key]
                        for other_input_dict in other_yaml[inputs_key]:
                            if (
                                input_name_key in other_input_dict
                                and other_input_dict[input_name_key] == n
                            ):
                                # create a new sub-dict to specify the changes to this specific input socket
                                specific_changes[k]["node_inputs_changed"][n] = {}
                                ## check each possible combination of input socket
                                ## record that either the type of socket or the value of the socket changed
                                if determine_input_change(
                                    graph_input_key,
                                    this_input_dict,
                                    other_input_dict,
                                    n,
                                ):
                                    break
                                if determine_input_change(
                                    variable_key,
                                    this_input_dict,
                                    other_input_dict,
                                    n,
                                ):
                                    break
                                if determine_input_change(
                                    field_value_key,
                                    this_input_dict,
                                    other_input_dict,
                                    n,
                                ):
                                    break
                                if determine_input_change(
                                    connections_key,
                                    this_input_dict,
                                    other_input_dict,
                                    n,
                                ):
                                    break
                                break
                        # end for other_input_dict in other_yaml[inputs_key]
                    # end else (inputs not equal)
                # end for this_input_dict in this_yaml[inputs_key]
            else:
                # only this branch has node inputs
                specific_changes[k]["node_inputs_current_branch_only"] = this_yaml[
                    inputs_key
                ]
        elif inputs_key in other_yaml:
            # only the other branch has node inputs
            specific_changes[k]["node_inputs_other_branch_only"] = other_yaml[
                inputs_key
            ]

        # setup some dictionary entries to be there even if the if statement doesn't fire
        specific_changes[k]["field_value_changed"] = False
        specific_changes[k]["field_value_this_branch_only"] = False
        specific_changes[k]["field_value_other_branch_only"] = False
        specific_changes[k]["field_value_this_branch"] = ""
        specific_changes[k]["field_value_other_branch"] = ""

        # compare fieldValue:
        if field_value_key in this_yaml:
            specific_changes[k]["field_value_this_branch"] = this_yaml[field_value_key]
            if field_value_key in other_yaml:
                specific_changes[k]["field_value_other_branch"] = other_yaml[
                    field_value_key
                ]
                # here we know both branches have a field value for this node
                if this_yaml[field_value_key] != other_yaml[field_value_key]:
                    # here we know the value of the field value changed between branches
                    specific_changes[k]["field_value_changed"] = True
            else:
                # here we know only this_yaml has a field_value
                specific_changes[k]["field_value_this_branch_only"] = True
        elif field_value_key in other_yaml:
            specific_changes[k]["field_value_other_branch"] = other_yaml[
                field_value_key
            ]
            # here we know only the other yaml has a field value
            specific_changes[k]["field_value_other_branch_only"] = True
        # endif
    # end for k,v in items
    for k, other_value in other_branch_map.items():
        if k not in specific_changes:
            specific_changes[k] = {}
            specific_changes[k]["only_in_other_branch"] = True
            specific_changes[k]["other_branch_yaml"] = other_value
    return specific_changes


def compare_graph_inputs(
    git_repo: Repo,
    other_branch_name: str,
    filepath: str,
    this_branch_changed_graph_inputs: typing.Dict[str, str],
    other_branch_changed_graph_inputs: typing.Dict[str, str],
    this_branch_graph_inputs_start_line: int,
    other_branch_graph_inputs_start_line: int,
    this_branch_changed_lines: typing.Optional[typing.List[str]] = None,
    other_branch_changed_lines: typing.Optional[typing.List[str]] = None,
) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    """
    Compares the two provided dictionaries of graph inputs names and yml blocks. Outputs a single dictionary containing a summary of the changes between the two branches.
    This function will double-check the opposing git branch if a change (graph input name) is recognized by only one branch. This helps prevent marking graph inputs that didn't actually change between the branches (meaning git marked too much as changed).

    :param git_repo: the git repo object to use to interface with git. Will use the 'active_branch' as one of the two branches
    :param other_branch_name: the name of the other branch (the same one as the other_branch_... inputs)
    :param filepath: the path to the file on the filesystem being compared
    :param this_branch_changed_graph_inputs: A dictionary of 'graph input name' -> 'yml block' of the changes detected on this branch only (see find_changed_graph_inputs(...) and git_diff_changed_gx_files(...))
    :param other_branch_changed_graph_inputs A dictionary of 'graph input name' -> 'yml block' of the changes detected on the 'other_branch_name' only (see find_changed_graph_inputs(...) and git_diff_changed_gx_files(...))
    :param this_branch_graph_inputs_start_line: The line at which graph inputs start appearing in the filepath for this branch (see util.find_graph_inputs_line_number(...) and git_diff_changed_gx_files(...))
    :param other_branch_graph_inputs_start_line: The line at which graph inputs start appearing in the filepath for the 'other_branch_name' branch (see util.find_graph_inputs_line_number(...) and git_diff_changed_gx_files(...))
    :param this_branch_changed_lines: (optional) the contents of the filepath for this branch if already pulled from git in a previous function (separated on newlines)
    :param other_branch_changed_lines: (optional) the contents of the filepath for the other branch if already pulled from git in a previous function (separated on newlines)

    :returns: A dictionary of the form: graph_input_name -> { details about that input }. Where the detail keys can be any of the following: only_on_this_branch (bool), only_on_other_branch (bool), both_branches (bool), this_branch_yaml (string), other_branch_yaml (string), line_count_difference (int). When comparing individual aspects of graph inputs changed on "both_branches" (True): you will always have three keys in this form: "key_name_changed", "this_branch_key_name" and "other_branch_key_name" where 'key_name' can be one of: "datatype", "isList", "description", "category", "enumOptions", "defaultValue", "isPassword".
    """
    # to hold all the changes we find between the yaml blocks
    gi_specific_changes: dict = {}

    # to hold information about each individual branch
    gi_both_branches: typing.Set[str] = set()
    gi_only_this_branch: typing.Dict[str, str] = {}
    gi_only_other_branch: typing.Dict[str, str] = {}

    # check if the inputs changed on both branches are equal
    for graph_input_name in this_branch_changed_graph_inputs.keys():
        if graph_input_name not in other_branch_changed_graph_inputs:
            # only in this branch
            gi_only_this_branch[graph_input_name] = this_branch_changed_graph_inputs[
                graph_input_name
            ]
        else:
            # in both branches
            gi_both_branches.add(graph_input_name)
    for graph_input_name in other_branch_changed_graph_inputs.keys():
        if graph_input_name not in this_branch_changed_graph_inputs:
            # only in other branch
            gi_only_other_branch[graph_input_name] = other_branch_changed_graph_inputs[
                graph_input_name
            ]

    # We need to QA git here because sometimes the 'only on x branch' sets are not detected properly by git
    # go through the individual sets and do a lookup on the other branch to confirm that the graph input name is unique
    if len(gi_only_this_branch) > 0 or len(gi_only_other_branch) > 0:
        # load the contents of the file on each branch and split by line
        this_branch_lines: typing.List[str] = (
            git_show_file_on_branch(
                git_repo, git_repo.active_branch.name, filepath
            ).split("\n")
            if this_branch_changed_lines is None
            else this_branch_changed_lines
        )
        other_branch_lines: typing.List[str] = (
            git_show_file_on_branch(git_repo, other_branch_name, filepath).split("\n")
            if other_branch_changed_lines is None
            else other_branch_changed_lines
        )

        if len(gi_only_this_branch) > 0:
            delete_keys: typing.List[str] = []
            for graph_input_name in gi_only_this_branch:
                yml_block = util.find_graph_input_yml_by_name(
                    graph_input_name,
                    other_branch_lines,
                    other_branch_graph_inputs_start_line,
                )
                if yml_block != "":
                    # this input actually exists on the other git branch as well
                    delete_keys.append(graph_input_name)
                    gi_both_branches.add(graph_input_name)
                    other_branch_changed_graph_inputs[graph_input_name] = yml_block
                # end if yml
            # end for1
            for k in delete_keys:
                gi_only_this_branch.pop(k)
            # end for2
        # end if len
        if len(gi_only_other_branch) > 0:
            delete_keys: typing.List[str] = []
            for graph_input_name in gi_only_other_branch:
                yml_block = util.find_graph_input_yml_by_name(
                    graph_input_name,
                    this_branch_lines,
                    this_branch_graph_inputs_start_line,
                )
                if yml_block != "":
                    # this input actually exists on this git branch as well
                    delete_keys.append(graph_input_name)
                    gi_both_branches.add(graph_input_name)
                    this_branch_changed_graph_inputs[graph_input_name] = yml_block
                # end if yml
            # end for1
            for k in delete_keys:
                gi_only_other_branch.pop(k)
            # end for2
        # end if len
    # end if len or len

    # at this point we can assume our local variables are correctly tracking the changes to the graph inputs
    # add the graph inputs unique to one branch or the other
    for graph_input_name, yml_block in gi_only_this_branch.items():
        gi_specific_changes[graph_input_name] = {}
        gi_specific_changes[graph_input_name]["only_on_this_branch"] = True
        gi_specific_changes[graph_input_name]["this_branch_yaml"] = yml_block
    for graph_input_name, yml_block in gi_only_other_branch.items():
        gi_specific_changes[graph_input_name] = {}
        gi_specific_changes[graph_input_name]["only_on_other_branch"] = True
        gi_specific_changes[graph_input_name]["other_branch_yaml"] = yml_block

    ### Helper functions for looping through the graph input yml data
    def key_changed(_key_name: str):
        """
        Returns True if the _key_name is in either yaml
        """
        return _key_name in this_yaml_values or _key_name in other_yaml_values

    def assign_temp_values(_key_name: str, _else_value: str):
        """
        Assigns a temp value to this branch and other branch based on the value in the yaml or the _else_value if not present in the yaml
        """
        t = (
            this_yaml_values[_key_name]
            if _key_name in this_yaml_values
            else _else_value
        )
        o = (
            other_yaml_values[_key_name]
            if _key_name in other_yaml_values
            else _else_value
        )
        return t, o

    def record_changes(
        _key_name: str,
        _input_name: str,
        _this_value: typing.Any,
        _other_value: typing.Any,
    ):
        """
        Adds three keys annotating the specific changes to the dict returned by the parent of this function.
        """
        gi_specific_changes[_input_name][_key_name + "_changed"] = True
        gi_specific_changes[_input_name]["this_branch_" + _key_name] = _this_value
        gi_specific_changes[_input_name]["other_branch_" + _key_name] = _other_value

    def mark_if_value_changed(_key_name: str, _input_name: str, _else_value: str):
        """
        Assigns values to temp variables based on their presence in the yaml or not and records a change if there is one between the variables.
        """
        _t, _o = assign_temp_values(_key_name, _else_value)
        if _t != _o:
            record_changes(_key_name, _input_name, _t, _o)

    ### End helper functions

    # now we need to compare changes that occured on both branches
    for graph_input_name in gi_both_branches:
        if (
            this_branch_changed_graph_inputs[graph_input_name]
            == other_branch_changed_graph_inputs[graph_input_name]
        ):
            # both branches are equal ... we have no reason to alert anyone of a change
            continue
        # else there was a change between the branches
        gi_specific_changes[graph_input_name] = {}
        gi_specific_changes[graph_input_name]["both_branches"] = True

        # store the exact yaml change between the blocks
        this_branch_yml: str = this_branch_changed_graph_inputs[graph_input_name]
        other_branch_yml: str = other_branch_changed_graph_inputs[graph_input_name]
        gi_specific_changes[graph_input_name]["this_branch_yaml"] = this_branch_yml
        gi_specific_changes[graph_input_name]["other_branch_yaml"] = other_branch_yml

        # determine if there was a change in the length of the blocks
        gi_specific_changes[graph_input_name]["line_count_difference"] = abs(
            len(this_branch_yml.split("\n")) - len(other_branch_yml.split("\n"))
        )

        # parse the yaml to get individual changes
        this_yaml: typing.Dict = util.parse_yml("inputs:\n" + this_branch_yml)
        other_yaml: typing.Dict = util.parse_yml("inputs:\n" + other_branch_yml)
        this_yaml_values: typing.Dict = this_yaml["inputs"][0]
        other_yaml_values: typing.Dict = other_yaml["inputs"][0]

        # datatype must be in both inputs
        single_key_name = "datatype"
        if this_yaml_values[single_key_name] != other_yaml_values[single_key_name]:
            record_changes(
                single_key_name,
                graph_input_name,
                this_yaml_values[single_key_name],
                other_yaml_values[single_key_name],
            )

        # to compare optional keys we first have to check for the existance of the key and then evaluate if the value of the keys changed
        keys = [
            ("isList", False),
            ("description", ""),
            ("category", ""),
            ("enumOptions", ""),
            ("defaultValue", ""),
            ("isPassword", False),
        ]
        for key_tuple in keys:
            key_name: str = key_tuple[0]
            else_value: str = str(key_tuple[1])
            if key_changed(key_name):
                mark_if_value_changed(key_name, graph_input_name, else_value)

    # return the dict of compiled changes
    return gi_specific_changes


def git_diff_gx(
    git_repo: Repo, other_branch_name: str, filepath: str
) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    """
    Performs a 'git diff' of the current branch being tracked by the provided 'git_repo' object against the 'other_branch_name' on the provided 'filepath'.
    The results from 'git diff' are parsed for line number indicators. This function will return immediately if no changes are detected by 'git'.
    If changes are detected: the line numbers will be used to extract the relevant 'node IDs' and 'graph input names' from the filepath on each branch (using 'git show').
    The yaml blocks extracted from the filepath will be compared to determine the exact changes between the two branches.

    :param git_repo: A properly configured/initialized 'git repository' object created from the 'git' pip package (e.g.: from git import Repo)
    :param other_branch_name: The name of the other branch to compare as a string
    :param filepath: The path to the file on the filesystem as a string

    :returns: A dictionary summary of the specific changes made between the two branches. The returned dictionary will be empty if no changes are found between the branches.
    The top level keys are: "changes_to_nodes" and "changes_to_graph_inputs". Both these top level keys map to sub-dicts. The keys for the "changes_to_nodes" sub-dict are the node_ids that have changes on either branch and the keys for "changes_to_graph_inputs" are the names of the changed inputs (e.g. it is possible for a node ID or graph input name to exist only on one of the branches). For specific details on the keys possible to appear in the sub-dicts, please see the comparison function comments in this file: compare_yaml_blocks_for_nodes(...) and compare_graph_inputs(...).
    """
    # perform the git diff, parse the git results, and identify which nodes and graph inputs are affected by the diff between the two branches
    dict_of_possible_diffs = git_diff_changed_gx_files(
        git_repo=git_repo, other_branch_name=other_branch_name, filepath=filepath
    )

    # None is returned if there is no changes detected between the branches
    if dict_of_possible_diffs is None:
        return {}

    # Now that we know the IDs of the nodes that are supposably changed: get the yaml blocks corresponding to the changed IDs on both branches
    current_branch_nodes_to_yaml, other_branch_nodes_to_yaml = (
        git_find_yaml_blocks_for_node_ids(
            git_repo=git_repo,
            filepath=filepath,
            changed_nodes_this_branch=dict_of_possible_diffs[
                "changed_nodes_this_branch"
            ],
            other_branch_name=other_branch_name,
            changed_nodes_other_branch=dict_of_possible_diffs[
                "changed_nodes_other_branch"
            ],
            this_branch_changed_lines=dict_of_possible_diffs[
                "line_content_for_this_branch"
            ],
            other_branch_changed_lines=dict_of_possible_diffs[
                "line_content_for_other_branch"
            ],
        )
    )

    # Compare the yaml blocks of the two branches and create a specific, compiled dictionary of the changes between the branches
    dict_of_specific_changes_to_nodes = compare_yaml_blocks_for_nodes(
        current_branch_nodes_to_yaml, other_branch_nodes_to_yaml
    )

    # Compare the graph inputs of the two branches (retrieving more yaml blocks as needed) and return a specific, compiled dictionary of the changes for just the graph inputs
    # (between the two branches)
    dict_of_specific_changes_to_graph_inputs = compare_graph_inputs(
        git_repo=git_repo,
        other_branch_name=other_branch_name,
        filepath=filepath,
        this_branch_changed_graph_inputs=dict_of_possible_diffs[
            "changed_graph_inputs_this_branch"
        ],
        other_branch_changed_graph_inputs=dict_of_possible_diffs[
            "changed_graph_inputs_other_branch"
        ],
        this_branch_graph_inputs_start_line=dict_of_possible_diffs[
            "graph_inputs_start_line_this_branch"
        ],
        other_branch_graph_inputs_start_line=dict_of_possible_diffs[
            "graph_inputs_start_line_other_branch"
        ],
        this_branch_changed_lines=dict_of_possible_diffs[
            "line_content_for_this_branch"
        ],
        other_branch_changed_lines=dict_of_possible_diffs[
            "line_content_for_other_branch"
        ],
    )

    # return the changes compiled into a single dict
    return {
        "changes_to_nodes": dict_of_specific_changes_to_nodes,
        "changes_to_graph_inputs": dict_of_specific_changes_to_graph_inputs,
    }


def check_file_for_merge_conflict(file_contents: str, parse_yml: bool = True):
    """
    First attempts to parse the yaml for the provided file (if parse_yml is True).
    If the parse fails: searches for the 'git HEAD' marker in the file.

    :param file_contents: The entire contents of the file
    :parma parse_yml: Whether to attempt to parse the file first (recommended)

    :returns: True if the file has a conflict, False otherwise
    """
    if not parse_yml:
        return GIT_MERGE_HEAD_MARKER in file_contents

    # If there is a merge conflict the parse will fail
    try:
        util.parse_yml(file_contents)
    except Exception:
        return GIT_MERGE_HEAD_MARKER in file_contents
    return False


def determine_merge_conflict_line_numbers(file_contents_lines: typing.List[str]):
    """
    Breaks up the contents of a file with one or more merge conflicts into lines and then collects the line number ranges
    that are effecting the merge conflict.

    :param file_contents: a single string containing the entire contents of the file with a merge conflict

    :returns: A list of line number ranges showing the start and end lines of the conflict as a tuple of values: (starting_line, ending_line)
    """

    line_ranges: typing.List[typing.Tuple[int, int]] = []
    line_start = -1
    for i, line in enumerate(file_contents_lines):
        if GIT_MERGE_HEAD_MARKER in line:
            line_start = i + 1
        elif GIT_MERGE_END_MARKER in line:
            if line_start < 0:
                raise Exception(
                    f"ERROR: 'git merge' ending marker: '{GIT_MERGE_END_MARKER}' was detected in line: '{line}' but the 'git merge' start marker: '{GIT_MERGE_HEAD_MARKER}' was not previously found!"
                )
            line_ranges.append((line_start, i + 1))
            line_start = -1
    return line_ranges


def extract_from_merge_conflict_line_numbers(
    merge_lines: typing.List[typing.Tuple[int, int]],
    file_contents_lines: typing.List[str],
):
    """
    Using the provided 'merge_lines' (numbers): steps through the file with the merge conflict and determines the affected node ID or graph input name for each provided line.

    :param merge_lines: A list of line number ranges showing the start and end lines of the conflict as a tuple of values: (starting_line, ending_line) ( see determine_merge_conflict_line_numbers(...) )
    :param file_contents_lines: The contents of the file with a merge conflict after it has been split into lines on the newline ('\n') character

    :returns: A dictionary containing two keys: "matching_node_ids" and "matching_graph_input_data". The key "matching_node_ids" maps to a set of node_ids that are affected by the merge conflict. The key "matching_graph_input_data" maps to a sub-dictionary containing the names of the graph inputs that are affected and maps those names to their yml blocks.
    """
    node_ids: typing.Set[str] = set()
    graph_input_data: typing.Dict[str, str] = {}
    graph_inputs_start_number: int = util.find_graph_inputs_line_number(
        file_contents_lines
    )

    for lines_tuple in merge_lines:
        # line numbers are always one higher than index numbers
        for line_number in range(lines_tuple[0], lines_tuple[1] + 1):
            if (
                line_number < graph_inputs_start_number
                or graph_inputs_start_number == -1
            ):
                node_id = util.node_id_from_file_content(
                    file_contents_lines, line_number, stop_if_empty_line=True
                )
                if node_id != "":
                    node_ids.add(node_id)
            elif (
                line_number > graph_inputs_start_number
                and graph_inputs_start_number != -1
            ):
                graph_input_name, yml_block = (
                    util.find_graph_input_data_from_line_number(
                        file_contents_lines, line_number
                    )
                )
                if graph_input_name != "" and yml_block != "":
                    graph_input_data[graph_input_name] = yml_block

    return {
        "matching_node_ids": list(node_ids),
        "matching_graph_input_data": graph_input_data,
    }


def identify_merge_conflict_causes(
    git_repo: Repo, other_branch_name: str, filepath: str, gitpath: str
) -> dict:
    """
    This function operates similar to the 'git_diff_gx(...)' function except that it is specific to merge conficts.
    This function parses the provided filepath and automatically determines which node IDs and graph input names are affected by merge conflicts.
    After identifying the affected parts of the file: compares the changes between the two branches and outputs a dictionary in the same format as 'git_diff_gx(...)' (read the comment for that function for specifics).
    This function will not compare every change between the two files, but instead will only compare the changes causing a merge conflict.

    :param git_repo: the git repo object to use to interface with git. Will use the 'active_branch' as one of the two branches
    :param other_branch_name: the name of the other branch in the conflict
    :param filepath: the path to the file on the filesystem with the merge conflict
    :param gitpath: the path to the file in the git repo with the merge conflict

    :returns: A dictionary with the similar keys as 'git_diff_gx(...)'. Also includes a key that shows specifically all the node IDs and graph input names identified as conflicts by git: "identified_conflicts" -> dict { "matching_node_ids", "matching_graph_input_data"} and a key for "current_branch_nodes_to_yaml" (for use by the reconstruction function later)
    """
    # Validate we are comparing two different branches
    if other_branch_name == git_repo.active_branch.name:
        raise Exception(
            f"Error: trying to run a GX git diff between two branches with the same name!: {other_branch_name}"
        )

    # Validate that the file we are trying to diff exists
    # git will not inform you if the file doesn't exist!
    if not os.path.exists(filepath):
        raise Exception(f"No file exists on server with name: {filepath}")

    if not os.path.isfile(filepath):
        raise Exception(f"Is not a 'file': {filepath}")

    with open(filepath, "r") as f:
        content = f.read()

    # check if there are any conflicts to begin with
    if not check_file_for_merge_conflict(content):
        return {}

    # break up the file into lines
    lines_from_file: typing.List[str] = content.split("\n")

    # determine which lines in the file are affected by merge conflicts
    merge_line_number_ranges: typing.List[typing.Tuple[int, int]] = (
        determine_merge_conflict_line_numbers(lines_from_file)
    )

    # Create a dict identifing the node IDs and the graph input names that were found from the conflicting line numbers
    # TODO make sure this searches both directions?
    dict_of_node_ids_and_gi_names = extract_from_merge_conflict_line_numbers(
        merge_line_number_ranges, lines_from_file
    )

    # collect the files for each branch for analysis
    this_branch_lines: typing.List[str] = git_show_file_on_branch(
        git_repo, git_repo.active_branch.name, gitpath
    ).split("\n")
    other_branch_lines: typing.List[str] = git_show_file_on_branch(
        git_repo, other_branch_name, gitpath
    ).split("\n")

    # Grab the yaml blocks that match the node IDs identified as changes
    current_branch_nodes_to_yaml, other_branch_nodes_to_yaml = (
        git_find_yaml_blocks_for_node_ids(
            git_repo,
            filepath,
            dict_of_node_ids_and_gi_names["matching_node_ids"],
            other_branch_name,
            dict_of_node_ids_and_gi_names["matching_node_ids"],
            this_branch_lines,
            other_branch_lines,
        )
    )

    # Compare the yaml blocks of the two branches and create a specific, compiled dictionary of the changes between the branches
    dict_of_specific_changes_to_nodes = compare_yaml_blocks_for_nodes(
        current_branch_nodes_to_yaml, other_branch_nodes_to_yaml
    )

    # get the line numbers where the graph inputs begin in each branch
    line_number_for_graph_inputs_in_this_branch = util.find_graph_inputs_line_number(
        this_branch_lines
    )
    line_number_for_graph_inputs_in_other_branch = util.find_graph_inputs_line_number(
        other_branch_lines
    )

    # Compare the graph inputs of the two branches (retrieving more yaml blocks as needed) and return a specific, compiled dictionary of the changes for just the graph inputs
    # (between the two branches)

    # Get the graph input yaml for each branch
    inputs = dict_of_node_ids_and_gi_names["matching_graph_input_data"].keys()
    this_branch_input_changes: dict[str, str] = {}
    other_branch_input_changes: dict[str, str] = {}

    for input in inputs:
        # Split the text by the conflict markers
        parts = dict_of_node_ids_and_gi_names["matching_graph_input_data"][input].split(
            "<<<<<<< HEAD\n"
        )
        if len(parts) == 1:
            # only exists in one branch, but git markers are not nice
            incoming_change = parts[0].split("\n>>>>>>> ")[0]
            current_change = ""
            # this_branch_input_changes[input] = current_change
            other_branch_input_changes[input] = incoming_change
        else:
            # Split the second part by the next conflict marker
            current_change, incoming_change = parts[1].split("\n=======\n")

            # Remove the trailing conflict marker from the incoming change
            incoming_change = incoming_change.split("\n>>>>>>> ")[0]

            # Reconstruct the full strings for each change
            current_change_full = parts[0] + current_change
            incoming_change_full = parts[0] + incoming_change

            this_branch_input_changes[input] = current_change_full
            other_branch_input_changes[input] = incoming_change_full

    dict_of_specific_changes_to_graph_inputs = compare_graph_inputs(
        git_repo,
        other_branch_name,
        filepath,
        this_branch_input_changes,
        other_branch_input_changes,
        line_number_for_graph_inputs_in_this_branch,
        line_number_for_graph_inputs_in_other_branch,
        this_branch_lines,
        other_branch_lines,
    )

    # return the changes compiled into a single dict
    return {
        "changes_to_nodes": dict_of_specific_changes_to_nodes,
        "changes_to_graph_inputs": dict_of_specific_changes_to_graph_inputs,
        "identified_conflicts": dict_of_node_ids_and_gi_names,
        "current_branch_nodes_to_yaml": current_branch_nodes_to_yaml,
    }


def reconstruct_merge_conflicted_file(
    git_repo: Repo,
    other_branch_name: str,
    filepath: str,
    gitpath: str,
    chosen_nodes_on_branch: typing.Dict[str, str],
    chosen_graph_inputs_on_branch: typing.Dict[str, str],
    identified_conflicts: typing.Dict[str, typing.Any],
    current_branch_nodes_to_yaml: typing.Dict[str, str],
) -> str:
    """
    This function is intended to be called only after "identify_merge_conflict_causes(...)" has returned each branch's choice to the user during a merge conflict. The user then selects which nodes and graph inputs to change from each branch and returns the choices to this function. This function then reconstructs the conflicted file with the chosen changes.

    :param git_repo: the git repo object to use to interface with git. Will use the 'active_branch' as one of the two branches
    :param other_branch_name: the name of the other branch in the conflict
    :param filepath: the path to the file on the filesystem with the merge conflict
    :param gitpath: the path to the file in the git repo with the merge conflict
    :param chosen_nodes_on_branch: A mapping of node_id -> yaml of branch chosen for this ID
    :param chosen_graph_inputs_on_branch: A mapping of graph_input_name -> yaml of branch chosen for this graph input name
    :param identified_conflicts: The same dict as the key in identify_merge_conflict_causes(...)

    :return: A string containing the new file contents (merge conflict resolved)
    """

    # variable to hold the reconstructed file
    new_file_string = ""

    # Validate we are comparing two different branches
    if other_branch_name == git_repo.active_branch.name:
        raise Exception(
            f"Error: trying to run a GX git diff between two branches with the same name!: {other_branch_name}"
        )

    # Validate that the file we are trying to diff exists
    # git will not inform you if the file doesn't exist!
    if not os.path.exists(filepath):
        raise Exception(f"No file exists on server with name: {filepath}")

    if not os.path.isfile(filepath):
        raise Exception(f"Is not a 'file': {filepath}")

    with open(filepath, "r") as f:
        content = f.read()

    # break up the file into lines
    lines_from_merge_conflict_file: typing.List[str] = content.split("\n")

    # some flags to keep track of what is happening as we traverse the file contents
    nodes_key: str = "nodes:"
    inputs_key: str = "inputs:"
    names_key: str = "  - name: "
    ids_key: str = "id: "
    found_nodes_key: bool = False
    found_inputs_key: bool = False
    skipping_line: bool = False

    # keep track of the nodes and graph inputs to avoid duplication
    recorded_nodes: typing.List[str] = []
    recorded_inputs: typing.List[str] = []

    def find_id_of_yaml_block(_current_index: int):
        """
        Returns the index of the node_id in the current yaml block or -1 if it isn't found
        """
        if _current_index + 1 >= len(lines_from_merge_conflict_file):
            return -1
        i = _current_index
        while True:
            _line = lines_from_merge_conflict_file[i + 1].strip()
            if _line.startswith(ids_key):
                return i + 1
            elif _line == "":
                return -1
            if i + 1 < len(lines_from_merge_conflict_file):
                i = i + 1
            else:
                return -1

    for i, line in enumerate(lines_from_merge_conflict_file):
        # format the string once and check it in several more places
        formatted_line = line.replace("\r", "").strip()

        # continue to the next line if this line has a git marker (we are ignoring them)
        if (
            formatted_line.startswith(GIT_MERGE_HEAD_MARKER)
            or formatted_line == GIT_MERGE_CENTER_SEP
            or formatted_line.startswith(GIT_MERGE_END_MARKER)
        ):
            continue
        # only record the nodes_key once
        elif formatted_line == nodes_key:
            if not found_nodes_key:
                found_nodes_key = True
                new_file_string += line + "\n"
            continue
        # only record the inputs_key once
        # we want to include whitespace in the equality check here (nodes can also have a key called inputs)
        elif line == inputs_key:
            if not found_inputs_key:
                found_inputs_key = True
                new_file_string += line + "\n"
            continue
        # reset the skip tracker when we reach an empty line
        elif formatted_line == "":
            skipping_line = False
            new_file_string += "\n"
            continue
        elif skipping_line:
            continue
        # this should be the start of a section for either naming or IDs
        # we want to include whitespace in the equality check here
        elif line.startswith(names_key):
            # if we are tracking graph inputs (always bottom of file)
            if found_inputs_key:
                # grab the name of the graph input from this line
                graph_input_name = util.extract_graph_input_name_from_line(line)
                if graph_input_name in recorded_inputs:
                    # graph input has already been recorded
                    skipping_line = True
                    continue
                # check if we have a conflict for this file
                if (
                    graph_input_name
                    in identified_conflicts["matching_graph_input_data"]
                ):
                    if graph_input_name in chosen_graph_inputs_on_branch:
                        # The user specified which branch to use here
                        # Only add the input if the user specified
                        new_file_string += chosen_graph_inputs_on_branch[
                            graph_input_name
                        ]
                        recorded_inputs.append(graph_input_name)
                    skipping_line = True
                    if not new_file_string.endswith("\n"):
                        new_file_string += "\n"
                    continue
                    # end if in chosen inputs
                # end if conflict
            # if we are tracking nodes
            elif found_nodes_key:
                # we need to look forward to find the ID in this block of yaml
                index_of_ids_key = find_id_of_yaml_block(i)
                # fail the operation if we couldn't find the index line for the ID
                if index_of_ids_key < 0:
                    raise Exception(
                        f"Reached blank line or end of file while searching for the key: '{ids_key}' (during merge conflict file reconstruction)! Started searching at line number: {i+1}"
                    )
                # grab the line cooresponding to the index
                _line = lines_from_merge_conflict_file[index_of_ids_key]
                # grab the node_id from that line
                node_id = util.extract_node_id_from_line(_line)
                if node_id in recorded_nodes:
                    # node has already been recorded
                    skipping_line = True
                    continue
                # check if we have a conflict for this file
                if node_id in identified_conflicts["matching_node_ids"]:
                    if node_id in chosen_nodes_on_branch:
                        new_file_string += chosen_nodes_on_branch[node_id]
                        recorded_nodes.append(node_id)
                    elif node_id in current_branch_nodes_to_yaml:
                        # load the contents of this branch only if we need them
                        new_file_string += current_branch_nodes_to_yaml[node_id]
                        recorded_nodes.append(node_id)
                    skipping_line = True
                    if not new_file_string.endswith("\n"):
                        new_file_string += "\n"
                    continue
                    # end if chosen node
                # end if conflict
            # end elif formatted line starts with names key
        # else
        # simply record the line and move on
        new_file_string += line + "\n"
    # end for line in lines
    return new_file_string


def git_merge_log(git_repo: Repo) -> typing.Dict[str, str]:
    """
    Determines the names and hashes of the most recent commits being merged together.
    This function is only intended to be used if a merge conflict has already been created on the current branch (and not yet resolved)

    :param git_repo: the git repo object to use to interface with git

    :returns: A dictionary of strings with the following keys: "this_branch_commit_hash", "this_branch_commmit_name", "other_branch_commit_hash", and "other_branch_commit_name"
    """
    raw_text: str = git_repo.git.log("--merge", "--oneline")
    lines: typing.List[str] = raw_text.split("\n")
    this_branch_info: typing.List[str] = lines[0].split()
    other_branch_info: typing.List[str] = lines[1].split()
    return {
        "this_branch_commit_hash": this_branch_info[0].strip(),
        "this_branch_commmit_name": this_branch_info[1].strip(),
        "other_branch_commit_hash": other_branch_info[0].strip(),
        "other_branch_commit_name": other_branch_info[1].strip(),
    }


def git_branches_containing_hash(git_repo: Repo, hash: str) -> typing.List[str]:
    """
    Returns a list of branches that have the hash provided.

    :param git_repo: the git repo object to use to interface with git
    :param hash: The commit hash that you want to find out the branch names for

    :returns: a list of all branches that contain the provided hash for one of their commits
    """
    raw_text: str = git_repo.git.branch("--contains", hash)
    lines = raw_text.split("\n")
    for i in range(len(lines)):
        # split on whitespace
        removed_whitespace: typing.List[str] = lines[i].split()
        lines[i] = (
            removed_whitespace[1].strip()
            if len(removed_whitespace) > 1
            else removed_whitespace[0].strip()
        )
    return lines
