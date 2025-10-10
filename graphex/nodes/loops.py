import typing
from graphex import (
    Dynamic,
    String,
    Number,
    Boolean,
    Graph,
    NodeMetadata,
    NodeDynamicAttributes,
    Node,
    InputSocket,
    ListInputSocket,
    LinkOutputSocket,
    OutputSocket,
)

from graphex.nodes.templates import DynamicInputTemplateNode
from graphex import constants, exceptions
from graphex.sockets.base import _BaseSocket


class ForLoop(Node, include_forward_link=False):
    name = "For Loop"
    description = "Iterate nodes for a given number of times."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#the-range-function"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    iterations = InputSocket(
        datatype=Number,
        name="Number of Iterations",
        description="The number of times to iterate the loop. Floating point values will be truncated to an integer.",
        input_field=10,
    )

    body = LinkOutputSocket(name="Loop Body", description="Branch for the body of the loop, to be run on each iteration.")
    index = OutputSocket(
        datatype=Number,
        name="Index",
        description="The loop index, starting from 0 to the number of iterations (not inclusive). This will be disabled when used outside the loop body.",
    )
    completed = LinkOutputSocket(name="Completed", description="Branch to run when the loop has completed.")

    def run(self):
        try:
            for i in range(0, int(self.iterations)):
                self.index = i
                try:
                    for node in self.forward("Loop Body"):
                        self._runtime.execute_node(node)
                except exceptions.LoopContinueException:
                    pass
        except exceptions.LoopBreakException:
            pass

        self.disable_output_socket("Index")

    def run_next(self):
        for node in self.forward("Completed"):
            self._runtime.execute_node(node)


class RangedForLoop(Node, include_forward_link=False):
    name = "Ranged For Loop"
    description = "Iterate nodes for each index in a given range."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#the-range-function"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    start = InputSocket(datatype=Number, name="First Index", description="A number representing the first index of the loop.", input_field=0)
    end = InputSocket(datatype=Number, name="Last Index", description="A number representing the last index of the loop (inclusive).", input_field=10)
    increment = InputSocket(datatype=Number, name="Increment", description="The amount to increment for each loop iteration.", input_field=1)

    body = LinkOutputSocket(name="Loop Body", description="Branch for the body of the loop, to be run on each iteration.")
    index = OutputSocket(datatype=Number, name="Index", description="The loop index. This will be disabled when used outside the loop body.")
    completed = LinkOutputSocket(name="Completed", description="Branch to run when the loop has completed.")

    def run(self):
        try:
            increment = self.increment or 1
            self.index = self.start
            while self.index <= self.end:
                try:
                    for node in self.forward("Loop Body"):
                        self._runtime.execute_node(node)
                except exceptions.LoopContinueException:
                    pass
                self.index = self.index + increment
        except exceptions.LoopBreakException:
            pass

        self.disable_output_socket("Index")

    def run_next(self):
        for node in self.forward("Completed"):
            self._runtime.execute_node(node)


class ForEach(DynamicInputTemplateNode, include_forward_link=False):
    name = f"For Each"
    description = "Iterate/loop for each item in a list."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#for-statements"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    list_items = ListInputSocket(
        datatype=Dynamic,
        name="List to Iterate",
        description="The list to iterate over. This can be a list of any type, and the output value of this node will depend on the type of the input list.",
    )

    def run(self):
        try:
            dynamic_attributes = self.dynamic_attributes(self._graph, self._instance_metadata)
            if dynamic_attributes.error:
                raise RuntimeError(dynamic_attributes.error)

            dynamic_sockets = {socket.name: socket for socket in dynamic_attributes.sockets or []}
            index_socket = dynamic_sockets["Index"]
            value_socket = dynamic_sockets["Value"]

            self.disable_output_socket("Index")
            self.disable_output_socket("Value")

            for index, value in enumerate(self.list_items):
                index_socket.set_value(self, index)
                value_socket.set_value(self, value)
                try:
                    for node in self.forward("Loop Body"):
                        self._runtime.execute_node(node)
                except exceptions.LoopContinueException:
                    pass
        except exceptions.LoopBreakException:
            pass

    def run_next(self):
        for node in self.forward("Completed"):
            self._runtime.execute_node(node)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            datatype = cls.get_datatype("List to Iterate", graph, instance_metadata)
            if not datatype:
                return NodeDynamicAttributes(None, None, None, None)

            return NodeDynamicAttributes(
                sockets=[
                    ListInputSocket(
                        datatype=datatype,
                        name="List to Iterate",
                        description="The list to iterate over. This can be a list of any type, and the output value of this node will depend on the type of the input list.",
                    ),
                    LinkOutputSocket(name="Loop Body", description="Branch for the body of the loop, to be run on each iteration."),
                    OutputSocket(datatype=datatype, name="Value", description="The value for this iteration of the loop."),
                    OutputSocket(datatype=Number, name="Index", description="The loop index."),
                    LinkOutputSocket(name="Completed", description="Branch to run when the loop has completed."),
                ],
                description=f"Iterate/loop for each item in a '{datatype.name}' list.",
                color=datatype.color,
                error=None,
            )
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, error=str(e))


class InfiniteLoop(Node, include_forward_link=False):
    name = "Infinite Loop"
    description = "Iterate a block of nodes indefinitely (hint: use a 'Loop Break' node to exit the loop)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/compound_stmts.html#while"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    body = LinkOutputSocket(name="Loop Body", description="Branch for the body of the loop, to be run on each iteration.")
    index = OutputSocket(
        datatype=Number,
        name="Index",
        description="The loop index. This will increment by 1 automatically for every iteration of this loop.",
    )
    completed = LinkOutputSocket(name="Completed", description="Branch to run when the loop has completed.")

    def run(self):
        try:
            self.index = 0
            while True:
                try:
                    for node in self.forward("Loop Body"):
                        self._runtime.execute_node(node)
                except exceptions.LoopContinueException:
                    pass
                self.index = self.index + 1
        except exceptions.LoopBreakException:
            pass

        self.disable_output_socket("Index")

    def run_next(self):
        for node in self.forward("Completed"):
            self._runtime.execute_node(node)


class RetryLoop(Node, include_forward_link=False):
    name = "Retry Loop"
    description = "Iterate nodes until they succeed without error or until a given number of times."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#for-statements", "https://docs.python.org/3/tutorial/errors.html#handling-exceptions"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    max_attempts = InputSocket(
        datatype=Number,
        name="Maximum Attempts",
        description="The maximum number of times to attempt to execute the given nodes. Floating point values will be truncated to an integer.",
        input_field=1,
    )
    raise_error = InputSocket(
        datatype=Boolean,
        name="Raise Error",
        description="Raise an error when all attempts have been exhausted without 'Attempt Body' succeeding. If False, no error will be raised and the 'Error Body' branch will be executed instead.",
        input_field=True,
    )

    attempt_body = LinkOutputSocket(
        name="Attempt Body",
        description="Branch for the body of the loop, to be run on each attempt until success or the maximum number of attempts is reached. An error from any node in this branch will trigger another attempt (starting from the beginning of this branch), if additional attempts remain. A 'Loop Break' node executed in this branch will be considered a success. A 'Loop Continue' node executed in this branch will be considered a failure and another attempt will be made if additional attempts remain.",
    )
    after_attempt_body = LinkOutputSocket(
        name="After Attempt",
        description="Branch to run after the 'Attempt Body' branch. This will be run between each attempt (i.e. when 'Attempt Body' fails) and after the last attempt (successful or otherwise). This may be used to clean up resources between and after attempts.",
    )
    index = OutputSocket(
        datatype=Number,
        name="Attempt Number",
        description="The current attempt number (starting from 1).",
    )
    success = OutputSocket(
        datatype=Boolean,
        name="Success",
        description="The status of the last attempt from 'Attempt Body'. If 'Attempt Body' completed successfully, this will be True. Otherwise, this will be False",
    )
    error_msg = OutputSocket(
        datatype=String,
        name="Error Message",
        description="The error message for the most recent failed attempt from 'Attempt Body'. If 'Attempt Body' completed successfully, this will be an empty string.",
    )
    failure_body = LinkOutputSocket(
        name="On Failure",
        description="Branch to run when all attempts have failed and 'Raise Error' is False. It may be assumed that 'Success' is False and all attempts have been exhausted whenever this is run.",
    )
    completed = LinkOutputSocket(
        name="Completed",
        description="Branch to run when this node has completed. When 'Raise Error' is True, this will only run after 'Attempt Body' has completed successfully. When 'Raise Error' is False and an error still exists after all attempts, this will be run after the 'On Failure' branch.",
    )

    def run(self):
        self.index = 1
        self.error_msg = ""
        self.success = False
        error = None
        for i in range(1, int(self.max_attempts) + 1):
            error = None
            self.index = i

            try:
                for node in self.forward("Attempt Body"):
                    self._runtime.execute_node(node)
            except exceptions.LoopContinueException:
                error = RuntimeError(f"Loop Continue")
            except exceptions.LoopBreakException:
                pass
            except Exception as e:
                error = e

            self.error_msg = str(error) if error else ""
            self.success = not error
            for node in self.forward("After Attempt"):
                self._runtime.execute_node(node)

            if not error:
                break

        if error and self.raise_error:
            raise error
        elif error:
            for node in self.forward("On Failure"):
                self._runtime.execute_node(node)

    def run_next(self):
        for node in self.forward("Completed"):
            self._runtime.execute_node(node)


class LoopBreak(Node, include_forward_link=False):
    name = "Loop Break"
    description = "Terminate the current loop early."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#break-and-continue-statements-and-else-clauses-on-loops"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    def run(self):
        raise exceptions.LoopBreakException()


class LoopContinue(Node, include_forward_link=False):
    name = "Loop Continue"
    description = "Continue to the next iteration of a loop instantaneously. Warning: This will completely skip over any remaining branches of execution (e.g. finally blocks) and return directly to the closest loop."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#break-and-continue-statements-and-else-clauses-on-loops"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    def run(self):
        raise exceptions.LoopContinueException()


class ListCompressionLoop(DynamicInputTemplateNode, include_forward_link=False):
    name: str = "List Compression Loop"
    description: str = "Takes as input multiple lists treats them as a single list containing an output value from each list. Immediately iterates over the compressed combination of the provided lists. Will iterate until the length of the shortest list provided. The value chosen from each list is the dependent upon the insertion order of the lists (e.g. the first value of list 1 and the first value of list 2 will appear in the output for each iteration of the loop). When inventory nodes are connected to this node, the output socket name will update to: 'List #... (Path string)' to match the name of the first index connected to the list input socket. This makes it easier to identify which values are available from that particular list. Don't worry about the order of the output socket values (e.g. 'List #1 Value') looking strange while you are configuring this node. This node will properly re-format itself when the file it lives in is closed and reopened." 
    categories = ["Control Flow"]
    color: str = constants.COLOR_CONTROL_FLOW

    # Lets the UI know that this node can have input sockets added/subtracted via a button
    allows_new_inputs = True

    def run(self):
        try:
            dynamic_attributes = self.dynamic_attributes(self._graph, self._instance_metadata)
            if dynamic_attributes.error:
                raise RuntimeError(dynamic_attributes.error)

            # all the dynamic sockets
            sockets = dynamic_attributes.sockets or []
            # the socket for the current index
            index_socket = {socket.name: socket for socket in dynamic_attributes.sockets or []}["Index"]
            # the length of the shortest input list
            min_length = None

            # compute the length of the shortest list
            for s in sockets:
                if s.is_input and s.is_list:
                    l = len(s.get_value(self))
                    if not min_length:
                        min_length = l
                    elif l < min_length:
                        min_length = l
                elif not s.is_input and not s.name == '_forward':
                    self.disable_output_socket(s.name)

            if not min_length:
                min_length = 0

            # step through each iteration of the loop
            for i in range(min_length):
                index_socket.set_value(self, i)
                self.enable_output_socket(index_socket.name)
                for s in sockets:
                    # the socket must be a data output socket and it can't be the index socket
                    if not s.is_input and not s.is_link and s.name != "Index":
                        input_name: str = s.name[:s.name.rfind('Value') - 1]
                        s.set_value(self, self.get_input(input_name, self._graph, self._instance_metadata).get_value(self)[i])
                        self.enable_output_socket(s.name)
                try:
                    for node in self.forward("Loop Body"):
                        self._runtime.execute_node(node)
                except exceptions.LoopContinueException:
                    pass
        except exceptions.LoopBreakException:
            pass

        try:
            self.disable_output_socket(index_socket.name)
        except Exception:
            pass

    def run_next(self):
        for node in self.forward("Completed"):
            self._runtime.execute_node(node)

    @classmethod
    def dynamic_attributes(cls, graph: Graph, instance_metadata: NodeMetadata) -> NodeDynamicAttributes:
        try:
            sockets: typing.List[_BaseSocket] = [
                LinkOutputSocket(name="Loop Body", description="Branch for the body of the loop, to be run on each iteration."),
                OutputSocket(datatype=Number, name="Index", description="The loop index.")
            ]
            counter = 0
            for s in instance_metadata.get("inputs", []):
                if s['name'] != '_backward':
                    datatype = cls.get_datatype(s['name'], graph, instance_metadata)
                    if not datatype:
                        sockets.append(ListInputSocket(datatype=Dynamic, name=s['name'], description="Connect a list or several individual items of the same type to this input socket. The individual values will be available via each step in the iteration."))
                    else:
                        # adding the list input socket with the same name overwrites the original 'default' socket on the node
                        # This effectively makes the color match the input color
                        sockets.append(ListInputSocket(datatype=datatype, name=s['name'], description="The individual values of this list will be available via each step in the iteration."))
                        output_socket_name: str = f"{s['name']} Value"
                        sockets.append(OutputSocket(datatype=datatype, name=output_socket_name, description=f"The value of the input list called '{s['name']}' at the current index in the loop will be available here."))
                    counter += 1

            sockets.append(LinkOutputSocket(name="Completed", description="Branch to run when the loop has completed."))

            return NodeDynamicAttributes(sockets, None, None, None)
        except Exception as e:
            return NodeDynamicAttributes(None, None, None, str(e))
