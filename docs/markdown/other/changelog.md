# Changelog

This page was created to track changes to versions of GraphEx. The changelog was created in v1.4 of GraphEx and only changes starting from that version are tracked here.

## 1.16.0

- GraphEx released as open source to the public
- Visual review of all project code with small updates to documentation, typo fixes, removal of unused imports and debugging statements, etc.

## 1.15.8

- Fix newline formatting bug in "Named Format String" node

## 1.15.7

- Bugfix to load graphs that have connections to nodes that do not exist

## 1.15.5

- Fix a bug that appeared during a merge conflict resolution when a graph input was deleted from one branch

## 1.15.4

- Report error in graphs that have more than one 'Graph Start' node

## 1.15.3

- List remote branches in the Source Control pane
- Show the active repo in the Source Control pane
- Save git credentials in the Vue store
- Better error handling for invalid git credentials

## 1.15.2

- Change the terminal searchbar 'next' and 'previous' buttons to be 'up' and 'down' arrows instead of 'left' and 'right'

## 1.15.1

- Turn off server-side debug logging and set to 'WARNING'
- Allow some CLI arguments such as "-inv" to be assigned an empty string ("") to override config file values (for compatibility with older versions of GraphEx and mixed usage of an individual configuration file)

## 1.15.0

- Add new 'Source Control' sidebar panel
- Add ability add, commit, and push changes to files from the UI
- Add ability to fetch, pull, and merge changes into the current branch from the UI
- Add ability to switch branches and create new branches from the UI
- Resolve merge conflicts from the UI

## 1.14.1

- Add back in deprecated/legacy node 'Get Nested Data Container List'

## 1.14.0

- Update icons for '.bash', '.zsh', '.gz', '.zip', '.7z', '.xz' extensions in the Files sidebar
- Create 'Data Container' nodes to handle adding and extracting primitive lists
- Lighten the color of 'Data Container' nodes to make them easier to see in the graph
- Add optional 'Ignore Dot Notation' socket input to storing and retrieval of nested Data Containers (and lists)
- Add more pip package dependencies to GraphEx for the purpose of supporting traditional graph/plotting visualizations
- Add nodes to plot graphs and output them as PNG image files in GraphEx
- Add node to sort lists
- Add more nodes for retrieval of number and boolean values from Data Containers

## 1.13.0

- Rework the 'Named Format String' to no longer work with specific datatypes and lists. Instead, the node now expects all inputs to be singular strings and makes the process of 'generating inputs' less confusing for users.
- Mark three of the other 'Format String' nodes as deprecated for future removal !!! Annotate that the normal 'Format String' isn't recommended for use
- The 'Named Format String' node now allows for the escaping of curly braces with the standard backslash character: '\'
- The 'Named Format String' node now highlights the sections in the textbox that will have text inserted into them
- Add 'List To String' node to convert Lists of all datatypes into a single string (for objects it is assumed the (plugin) object's developer implemented a toString method)
- Create 'Add Exception Handling' right-click (dropdown) menu in the editor context menu

## 1.12.2

- Fix a bug with GraphEx generating SSL certificates with the same serial number over and over (1000) on every machine running GraphEx. This resolves the error sometimes encountered in Firefox: 'SEC_ERROR_REUSED_ISSUER_AND_SERIAL'.

## 1.12.1

- Fix image links not opening in Chromium based browsers due to a new security policy on 'data' links

## 1.12.0

- Add 'forward' and 'back' buttons to the Terminal Panel searchbar
- Add 'case sensitve' search option to Terminal Panel searchbar
- Add 'match count' to the Terminal Panel searchbar (e.g. Match 1 of 'n')
- Add a filter option against the 'type' of log message to the Terminal Panel searchbar
- Add right-click option to terminal to 'export' a log in original JSON format for future 'import' on other GraphEx instances
- Rename existing right-click options to download logs to avoid confusion amongst all three available options
- Rename 'File' -> 'Open File...' to 'Open File (Client)...' and 'File' -> 'Open Log File...' to 'Open Log File (Server)...'
- Add ability to import log files using the 'File' -> 'Open File (Client)...' dialog
- Change the color and style of checkboxes to make them easier to see against dark backgrounds

## 1.11.1

- Fix bug where the yellow warning color for unused graph inputs was remaining when renaming a graph input that was un-used
- Fix bug where the UI was sometimes unable to find erroring graphs when graphs were executed inside directory structures
- Fix formatting issue with error output on the command line when verbose error logging is enabled (ID: ... was on the same line as errorLink: ...)

## 1.11.0

- Enables the import of Graph Inputs from configuration files into the currently opened graph in the editor panel
    - Use the new 'Import' button (looks like a 'download button') from the 'Configure Graph' Sidebar Panel

## 1.10.2

- Add clickable hyperlinks to the help popup of all relevant base/vanilla GraphEx nodes (for more documentation reference)
- Adds warning icons to inform the user of graphs that completed with warnings in the UI

## 1.10.1

- Fix 'sticky' behavior of dropdown menus that are nested inside each other

## 1.10.0

- Add reference finder for execute graph nodes to graph search panel

## 1.9.5

- Fix import error with typing python module

## 1.9.4

- Fix warning for default number primitive to 'light up' as a warning for '-2' instead of '-1'
- Add warning for unused data and generator nodes
- The 'Errors Panel' is renamed to the 'Errors and Warnings' Panel

## 1.9.3

- GraphEx server now uses pyopenssl to generate SSL certificates if the user doesn't specify certificates to use
- GraphEx server no longer uses 'dummy'/adhoc/single use certificates

## 1.9.2

- Fixes bug where sometimes error links couldn't be opened when left-clicking them in the UI

## 1.9.1

- Fixes issue parsing lists in yaml configuration files related to composite graph inputs

## 1.9.0

- Add new 'Inventory system' for managing static data. Paths to YML inventory files can be provided on the command line and the data itself seen from inside the UI. The data is displayed in a new sidebar panel and you can drag any data in 'boxes' out into the editor panel to create that data in the graph. Changes to the data specified in the YML files will automatically update the values in existing graphs.
- New List Compression Loop
- Index number indicators next to individual items fed into a list input socket
- Changes the sidebar icon for 'Graph Search' to hopefully cut back on confusion between the nodes panel and the graph search panel
- Changes the sidebar icon for 'Variables' back to 'ABC'
- Verbose error mode now raises more exceptions with stack traces during program initialization
- Enables the use of *List* 'Variable Output Sockets' for developers to create 'Save to Variable' checkboxes
- Adds 'Warnings' to the Errors Panels and yellow icon color to itself and the Graph Input Panel (for unused inputs)
- More right-click menu options for the editor panel to quickly create common nodes

## 1.8.1

- Strip white space from subprocess stdout and stderr 

## 1.8.0

- Add subprocess node for running command on machine serving graphex server or machine running graph.

## 1.7.1

- Fix bug causing socket edges to overlap help popup modals in the editor

## 1.7.0

- Add functionality to GraphEx that allows for graphs with objects as inputs to be run from the GraphEx UI. This feature must be implemented by the developer of the object in order for it to be usable by users (on a per object basis).

## 1.6.8

- Developer only patch: more groundwork towards git functionality in GraphEx UI

## 1.6.7

- Developer only patch: groundwork towards git functionality in GraphEx UI

## 1.6.6

- Move the git and virtual environment info to the top menu bar.

## 1.6.5

- Add Copy, cut, and paste options in the context menu for input fields

## 1.6.4

- The 'vault' mode on the CLI will now allow you to continue to input new secrets if you want it to

## 1.6.3

- Fixed a bug with the breakpoint node not logging graph inputs or variables if 'end program' was unchecked

## v1.6.2

- Adds a button to reset default value in the Run Graph modal
- Adds icon to show which default values have been updated

## v1.6.1

- Fixes bug with return type in the configuration file causing the server to crash on Ubuntu

## v1.6

- Adds a new Node Help component with clickable links to external documentation
- Adds hyperlinks to node metadata

## v1.5

- Graph Inputs are are now arranged in the sidebar under the the category in which they are configured for

## v1.4

- Introduces the 'vault' mode on the command line
    - Adds the ability to encrypt Graph Inputs to hide sensitive information (such as passwords) in both the configuration file and the UI
- Removes JSON as an option for configuration files (use YML instead)
- Documentation on 'Change Log' created (this one)
- Documentation on 'Secrets'created


[Return to Main Page](../index.md)