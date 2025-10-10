from graphex.datatype import DataType
from graphex import constants, String
import networkx as nx

class DirectedGraphViz(nx.DiGraph):
    def set_root_node(self, label_name: str):
        self.root_node_label = label_name

    def get_root_node(self):
        return self.root_node_label if self.root_node_label else None

DirectedGraph = DataType(
    true_type=DirectedGraphViz, #type:ignore
    name="Directed Graph",
    description="An object containing a directed graph for visualization of data.",
    color=constants.COLOR_DIRECTED_GRAPH_VIZ,
    categories=["Data"],
)

@DirectedGraph.cast(to=String)
def directedGraph_to_string(value: nx.DiGraph) -> str:
    return str(value)
