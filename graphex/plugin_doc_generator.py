import typing
import os
import shutil
from re import sub

template_index_html = '''
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="../graphexStyle.css">
</head>
<body>

<h1 id="plugins-documentation-overview">Plugins Documentation Overview</h1>
<p>Welcome to the documentation index for the currently installed Graphex plugins. Developers that have provided documentation for their GraphEx plugins will appear on this page.</p>
<h2 id="plugin-documentation-catalogue">Plugin Documentation Catalogue</h2>
<p><a href="../index.html">Either you provided no plugins to this GraphEx server or the plugins you have installed aren&#39;t providing documentation at this time. Click here to return to the main GraphEx documentation.</a></p>

<h2 id="return-to-main-page">Return to Main Page</h2>
<p><a href="../index.html">Click here to return to main page of the GraphEx documentation.</a></p>
</body>
</html>
'''

def generate_plugin_doc(graphex_package_location: str, desired_rel_path_to_plugin_docs: str, paths_to_plugin_index_files: typing.Dict[str, str]):
    # this the absolute path to where the docs live in the pip package
    abs_path_to_plugin_docs_dir = os.path.join(graphex_package_location, desired_rel_path_to_plugin_docs)
    # this the absolute path to the index file we will create for plugins (for the Flask server to serve)
    abs_path_to_plugin_index = os.path.join(abs_path_to_plugin_docs_dir, "plugins_index.html")
    
    # create a string containing the anchor tags to all other docs
    doc_links: str = ""
    # iterate through all plugins that provided docs
    for plugin_name, abs_path in paths_to_plugin_index_files.items():
        print(f"Loading documentation from plugin package: {plugin_name} ...", flush=True)
        # the path to the directory containing the docs for this plugin
        plugin_docs_dir = os.path.dirname(abs_path)
        # the path where we are going to copy the plugins docs into
        copied_dir_location = os.path.join(abs_path_to_plugin_docs_dir, plugin_name)
        # where the anchor tag should point to in order to navigate to the plugin doc from the plugin index
        expected_index_rel_path = os.path.join(plugin_name, "index.html")
        # remove the path to this plugin's docs if it already exists
        if os.path.exists(copied_dir_location):
            try:
                shutil.rmtree(copied_dir_location, ignore_errors=False)
            except Exception as e:
                print(f"ERROR trying to remove old plugin documentation: {str(e)}")
        try:
            # copy the docs from the plugin into the GraphEx docs
            shutil.copytree(plugin_docs_dir, copied_dir_location)
            # create the anchor tag that will
            doc_links += f"\n<li><a href={expected_index_rel_path} target=\"_blank\"> {plugin_name} </a></li>"
        except Exception as e:
                print(f"ERROR trying to copy plugin documentation to GraphEx package: {str(e)}")

    data = template_index_html
    num_plugins = len(paths_to_plugin_index_files.keys())
    if num_plugins > 0 and doc_links:
        # replace the replace HTML string with the generated links
        data: str = sub(r'<a.+</a>', doc_links, template_index_html, count=1)

    # write out the replaced data to the file
    try:
        with open(abs_path_to_plugin_index, 'w') as f:
            f.write(data)
    except Exception as e:
        print(f"ERROR trying to write out plugin documentation (plugin_index.html) file: {str(e)}")

    if num_plugins:
        print("Finished generating plugin documentation.", flush=True)
