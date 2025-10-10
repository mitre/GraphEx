import typing
import os
from graphex import GraphRegistry
from graphex.util import parse_yml

if typing.TYPE_CHECKING:
    from graphex.node import Node

class InventoryEntry:
    """
    Object that represents a single entry in a single 'InventoryFile' object.
    The raw data from the parsed yaml can be retrieved from the 'content' dictionary.
    If the entry can be init as an object in a GraphEx graph, it will extract the relevant information to recreate it into the following instance variables:
    self.node contains the node itself.
    self.node_inputs is a dict of mappings of node_input_name -> primitive data to apply to the created node.
    To have these instance variables defined, you must first add them to the yaml block. The yaml key 'Node' is reserved for this at the top level of each yaml entry.
    For example:
    - Name: MyESXiVM
    ...any ordinary primitive data...then...
      Node:
        Name: Get ESXi VM
        Inputs:
        - VM Name or ID: MyESXiVM
        - OS Type: Windows
        - Is ID?: False
    """
    def __init__(self, entry_name: str, yaml_content: typing.Dict[str, typing.Any], registry: GraphRegistry):
        self.entry_name: str = entry_name
        self.content: typing.Dict[str, typing.Any] = yaml_content
        self.node_name: str = ""
        self.node: typing.Optional[typing.Dict] = {}
        self.node_inputs: typing.Dict[str, typing.Union[int, float, bool, str]] = {}

        # Load the node metadata if this 'Node' key from the yaml exists in the registry
        if "Node" in self.content:
            node_block: typing.Dict[str, typing.Any] = self.content["Node"]
            try:
                self.node = registry.get_node(node_block["Name"]).metadata(None, None)
            except Exception as e:
                raise Exception(f"Error while loading inventory. Failed to load the node specified by the YML file with the name: '{node_block['Name']}' ... For the YML inventory entry: '{entry_name}'. Verify that all required plugins for this node are loaded and that the node name exists. The Actual error was: {str(e)}")
            self.node_name = node_block["Name"]
            # Load default values the user wants to add to the node
            if "Inputs" in node_block:
                inputs_block = node_block["Inputs"]
                # This code expects a list but we can convert a dict and it should still work
                if isinstance(inputs_block, dict):
                    inputs_block = [inputs_block]
                for list_item in inputs_block:
                    list_item: typing.Dict[str, typing.Union[str, float, int, bool]]
                    for input_name,input_value in list_item.items():
                        # Verify that the name of the socket provided in the 'Inputs' yaml block matches a socket with that same name in the node metadata
                        found_in_metadata: bool = False
                        for s in self.node["sockets"]:
                            if s["name"] == input_name:
                                found_in_metadata = True
                                break
                        if not found_in_metadata:
                            raise Exception(f"Error in Inventory entry with name: '{self.entry_name}': No socket input with name: '{input_name}' exists on the provided node name: '{self.node_name}'. Verify the fields provided in the yaml file under '{self.entry_name}' -> 'Node' -> 'Inputs' match the name of an available input socket on the node with name: '{self.node_name}'.")
                        self.node_inputs[input_name] = input_value
            # remove this key from the 'data' part of our inventory
            # we already recorded the relevant information to recreate this node later
            del self.content["Node"]
            if len(self.content.keys()) == 1 and "Name" in self.content:
                del self.content["Name"]
        # endif
    # end __init__

    def as_dict(self) -> typing.Dict:
        return {
            "entry_name": self.entry_name,
            "content": self.content,
            "name_of_node": self.node_name,
            "node": self.node,
            "node_inputs": self.node_inputs
        }

    def __str__(self) -> str:
        return str(self.as_dict())
    
    __repr__ = __str__


class InventoryFile():
    """
    A dictionary type object that contains all the entries in a single YML file. Each entry is an 'InventoryEntry' object.
    """
    def __init__(self, filename: str, filepath: str, key: str, entries: typing.Dict[str, InventoryEntry]):
        self.filename: str = filename
        """Name of the file containing the inventory"""

        self.filepath: str = filepath
        """Absolute path to the YML file containing the inventory"""

        self.key: str = key
        """The key used to index this object from the GraphInventory object"""

        self.entries: typing.Dict[str, InventoryEntry] = entries
        """A mapping of entry name -> object representing information about the entry"""

    def as_dict(self) -> typing.Dict:
        dict_entries: typing.Dict = {}

        for e in self.entries.keys():
            dict_entries[e] = self.entries[e].as_dict()

        return {
            "filename": self.filename,
            "filepath": self.filepath,
            "key": self.key,
            "inventoryEntries": dict_entries
        }

    def __str__(self) -> str:
        return str(self.as_dict())
    
    __repr__ = __str__


class GraphInventory:
    """
    Class the represents a registry of all inventory yaml files loaded by GraphEx for use in the UI sidebar panel.
    Each individual file that needs to be used as an inventory is added as its own 'InventoryFile' object.
    Then each 'yaml_block' parsed from the individual YML files becomes its own 'InventoryEntry'.
    This hierarchy allows individual yaml_blocks to be instanced as objects by retrieving a node that can create or produce the desired object.
    """

    def __init__(self, dir_path: str, registry: GraphRegistry, print_loading_msg: bool = True):
        self.dir_path = os.path.abspath(dir_path)
        """The path to the inventory directory."""

        if print_loading_msg:
            print(f"Loading Inventory from directory: {self.dir_path}")

        self.registry = registry
        """A reference to the registry containing all the nodes"""

        if not os.path.isdir(self.dir_path):
            raise Exception(f"Path to inventory files must be a directory! Provided path is not to a directory: {self.dir_path}")

        self.inventory_files: typing.Dict[str, InventoryFile] = {}
        """A mapping of last_dir/filename -> yaml content"""

        self.content_nodes: typing.List[typing.Type["Node"]] = []
        """Any previously generated nodes created by the function call: create_content_nodes"""

        for root, dirs, files in os.walk(self.dir_path):
            for filename in files:
                if not filename.endswith('.yml') and not filename.endswith('.yaml'):
                    continue
                f_path = os.path.join(root, filename)
                f_contents = ""
                try:
                    with open(f_path, mode="r") as f:
                        f_contents = f.read()
                except Exception as e:
                    raise RuntimeError(f'Failed to read inventory file contents "{f_path}": {str(e)}')
                
                try:
                    yaml_contents = parse_yml(f_contents)
                except Exception as yaml_error:
                    yaml_error_str = ("\n" + " " * 29).join(str(yaml_error).split("\n"))
                    raise RuntimeError(
                        f'Failed to parse inventory file "{f_path}":\n    - Not a valid YAML file: {str(yaml_error_str)}.'
                    )
                
                entries: typing.Dict[str, InventoryEntry] = {}
                for yaml_block in yaml_contents:
                    if "Name" not in yaml_block:
                        raise Exception(f"Inventory entry has no 'Name' key to associated the inventory entry by! Add the key 'Name' (case sensitive) to the inventory file: {f_path} with the yaml content: {yaml_block}")
                    
                    block_name = yaml_block["Name"]
                    entries[block_name] = InventoryEntry(entry_name=block_name, yaml_content=yaml_block, registry=self.registry)
                    
                key: str = os.path.basename(root) + '/' + filename
                self.inventory_files[key] = InventoryFile(filename, f_path, key, entries)

        if print_loading_msg:
            print("Inventory loaded successfully.")

    def as_dict(self) -> typing.Dict:
        files_as_dict: typing.Dict = {}

        for i in self.inventory_files.keys():
            files_as_dict[i] = self.inventory_files[i].as_dict()

        return {
            "dir_path": self.dir_path,
            "inventory_files": files_as_dict
        }

    def __str__(self) -> str:
        return str(self.as_dict())
    
    __repr__ = __str__

    def create_content_nodes(self, auto_register: bool = True, print_registered_amount: bool = False) -> typing.List[typing.Type["Node"]]:
        """Create all nodes for this inventory (specifically the data contents)."""

        from graphex.node import Node, NodeType
        from graphex.sockets import OutputSocket, ListOutputSocket
        
        nodes: typing.List[typing.Type["Node"]] = []


        def add_class_node(l: typing.List[typing.Type["Node"]], v: typing.Union[str, int, float, bool], datatype_str: str, hier: str, f_k: str):
            class GetInventoryVariable(Node, include_forward_link=False):
                node_type = NodeType.GENERATOR
                name = f_k + "$" + hier
                description = f"This node was created by and is associated with the inventory. The text in the box is the actual value of the inventory item and the text at the top of this node is the path to data in the inventory."
                categories = []
                datatype = self.registry.datatypes["String"] if datatype_str == "string" else self.registry.datatypes["Boolean"] if datatype_str == "boolean" else self.registry.datatypes["Number"]
                color = datatype.color

                value = OutputSocket(datatype=datatype, name="Value", description="The value of this data in the inventory.")
                is_inventory_node = True
                inventory_value = v

                def run(_obj):
                    _obj.value = v

            l.append(GetInventoryVariable)

        
        def add_class_node_for_list(l: typing.List[typing.Type["Node"]], v: typing.List[typing.Union[str, int, float, bool]], datatype_str: str, hier: str, f_k: str):
            class GetInventoryVariableList(Node, include_forward_link=False):
                node_type = NodeType.GENERATOR
                name = f_k + "$" + hier
                description = f"This node was created by and is associated with the inventory. It contains a list from the inventory. Each item in the list will appear on its own line in the textbox area. The text at the top of this node indicates both the source inventory file and the path to the data in that inventory file."
                categories = []
                datatype = self.registry.datatypes["String"] if datatype_str == "string" else self.registry.datatypes["Boolean"] if datatype_str == "boolean" else self.registry.datatypes["Number"]
                color = datatype.color

                value = ListOutputSocket(datatype=datatype, name="Value", description="The value of this data in the inventory.")
                is_inventory_node = True
                inventory_value = v

                def run(_obj):
                    _obj.value = v

            l.append(GetInventoryVariableList)


        def handle_primitive(v: typing.Any, h_str: str, f_key: str):
            if isinstance(v, str):
                add_class_node(nodes, v, "string", h_str, f_k=f_key)
            elif isinstance(v, bool):
                add_class_node(nodes, v, "boolean", h_str, f_k=f_key)
            elif isinstance(v, int) or isinstance(any, float):
                add_class_node(nodes, v, "number", h_str, f_k=f_key)
            else:
                raise Exception(f"Error creating node for inventory entry in handle_primitives (inventory.py): The type of: {h_str} is {type(v)} ... but should be a primitive value!")


        def is_array_of_primitives_of_one_type(l: typing.List):
            t: str | None = None
            for i in l:
                if isinstance(i, str):
                    if not t:
                        t = "string"
                    elif t != "string":
                        return None
                    continue
                if isinstance(i, int):
                    if not t:
                        t = "number"
                    elif t != "number":
                        return None
                    continue
                if isinstance(i, float):
                    if not t:
                        t = "number"
                    elif t != "number":
                        return None
                    continue
                if isinstance(i, bool):
                    if not t:
                        t = "boolean"
                    elif t != "boolean":
                        return None
                    continue
                return None
            return t


        def recursive_find_nodes(current_value: typing.Any, current_hierarchy_str: str, depth: int, file_key: str):
            if isinstance(current_value, list):
                for i,v in enumerate(current_value):
                    recursive_find_nodes(v, current_hierarchy_str+" -> Index#"+str(i), depth+1, file_key=file_key)
                array_datatype = is_array_of_primitives_of_one_type(current_value)
                if array_datatype:
                    add_class_node_for_list(nodes, current_value, array_datatype, current_hierarchy_str, file_key)
            elif isinstance(current_value, dict):
                for k,v in current_value.items():
                    h_str = current_hierarchy_str + " -> " + str(k)
                    recursive_find_nodes(v, h_str, depth+1, file_key=file_key)
            else:
                handle_primitive(current_value, current_hierarchy_str, f_key=file_key)

        for f in self.inventory_files.values():
            for entry in f.entries.values():
                entry_name: str = entry.entry_name
                for sub_entry_name, any in entry.content.items():
                    hierarchy_str: str = entry_name + " -> " + sub_entry_name
                    recursive_find_nodes(any, hierarchy_str, 0, file_key=f.key)

        self.content_nodes = nodes
        if auto_register:
            for n in nodes:
                self.registry.register_node(n, "GraphEx Inventory")
            if print_registered_amount:
                print(f"Registered: {len(nodes)} nodes from inventory file path: {self.dir_path}")

        return nodes
