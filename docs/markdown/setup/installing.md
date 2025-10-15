# Installing Graphex

Graphex is installed via package through Python's pip package manager (using the CLI (command line interface)). This package can be either downloaded or built from source via our git repository.

## Prerequisites

The following applications are required to run Graphex:
- Python (version 3.10 or greater) and pip (the python package manager)

The following applications are required if building from source:
- git
- node (v18.15.0 or greater) and npm (v9.5.0 or greater)
- make

It is also recommended that you install the application in a python virtual environment (venv). This helps ensure that different python packages (especially ones that may be critical to your system) don't have conflicts between each other.

## Installing a Released Graphex Version

GraphEx is available via pip: you can simply install the latest graphex package via:
```
python3 -m pip install --upgrade pip
python3 -m pip install mitre-graphex
```

Graphex should now be installed on your system. You can check by running:
```
python3 -m pip list
```

You should see Graphex in the list of packages installed by pip. Unix systems can grep the result for Graphex.

You can install any released Graphex plugin that is available in pip in this same way. For example, the esxi_utils plugin could be installed with:
```
python3 -m pip install graphex-esxi-utils
```

Likewise, the web automation plugin can be installed with:
```
python3 -m pip install graphex-webautomation-plugin
```

[Click here for instructions on installing plugins that aren't located in the pip feed](#installing-plugins).

At this point, 'vanilla' Graphex is installed. [Click here](running.md) to navigate to instructions on how to run Graphex.

## Building from Source

Create a python virtual environment (venv) now if you intend to use one.

Ensure you have the latest version of pip for python running the following command:
```
python3 -m pip install --upgrade pip
```

You can download this repository using git:
```
git clone https://github.com/mitre/GraphEx
```

Navigate into the folder retrieved from the server. Install the python package dependencies for Graphex by running the following command:
```
python3 setup.py install
```

Then build and install the program with make:
```
python3 -m pip install build wheel
make all
```

Graphex should now be installed on your system. You can check by running:
```
python3 -m pip list
```

You should see Graphex in the list of packages installed by pip. Unix systems can grep the result for Graphex.

At this point, 'vanilla' Graphex is installed. [Click here](running.md) to navigate to instructions on how to run Graphex or [continue to the next section for instructions on installing plugins](#installing-plugins).

### Installing Plugins

Plugins for Graphex are installed as standalone python packages. Each plugin will have its own pip (python package) dependencies that will need to be installed before the package itself can be installed. The process to install a plugin is functionally identical to the process you just followed to install Graphex.

As an example, there is a ESXi Utilities package available for graphex.

You would clone the repository (in the same way you cloned the Graphex application):
```
git clone https://github.com/mitre/GraphEx-ESXi-Utilities
```

Navigate into the folder retrieved from the server. Install the python package dependencies for the plugin by running the following command (it may error):
```
python3 setup.py install
```

If you receive an error after running this command, it is likely because you are missing a dependency for the package. This particular plugin requires the 'esxi_utils' python package (the library containing the functions to interface with ESXi). You would install it in the same manner as has been described here. You can find [esxi utils here](https://github.com/mitre/Python-ESXi-Utilities).

When you have resolved all your dependency installation errors, you can install the package itself:
```
make all
```

The plugin for Graphex should now be installed on your system. You can check by running:
```
python3 -m pip list
```

You should see both Graphex and the plugin's package name in the list of packages installed by pip. Unix systems can grep the results.

When you are done installing all your plugins, [click here](running.md) to navigate to instructions on how to run Graphex.


## Updating Graphex

Graphex and its plugins are python (pip) packages. They can be upgraded in the same manner as any other python package.

### Updating Install from a Pip Feed

Any packages installed from the feed can be upgraded through pip:
```
python3 -m pip install --upgrade graphex
# or, plugin example
python3 -m pip install --upgrade plugin_name
```

### Updating Built from Source

Any packages installed from a repository have to be re-built. First you will 'pull down' changes from the remote repository and then you will perform a fresh build and install of the package.

Navigate to the directory/folder of the package you want to upgrade (i.e. Graphex itself or any of its plugins)

First, figure out what 'git branch' you are currently on:
```
git branch --show-current
```

Typically it is called 'main', 'master', or 'release/v#'. If it isn't one of these, you are probably on a branch for development (one that may not be complete or has untested changes). Confirm that is what you want before continuing.

If you have modified the files in this branch in any way, it may interfere with the following steps. This document is going to assume you have not changed any of the files in the folder (if you have changed the files on accident, you can always clone the repo again in a new folder to avoid conflicting with the changes in the current folder).

You can check for changes to the current git directory by running:
```
git status -s
```

An unchanged directory/folder will show no output after this command.

Now 'pull down' the latest changes (replacing name_of_branch with the one you discovered earlier):
```
git pull origin name_of_branch
```

If you see the message 'Already up to date.' then there are no new updates to install. You have the latest version of the package and don't need to rebuild and reinstall.

Otherwise, rebuild and reinstall the package:
```
python3 setup.py install
make all
```

You can verify the version changed by running:
```
pip list
```

And checking that the version number changed from what it was before.


[Return to Main Page](../index.md)