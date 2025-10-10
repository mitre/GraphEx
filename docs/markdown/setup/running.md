# Running Graphex

Graphex is run via the command line interface (CLI) as a python module. A built in help menu is available to assist you in providing arguments to the module.

The help menu can be reached by running:
```
python3 -m graphex -h
```

You will notice that there are two primary options/modes: serve and run. The serve option creates a webserver that can be connected to via a browser and provides you with a User Interface (UI) in which to plot (and run) graphs with. The run option lets you run a previously created graph without a UI.

More comprehensive help for each option can be found by chaining the help flag, e.g.:
```
python3 -m graphex serve -h
python3 -m graphex run -h
```

## Common Arguments

There are some arguments that can be provided to both the 'serve' and 'run' options:
- '-h' or '--help' to retrieve a list of all arguments/flags you can provide to your current option (serve or run)
- '-l' or '--plugins' to provide a comma-separated list of plugins to load
- '-c' or '--config' to provide a configuration file (discussed further [in the document on configuration files](../advanced/config.md))
- '-r' or '--root' to tell Graphex to use a different directory for file storage (default is the current directory)
- '-e' or '--errors' to increase the verbosity of error messages (enabling a stack trace in python)
- '-inv' or '--inventory_path' to provide the directory containing inventory files to GraphEx

Provide the arguments following either the 'serve' or 'run' option. For example, if I wanted to provide two plugins to Graphex:
```
python3 -m graphex serve --plugins graphex_esxi_utils, some_other_graphex_plugin
```

$warning$ External plugin code and documentation can't be verified to be safe to use by GraphEx itself. Verify that the plugin you are installing is safe before providing it as an argument to GraphEx.

## Serve

The 'serve' option is the primary way you will interface with Graphex. This option will create a web server on the machine it is run from. This server can be reached from any other computer that can access the computer that the server is running on.

Any computer with a connection can then act as a client to the server. The client receives a UI that lets the user plot nodes on graphs. As the user, you can save plotted graphs to the server or download them to your local machine. Any graph you run through the UI will be run on the server itself (as its own process).

There is currently one argument specific to the 'serve' option:
- '-p' or '--port' to provide an alternate port to run the server on (default is 8080)

It will be up to you to configure the networking so the client/server architecture works properly. If you have no need of this, you can simply run the serve command on your local computer (provide any additional arguments you desire):
```
python3 -m graphex serve
```

And then navigate to 'https://localhost:8080' in your browser. This will connect to the server you created on your local computer. If hosting the GraphEx server across a network, you would replace the words 'localhost' with the IP or hostname of the machine serving GraphEx.

$note$ Some plugins may not function properly from a user machine. One such example is the ESXi plugin: Graphex should be served from an Ubuntu agent located on a virtual machine (VM) inside of the ESXi instance.

## Run

The 'run' option is used to execute graphs that have already been built via the UI using the 'serve' option. This is equivalent to running an application or python script on the CLI.

The following arguments are specific to the 'run' option only:
- '-f' or '--file' a **REQUIRED** argument that tells Graphex which file you want to run/execute
- '-v' or '--verbose' enables any logs set to the 'debug' level inside a graph
- '-o' or '--validate_only' checks the graph file for errors and then exits instead of executing 
- '-i' or '--show_inputs' logs the Graph Inputs that were provided to the graph at the top of the terminal. Inputs that were specified to be hidden will have their length replaced with asterisk ('*') characters in the output.

The 'run' option will only execute on '.gx' files (GraphEx files). These are specially formatted files that are created when you save a graph through the UI (serve option).

For example, if you wanted to run a file called 'test.gx':
```
python3 -m graphex run --file test.gx
```

Remember to provide any desired arguments.

### Providing Graph Inputs

Graph Inputs are arguments provided to an individual graph in order for it to execute. The are designated by the creator of the graph. On the command line, you will provide a graph input by the following syntax: inputName=inputValue

For example:
```
python3 -m graphex run --file name_of_graph.gx MyInput=some_value
```

If you need to provide a sequence of text with spaces (i.e. a string with spaces), you can do so by placing quotation marks around your text:
```
python3 -m graphex run -f Untitled-1.gx MyInput="Text with spaces"
```

Lists can be provided on the command line by separating each list value with a space or a comma.

Some examples:
```
python3 -m graphex run --file name_of_graph.gx SomeList=value1 value2 value3 SomeOtherList=otherValue1 etc
python3 -m graphex run --file name_of_graph.gx SomeList=value1, value2, value3
python3 -m graphex run --file name_of_graph.gx SomeList=value1,value2,value3
```

All of the examples above will give the following list to Graphex: ["value1", "value2", "value3"]. If you want to include the comma character (,) in your list, you will have to escape it with a double backslash:
```
python3 -m graphex run --file name_of_graph.gx SomeList=value1\\, value2\\, value3
python3 -m graphex run --file name_of_graph.gx SomeList=value1\\,value2\\,value3
```

If you escape the comma, GraphEx will *not* count the comma as a separator in your list. Thus the first example will create the list: ["value1,", "value2,", "value3,"] and the second example will create a list of a *a single item:* ["value1,value2,value3"].

When providing lists of strings, you do not have to "quote" the strings. The graph input was already previously defined in the UI to have a datatype of "String List". That being said, if you provide quotes of either type ("like this" or 'this'): GraphEx will remove them from the input. Thus MyInputList="abc" "def" would become simply: abc def. If you want to include quotation marks, escape them with a single backslash:
```
# evaluates to ["'value1'", "'value2'"]
python3 -m graphex run --file name_of_graph.gx SomeListWithMarks=\'value1\' \'value2\'
```

Remember that you can see a list of what graph inputs are required for a graph using "-h":
```
python3 -m graphex run -f name_of_graph.gx -h

...

GRAPH-INPUT DATATYPE    VALUE       DESCRIPTION                    
───────────────────────────────────────────────────────────────────
MyInput     String 
```

The data you provide to each graph input after the equal sign (=) must match the datatype designated in the graph (as shown under the DATATYPE column in the "-h" menu output).

Graph Inputs themselves are explained in more detail in [the section explaining the Sidebar Panel](../ui/sidebar.md).

[Return to Main Page](../index.md)