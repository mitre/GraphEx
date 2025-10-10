from graphex import Number, Boolean, String, DataContainer, Node, constants, InputSocket, ListInputSocket, OptionalInputSocket, DirectedGraph, DirectedGraphViz, VariableOutputSocket, EnumInputSocket
import typing
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import random
import math

class BarGraph(Node):
    name: str = "Create Bar Graph"
    description: str = "Creates a bar graph using the provided input options and outputs it to a PNG image file."
    hyperlink: typing.List[str] = []
    categories: typing.List[str] = ["Visualizations"]
    color: str = constants.COLOR_VIS

    data_to_graph = InputSocket(datatype=DataContainer, name="Data to Graph", description="A container mapping the 'category name' to a list of numbers to display in a bar graph. The 'key' or 'location' of each collection of data is the 'category name' (will be displayed on the y-axis). The value for each 'location' is a list of numbers. Each number in the list is a value to display in a graph of its own color in the 'category name'. The same index numbers of different 'category names' will be displayed in the same color. (e.g. if 'category name' one is cat and 'category name' two is dog then index 0 might represent average height for each species and index 1 might represent average weight. The category names would be 'cat' and 'dog'. The data container would have two 'locations': 'cat' and 'dog'. The 'cat' location would have a list of two numbers: the first number representing average height and the second representing average weight. The 'dog' location would have the data in the same order but different values).")
    group_names = ListInputSocket(datatype=String, name="Group Names", description="The name of each index as provided by the list of numbers in the 'Data to Graph' input (e.g. if index 0 of every category might represent weight, you would put 'weight' as the first item in this array). This array is only used to create the key for the data being compared (bars of the same color).")
    x_axis_label = InputSocket(datatype=String, name="X-Axis Label (Data)", description="The text to show on the 'x-axis' of the graph. This should be a label that is descriptive for all numbers provided in the 'Data to Graph' input (e.g. percentage or pounds).")
    y_axis_label = InputSocket(datatype=String, name="Y-Axis Label (Categories)", description="The text to show on the 'y-axis' of the graph. This should be a label that describes what each category name means (e.g. this axis could literally be called Categories)")
    graph_title = InputSocket(datatype=String, name="Title", description="The title to show at the top of the graph.")
    output_filename = InputSocket(datatype=String, name="Output Filename", description="The name to give to the output file", input_field="bar_graph.png")
    indicator_line = OptionalInputSocket(datatype=Number, name="Indicator Line", description="When a number is provided to this input: will created a dashed line indicating the location of this number. One example usage of this would be to show a 'maximum' value (such as 100%)")
    indicator_line_label = OptionalInputSocket(datatype=String, name="Indicator Label", description="What to call the indicator lines label in the graph key")
    annotate_values = InputSocket(datatype=Boolean, name="Annotate Values", description="When True: display the amount for each number using text overlapping the end of each bar in the graph.")
    use_percentage = InputSocket(datatype=Boolean, name="Convert to %", description="When True: will multiply all input numbers by 100 to convert them to percentages (e.g. you have percentages represented as numbers from 0.0 to 1.0) and will add a percent sign ('%') character to the labels of each graphed amount when annotated.", input_field=False)
    custom_colors = ListInputSocket(datatype=String, name="Custom Colors", description="An optional list of hexadecimal (e.g. #2ca02c) colors to assign to each bar graph. The colors will be assigned in the same order as 'Group Names'. When providing custom colors, you must provide a color for every single 'Group Name'")

    def run(self):
        data_dict: typing.Dict[str, typing.List[float]] = self.data_to_graph
        if self.use_percentage:
            for category in data_dict:
                data_dict[category] = [v * 100 for v in data_dict[category]]
        
        # Reverse the y-axis labels so that the first entry appears at the top
        categories = list(data_dict.keys())
        categories.reverse()

        # the label locations
        x = np.arange(len(categories))
        # the height of the bars
        height = 0.35

        # Calculate the width of the image based on the longest group name
        max_group_name_length = max(len(name) for name in self.group_names)
        # make sure the y-axis is always visible
        buffer = 2
        fig_width = max(10, max_group_name_length * 0.5) + buffer

        # You can change the font with this (if desired)
        # plt.rcParams['font.family'] = 'DejaVu Sans'

        fig, ax = plt.subplots(figsize=(fig_width, 6), dpi=150)

        # Dynamically create barh objects
        bars = []
        if self.custom_colors and len(self.custom_colors) > 0:
            for i, group_name in enumerate(self.group_names):
                bars.append(ax.barh(x + (i - len(self.group_names)/2) * height, 
                                    [data_dict[cat][i] for cat in categories], 
                                    height, 
                                    label=group_name,
                                    color=self.custom_colors[i % len(self.custom_colors)]))
        else:
            for i, group_name in enumerate(self.group_names):
                bars.append(ax.barh(x + (i - len(self.group_names)/2) * height, 
                                    [data_dict[cat][i] for cat in categories], 
                                    height, 
                                    label=group_name))

        if self.indicator_line:
            # Add a vertical line at the requested value
            ax.axvline(100, color='red', linestyle='--', linewidth=1, label=self.indicator_line_label if self.indicator_line_label else "Indicator Line")

        # Annotate bars with percentage values on top
        for bar_group in bars:
            for bar in bar_group:
                ax.text(bar.get_width() - 5, bar.get_y() + bar.get_height()/2, 
                        f'{int(bar.get_width())}%', va='center', ha='center', 
                        color='white', fontweight='bold')
                
        ax.set_ylabel(self.y_axis_label)
        ax.set_xlabel(self.x_axis_label)
        ax.set_title(self.graph_title)
        ax.set_yticks(x)
        ax.set_yticklabels(categories)
        ax.legend()

        # Adjust layout to make sure everything fits into the figure area
        plt.tight_layout()

        # Save the figure as a PNG file
        plt.savefig(self.output_filename)


class StartDirectedGraph(Node):
    name: str = "Start Directed Graph"
    description: str = "Starts a directed graph by creating the first point (node) in the graph."
    hyperlink: typing.List[str] = []
    categories: typing.List[str] = ["Visualizations", "Directed Graph"]
    color: str = constants.COLOR_VIS

    start_label = InputSocket(datatype=String, name="Start Label", description="The label (display name) of the first node in the graph.")

    graph_output = VariableOutputSocket(datatype=DirectedGraph, name="Directed Graph", description="An object representing the graph with the first (root) node/point in it.")

    def run(self):
        # Create a directed graph
        G = DirectedGraphViz()
        # Root node
        G.add_node(self.start_label)
        G.set_root_node(self.start_label)

        self.graph_output = G


class DirectedGraphAddEdge(Node):
    name: str = "Add Edge/Connection to Directed Graph"
    description: str = "Connects an existing node in the directed graph to a new node and creates an edge pointing from one to the other."
    hyperlink: typing.List[str] = []
    categories: typing.List[str] = ["Visualizations", "Directed Graph"]
    color: str = constants.COLOR_VIS

    existing_graph = InputSocket(datatype=DirectedGraph, name="Existing Graph", description="The graph to add new node and edge to.")
    start_label = InputSocket(datatype=String, name="Existing Node Label", description="The label of an existing node in the directed graph.")
    end_label = InputSocket(datatype=String, name="New Node Label", description="The label to give to the new node in the graph.")

    graph_output = VariableOutputSocket(datatype=DirectedGraph, name="Directed Graph", description="An object representing the current directed graph.")

    def run(self):
        G = self.existing_graph
        G.add_edge(self.start_label, self.end_label)
        self.graph_output = G


class PlotDirectedGraph(Node):
    name: str = "Plot Directed Graph"
    description: str = "Outputs the provided Directed Graph object to a PNG file for visualization."
    hyperlink: typing.List[str] = ["https://networkx.org/documentation/stable/reference/drawing.html#module-networkx.drawing.layout"]
    categories: typing.List[str] = ["Visualizations", "Directed Graph"]
    color: str = constants.COLOR_VIS

    existing_graph = InputSocket(datatype=DirectedGraph, name="Existing Graph", description="The graph to visualize.")
    graph_title = InputSocket(datatype=String, name="Title", description="The title of the directed graph visualization.")
    output_filename = InputSocket(datatype=String, name="Output Filename", description="The name to give to the output file", input_field="directed_graph.png")
    hierarchical = InputSocket(datatype=Boolean, name="Hierarchical?", description="Whether to arrange the data in a 'tree' style hierarchy or not (if False, uses 'Spacing Algorithm'). This value is overwritten by 'Radial Hierarchy?' This plotting style works better on graphs with smaller node sizes and labels.", input_field=True)
    radial = InputSocket(datatype=Boolean, name="Radial Hierarchy?", description="Whether to arrange the data in a 'circular' or 'radial' style hierarchy or not (if False, uses 'Spacing Algorithm'). This value will overwrite standard 'Hierarchical?'", input_field=True)
    node_size = InputSocket(datatype=Number, name="Node Size", description="The size of the nodes in the graph. Make this bigger to encapsulate the labels with bigger circles.", input_field=1000)
    font_size = InputSocket(datatype=Number, name="Font Size", description="The size of the font of each of the labels", input_field=10)
    custom_spacing = EnumInputSocket(datatype=String, name="Spacing Algorithm", description="The spacing algorithm to use. This will be ignored when 'Hierarchical?' is set to True. Note that Bipartite assumes there is some binary structure from which to build from and may have strange results otherwise.", enum_members=["Arf", "Circular", "ForceAtlas2", "Planar", "Random", "Shell", "Spring", "Spectral", "Spiral"], input_field="Spring")
    label_colors = InputSocket(datatype=String, name="Label Colors", description="The color (hexidecimal) to assign the labels on top of the nodes in the graph.", input_field="#000000")
    custom_colors = ListInputSocket(datatype=String, name="Custom Colors", description="An optional list of hexadecimal (e.g. #2ca02c) colors to assign to each layer of the directed graph.")

    def run(self):
        G = self.existing_graph
        root_label = G.get_root_node()

        # def hierarchy_pos(G, root=None, width=1., vert_gap=0.2, hor_gap=0.5, vert_loc=0, xcenter=0.5):
        #     def _hierarchy_pos(G, root, width=1., vert_gap=0.2, hor_gap=0.5, vert_loc=0, xcenter=0.5, pos=None, parent=None):
        #         if pos is None:
        #             pos = {root: (xcenter, vert_loc)}
        #         else:
        #             pos[root] = (xcenter, vert_loc)
        #         children = list(G.neighbors(root))
        #         if not isinstance(G, nx.DiGraph) and parent is not None:
        #             children.remove(parent)

        #         if len(children) != 0:
        #             total_width = width * len(children) + hor_gap * (len(children) - 1)
        #             nextx = xcenter - total_width / 2 + width / 2
        #             for child in children:
        #                 child_width = width / len(children)
        #                 pos = _hierarchy_pos(G, child, width=child_width, vert_gap=vert_gap, hor_gap=hor_gap, vert_loc=vert_loc-vert_gap, xcenter=nextx, pos=pos, parent=root) #type:ignore
        #                 nextx += child_width + hor_gap
        #         return pos

        #     return _hierarchy_pos(G, root, width, vert_gap, hor_gap, vert_loc, xcenter)

        def hierarchy_pos(G, root=None, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5):
            '''
            From Joel's answer at https://stackoverflow.com/a/29597209/2966723.  
            Licensed under Creative Commons Attribution-Share Alike 
            
            If the graph is a tree this will return the positions to plot this in a 
            hierarchical layout.
            
            G: the graph (must be a tree)
            
            root: the root node of current branch 
            - if the tree is directed and this is not given, 
            the root will be found and used
            - if the tree is directed and this is given, then 
            the positions will be just for the descendants of this node.
            - if the tree is undirected and not given, 
            then a random choice will be used.
            
            width: horizontal space allocated for this branch - avoids overlap with other branches
            
            vert_gap: gap between levels of hierarchy
            
            vert_loc: vertical location of root
            
            xcenter: horizontal location of root
            '''
            if not nx.is_tree(G):
                raise TypeError('cannot use hierarchy_pos on a graph that is not a tree')

            if root is None:
                if isinstance(G, nx.DiGraph):
                    root = next(iter(nx.topological_sort(G)))  #allows back compatibility with nx version 1.11
                else:
                    root = random.choice(list(G.nodes))

            def _hierarchy_pos(G, root, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, pos = None, parent = None):
                '''
                see hierarchy_pos docstring for most arguments

                pos: a dict saying where all nodes go if they have been assigned
                parent: parent of this branch. - only affects it if non-directed

                '''
            
                if pos is None:
                    pos = {root:(xcenter,vert_loc)}
                else:
                    pos[root] = (xcenter, vert_loc)
                children = list(G.neighbors(root))
                if not isinstance(G, nx.DiGraph) and parent is not None:
                    children.remove(parent)  
                if len(children)!=0:
                    dx = width/len(children) 
                    nextx = xcenter - width/2 - dx/2
                    for child in children:
                        nextx += dx
                        pos = _hierarchy_pos(G,child, width = dx, vert_gap = vert_gap, 
                                            vert_loc = vert_loc-vert_gap, xcenter=nextx, #type:ignore
                                            pos=pos, parent = root)
                return pos

                    
            return _hierarchy_pos(G, root, width, vert_gap, vert_loc, xcenter)

        def get_node_depths(G, root):
            depths = {}
            queue = [(root, 0)]
            while queue:
                node, depth = queue.pop(0)
                depths[node] = depth
                for neighbor in G.neighbors(node):
                    queue.append((neighbor, depth + 1))
            return depths
        
        if self.radial:
            pos = hierarchy_pos(G, root_label, width = 2*math.pi, xcenter=0)
            pos = {u:(r*math.cos(theta),r*math.sin(theta)) for u, (theta, r) in pos.items()}
            # nx.draw(G, pos=new_pos, node_size = 50)
            # nx.draw_networkx_nodes(G, pos=new_pos, nodelist = [0], node_color = 'blue', node_size = 200)
        elif self.hierarchical:
            pos = hierarchy_pos(G,root_label)
            # nx.draw(G, pos=pos, with_labels=True)
            # plt.savefig('hierarchy.png')
        else:
            if self.custom_spacing == "Arf":
                pos = nx.arf_layout(G) #type:ignore
            # elif self.custom_spacing == "Bipartite":
            #     # Assume you have a way to determine which nodes belong to the first partition
            #     top_nodes = set(n for n, d in G.nodes(data=True) if d.get('bipartite') == 0)
            #     pos = nx.bipartite_layout(G, top_nodes)
            # elif self.custom_spacing == "BFS":
            #     pos = nx.bfs_tree(G, source=root_label)
            elif self.custom_spacing == "Circular":
                pos = nx.circular_layout(G)
            elif self.custom_spacing == "ForceAtlas2":
                pos = nx.forceatlas2_layout(G) #type:ignore
            # elif self.custom_spacing == "Kamada-Kawai":
            #     pos = nx.kamada_kawai_layout(G)
            elif self.custom_spacing == "Planar":
                pos = nx.planar_layout(G)
            elif self.custom_spacing == "Random":
                pos = nx.random_layout(G)
            elif self.custom_spacing == "Shell":
                pos = nx.shell_layout(G)
            elif self.custom_spacing == "Spring":
                pos = nx.spring_layout(G)
            elif self.custom_spacing == "Spectral":
                pos = nx.spectral_layout(G)
            elif self.custom_spacing == "Spiral":
                pos = nx.spiral_layout(G)
            # elif self.custom_spacing == "Multipartite":
            #     pos = nx.multipartite_layout(G)
            else:
                pos = nx.spring_layout(G)  # Default to spring layout if no match

        depths = get_node_depths(G, root_label)
        colors = ['#ADD8E6', '#90EE90', '#F08080', '#FFB6C1']
        if self.custom_colors and len(self.custom_colors) > 0:
            colors = self.custom_colors
        node_colors = [colors[depths[node] % len(colors)] for node in G.nodes()]

        max_depth = max(depths.values())
        num_nodes = len(G.nodes())
        fig_width = max(10, num_nodes / 2)
        fig_height = max(8, max_depth * 1.5)

        plt.figure(figsize=(fig_width, fig_height))
        nx.draw(G, pos, with_labels=True, node_size=self.node_size, node_color=node_colors, font_size=self.font_size, font_weight='bold', arrows=True, font_color=self.label_colors)
        plt.title(self.graph_title)

        plt.savefig(self.output_filename)
