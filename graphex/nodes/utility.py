from graphex import Node, LinkOutputSocket, OptionalInputSocket, String
from graphex import constants


class Sequence2(Node, include_forward_link=False):
    name = "Sequence (2)"
    description = "Execute two events in order."
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    first_event = LinkOutputSocket(name="First Event", description="The first event.")
    second_event = LinkOutputSocket(name="Second Event", description="The second event. This will only execute after the first event has completed.")

    def run(self):
        pass

    def run_next(self):
        for node in self.forward("First Event"):
            self._runtime.execute_node(node)

        for node in self.forward("Second Event"):
            self._runtime.execute_node(node)


class Sequence3(Node, include_forward_link=False):
    name = "Sequence (3)"
    description = "Execute three events in order."
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    first_event = LinkOutputSocket(name="First Event", description="The first event.")
    second_event = LinkOutputSocket(name="Second Event", description="The second event. This will only execute after the first event has completed.")
    third_event = LinkOutputSocket(name="Third Event", description="The third event. This will only execute after the second event has completed.")

    def run(self):
        pass

    def run_next(self):
        for node in self.forward("First Event"):
            self._runtime.execute_node(node)

        for node in self.forward("Second Event"):
            self._runtime.execute_node(node)

        for node in self.forward("Third Event"):
            self._runtime.execute_node(node)


class Sequence4(Node, include_forward_link=False):
    name = "Sequence (4)"
    description = "Execute four events in order."
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    first_event = LinkOutputSocket(name="First Event", description="The first event.")
    second_event = LinkOutputSocket(name="Second Event", description="The second event. This will only execute after the first event has completed.")
    third_event = LinkOutputSocket(name="Third Event", description="The third event. This will only execute after the second event has completed.")
    fourth_event = LinkOutputSocket(name="Fourth Event", description="The fourth event. This will only execute after the third event has completed.")

    def run(self):
        pass

    def run_next(self):
        for node in self.forward("First Event"):
            self._runtime.execute_node(node)

        for node in self.forward("Second Event"):
            self._runtime.execute_node(node)

        for node in self.forward("Third Event"):
            self._runtime.execute_node(node)

        for node in self.forward("Fourth Event"):
            self._runtime.execute_node(node)


class Defer(Node, include_forward_link=False):
    name = "Defer"
    description = "Defer execution of nodes until the graph completes. This is typically used for clean-up operations. If multiple Defer nodes exist, the deferred nodes will be run in LIFO (Last In, First Out) order. Deferred nodes will be run even if the graph exits with an error."
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    defer_name = OptionalInputSocket(
        datatype=String, name="Name", description="The friendly name to give to the deferred nodes. This is only used for logging purposes."
    )

    deferred_nodes = LinkOutputSocket(name="Deferred Nodes", description="The nodes to defer execution of. These nodes will be run when the graph completes.")
    continue_nodes = LinkOutputSocket(name="Continue", description="Continue normal execution of the graph.")

    def log_prefix(self):
        if self.defer_name:
            return f"[{self.name} - {self.defer_name}] "
        else:
            return f"[{self.name}] "

    def run(self):
        pass

    def run_next(self):
        def deferred_func():
            self.debug(f"Executing deferred nodes...")
            for node in self.forward("Deferred Nodes"):
                self._runtime.execute_node(node)

        self.defer(deferred_func)

        for node in self.forward("Continue"):
            self._runtime.execute_node(node)
