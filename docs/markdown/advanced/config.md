# Configuration Files

Graphex has the ability to use an external configuration file to provide values that are normally given on the Command Line Interface (CLI). This includes specifying plugins and prepopulating 'Graph Input' values. These external configuration files can provide 'global' overrides to inputs (effecting all files run on that Graphex instance) and individual overrides to graph specific inputs.

Information on specifying plugins is originally discussed [in the document on running Graphex](../setup/running.md). Information on 'Graph Inputs' is originally discussed [in the document on the Sidebar Panel](../ui/sidebar.md).

## Format

GraphEx configuration files use the YAML (Yet Another Markup Language) format. You can name the file whatever you want. The file must end in the '.yml' extension and must be provided to Graphex when running either the server or an individual graph file.

An example YML configuration file could look something like this:
```yml
# Comments can be provided by starting the line with a hash mark (#)
# This value changes the name of tab shown in the browser when connected to a GraphEx server
title: "My GraphEx Browser Tab Name"

# Plugins needed for executing the graphs (so you don't have to specify -l on the CLI)
# Notice that YML files are "indent" sensitive
plugins:
  - graphex_esxi_utils
  - some_other_graphex_plugin

# This option tells GraphEx where to point the root directory (-r flag)
root: "."

# This option instructs the GraphEx server on which certificates to serve (-s flag)
ssl_certificates_path: "/path/to/ssl/certs/directory"

# This option provides a directory of inventory YML files to GraphEx for use in the sidebar panel
# This can be pointed to a directory containing directories
inventory_path: "/path/to/directory/with/inventory/files"

# Optional path to a text file containing the password to unlock the secrets vaulted in this file
# For more information read the GraphEx documentation or run: 'python3 -m graphex vault' for the vault help menu
vault_password_path:

# Configurable amount of logs to retain before removing the old ones and replacing them with new ones
log_rollover_amount: 20

# Custom values for running graphs
graph_inputs:
  "*":
    "MyStringGraphInput": "a String value for my input"
  "my_graph_filename":
    "MyBooleanGraphInput": true,
    "MyNumberGraphInput": 123

# You can copy/paste secrets from the command line and add them to your configuration file or
# you can use the 'vault' mode of GraphEx to have it create + store the encrypted values in the configuration file for you
secrets:
  nameOfMySecret: 12343453456576867897698
```

Providing the plugins in the configuration file removes the need to specify them each time you would run Graphex (you would specify the configuration file instead). Plugins should be provided as a list of each plugin that you have installed on your system.

All items under "graph_inputs" should either be the star ('\*') character or the name of an individual graph. The star ('\*') character (also called a wildcard) represents _every_ graph that will be run while being used by a Graphex instance.

Provide the name of each Graph Input as they would appear in the Sidebar Panel of the graph they occur in (also will be shown in the help menu on the CLI). Only primitive values can be provided, as explained [in the document on the Sidebar Panel](../ui/sidebar.md). The primitive value provided in the YML file must match the data type specified in the graph file. Use quotation marks around _String_ types and write either 'true' or 'false' for _Boolean_ values (no quotation marks).

For more information on secrets, [see this dedicated document on them.](secrets.md)

$important$ The number of indents/tabs/spaces in a YML file are important. Pay attention to formatting and quotation mark usage.

## Composite Inputs

Version 1.7.0 of GraphEx introduced 'Composite Inputs'. These are graph inputs that can be used to provide data for the instantiation of certain objects (i.e. they allow you to run graphs requiring objects as inputs directly (in the UI)). Please note that the developer of the object must first allow the specific object to be a 'Composite Input' in their code before you can use that object in this manner.

Objects that allow 'Composite Inputs' can have the values required for them defined in your configuration file. These inputs are provided similar to the way you would put a normal graph input into the configuration file (under the 'graph_inputs' key in the configuration file). For example:

```yml
# ...
graph_inputs:
  "*":
    MySSHConnectionGraphInputName:
      datatype: "SSH Connection"
      values:
        IP: "1.2.3.4"
        Username: "user"
        Password:
          from_secret: nameOfMySecret
        Retries: 5
        RetryDelay: 10
# ...
```

In the above example, we can see a composite graph input defined as: 'MySSHConnectionGraphInputName'. Just like a normal graph input, this name is the name that you will assign to the graph input in the sidebar panel of the UI. You can also see the name is nested underneath '*', which means the _values_ of this composite input will be available and assigned to any graph that attempts to use the name 'MySSHConnectionGraphInputName' in GraphEx.

Different from a normal graph input: you will notice the 'datatype' and 'values' keys nested underneath the name of the graph input. This is an easy way to identify a composite graph input in a configuration file. The 'datatype' key is (and must be) assigned to the name of the object type it references to (in this case, an object representing an SSH Connection). The "values" key has nested underneath it the names and values of the individual primitive fields requested by the composite graph input. The key 'from_secret' can be provided underneath an individual value to indicate that it is going to use an existing secret (underneath "secrets" in the configuration file) instead of specifying a value here in this section.

As a further example, take a look at this real example of an 'ESXi SSH Connection' (added via a plugin) that accepts a composite graph input:

![An empty composite graph input](../images/composite_graph_inputs.png)

The graph 'execute_ssh_cmd.gx' expects as an input an object of type 'SSHConnection'. We can see that instead of preventing us from executing the graph (the standard behavior in GraphEx when objects are required as inputs) the UI prompts us to enter a 'Composite Input' called 'SSHConnection' (because the developer of 'SSH Connection' overwrote this behavior). The name 'SSHConnection' here is the 'MySSHConnectionGraphInputName' as described two paragraphs ago. The developer of 'SSH Connection' decided that the following fields are required to be provided in order to create a SSH Connection: 'IP', 'Username', and 'Password'. Additionally, the 'Retries' and 'RetryDelay' are provided to the user to change as they please.

Now our configuration file example of a 'Composite Input' should make more sense. We are specifying in the configuration file what values we want to 'auto fill' for the fields being asked of 'MySSHConnectionGraphInputName' (or 'SSHConnection' in the image). Other than the 'composite' nature of these inputs in the UI, they function just like other graph inputs would (e.g. help bubbles, error messages, etc.).

If you have a 'hierarchy' of graphs that execute each other, it would be a good idea to name all of your 'SSH Connection' graph inputs with the same name (e.g. SSHConnection). Then you could fill out your configuration file in the manner shown in the above example. Afterward, anyone that wanted to execute a subgraph requiring a SSHConnection input would have the connection information autofilled (regardless of which subgraph they wanted to run).

## Graph Input Precendence

By now you may have noticed that there are at least three different places for you to provide values to Graph Inputs:

1. The 'Run Popup Modal' in the UI or as arguments on the CLI
2. In a configuration file
3. By checking the 'Default Value' checkbox and providing a value in the popup modal for creating a Graph Input (Sidebar Panel)

If providing multiple values in some combination of the above: the actual value of the graph input will be applied in the order shown above (from top to bottom). This means the 'Default Value' will always be overwritten if one of the other two options are provided.

Graph Inputs must have one of the above provided in order for the graph to run. An error/exception is thrown/raised if all three places are missing a value.

## What Configuration File Am I Using?

The path to the current configuration file in use by the server can be found in the client UI's [Menu Bar](../ui/menubar.md) via 'Help' -> 'About Graphex'.

## Deprecated JSON Files

GraphEx used to support the JSON (JavaScript Object Notation) format. This usage is no longer supported after v1.4.

An example JSON configuration file used to look something like this:
```json
{
    "title": "My GraphEx Browser Tab Name",
    "plugins": ["graphex_esxi_utils", "other_plugin_name"],
    "graph_inputs": {
        "*" {
            "MyStringGraphInput": "a String value for my input" 
        },
        "my_graph_filename": {
            "MyBooleanGraphInput": true,
            "MyNumberGraphInput": 123
        }
    }
}
```

Please convert any old JSON style configuration files in to the YML file.

## Moving On

You can read about [providing custom SSL certificates to GraphEx](../advanced/ssl.md) or there is [one more page on frequently asked questions](../other/faq.md), if you are interested.


[Or, Return to Main Page](../index.md)