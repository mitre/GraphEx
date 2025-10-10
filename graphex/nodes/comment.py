from graphex import (
    InputField,
    Node,
    NodeType,
    constants,
)
import typing


class Comment(Node, include_forward_link=False, include_backward_link=False):
    node_type = NodeType.COMMENT
    name: str = "Comment"
    description: str = "A comment in the graph. This node has no impact on graph execution or control flow."
    categories: typing.List[str] = ["Miscellaneous", "Comments"]
    color: str = constants.COLOR_COMMENT
    textColor: str = constants.COLOR_COMMENT_TEXT

    field = InputField(default_value="", name="Comment...", multiline=True, required=False, floating_label=False)

    def run(self):
        pass
