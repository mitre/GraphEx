from graphex import Boolean, Node, InputSocket, LinkOutputSocket, ListInputSocket, OutputSocket
from graphex import constants
import typing


class IfElse(Node, include_forward_link=False):
    name = "If / Else"
    description = "Conditionally continue this graph based on the given boolean."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#if-statements"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    boolean = InputSocket(datatype=Boolean, name="Condition", description="The boolean for this conditional.")

    if_true = LinkOutputSocket(name="If True", description="Execute this branch if the input boolean is True.")
    if_false = LinkOutputSocket(name="If False", description="Execute this branch if the output boolean is True.")

    def run(self):
        pass

    def run_next(self):
        if self.boolean:
            # Continue down the 'If True' line
            for node in self.forward("If True"):
                self._runtime.execute_node(node)
        else:
            # Continue down the 'If False' line
            for node in self.forward("If False"):
                self._runtime.execute_node(node)


class IfElseFinally(Node, include_forward_link=False):
    name = "If / Else / Finally"
    description = "Conditionally continue this graph based on the given boolean."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#if-statements"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    boolean = InputSocket(datatype=Boolean, name="Condition", description="The boolean for this conditional.")

    if_true = LinkOutputSocket(name="If True", description="Execute this branch if the input boolean is True.")
    if_false = LinkOutputSocket(name="If False", description="Execute this branch if the output boolean is True.")
    finally_block = LinkOutputSocket(
        name="Finally", description="Branch to (always) execute after either the 'If True' or 'If False' blocks complete successfully."
    )

    def run(self):
        if self.boolean:
            # Continue down the 'If True' line
            for node in self.forward("If True"):
                self._runtime.execute_node(node)
        else:
            # Continue down the 'If False' line
            for node in self.forward("If False"):
                self._runtime.execute_node(node)

    def run_next(self):
        for node in self.forward("Finally"):
            self._runtime.execute_node(node)


class IfTrue(Node, include_forward_link=False):
    name = "If True"
    description = "Conditionally continue this graph if the given boolean is True."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#if-statements"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    boolean = InputSocket(datatype=Boolean, name="Condition", description="The boolean for this conditional.")

    if_true = LinkOutputSocket(name="If True", description="Continue the graph if the input boolean is True.")

    def run(self):
        if self.boolean:
            # Continue down the 'If True' line
            for node in self.forward("If True"):
                self._runtime.execute_node(node)

    def run_next(self):
        pass


class IfFalse(Node, include_forward_link=False):
    name = "If False"
    description = "Conditionally continue this graph if the given boolean is False."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#if-statements"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    boolean = InputSocket(datatype=Boolean, name="Condition", description="The boolean for this conditional.")

    if_true = LinkOutputSocket(name="If False", description="Continue the graph if the input boolean is False.")

    def run(self):
        if not self.boolean:
            # Continue down the 'If False' line
            for node in self.forward("If False"):
                self._runtime.execute_node(node)

    def run_next(self):
        pass


class IfTrueFinally(Node, include_forward_link=False):
    name = "If True / Finally"
    description = "Conditionally branch this graph if the given boolean is True."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#if-statements"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    boolean = InputSocket(datatype=Boolean, name="Condition", description="The boolean for this conditional.")

    if_true = LinkOutputSocket(name="If True", description="Execute this branch if the input boolean is True.")
    finally_block = LinkOutputSocket(name="Finally", description="Branch to (always) execute after either the 'If True' block completes successfully.")

    def run(self):
        if self.boolean:
            # Continue down the 'If True' line
            for node in self.forward("If True"):
                self._runtime.execute_node(node)

    def run_next(self):
        for node in self.forward("Finally"):
            self._runtime.execute_node(node)


class IfFalseFinally(Node, include_forward_link=False):
    name = "If False / Finally"
    description = "Conditionally branch this graph if the given boolean is False."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/tutorial/controlflow.html#if-statements"]
    categories = ["Control Flow"]
    color = constants.COLOR_CONTROL_FLOW

    boolean = InputSocket(datatype=Boolean, name="Condition", description="The boolean for this conditional.")

    if_true = LinkOutputSocket(name="If False", description="Execute this branch if the input boolean is False.")
    finally_block = LinkOutputSocket(name="Finally", description="Branch to (always) execute after either the 'If False' block completes successfully.")

    def run(self):
        if not self.boolean:
            # Continue down the 'If False' line
            for node in self.forward("If False"):
                self._runtime.execute_node(node)

    def run_next(self):
        for node in self.forward("Finally"):
            self._runtime.execute_node(node)


class BooleanAnd(Node):
    name = "And (Boolean)"
    description = "Outputs True if all inputs are True"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#booleans"]
    categories = ["Control Flow", "Operators"]
    color = constants.COLOR_CONTROL_FLOW

    input_bools = ListInputSocket(datatype=Boolean, name="Booleans", description="Booleans to check for True")

    result = OutputSocket(datatype=Boolean, name="Result", description="True if all inputs are True")

    def run(self):
        if all(self.input_bools):
            self.result = True
        else:
            self.result = False


class BooleanOr(Node):
    name = "Or (Boolean)"
    description = "Outputs True if any input is True"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#booleans"]
    categories = ["Control Flow", "Operators"]
    color = constants.COLOR_CONTROL_FLOW

    input_bools = ListInputSocket(datatype=Boolean, name="Booleans", description="Booleans to check for True")

    result = OutputSocket(datatype=Boolean, name="Result", description="True if any input is True")

    def run(self):
        if any(self.input_bools):
            self.result = True
        else:
            self.result = False


class BooleanNot(Node):
    name = "Negate / Not (Boolean)"
    description = "'Flips the bit' on a boolean (e.g. converts True to False or False to True)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#is-not"]
    categories = ["Control Flow", "Operators"]
    color = constants.COLOR_CONTROL_FLOW

    input_bool = InputSocket(datatype=Boolean, name="Boolean", description="Boolean to flip")

    result = OutputSocket(datatype=Boolean, name="Result", description="The opposite of the input boolean.")

    def run(self):
        self.result = not self.input_bool


class BooleanEqual(Node):
    name = "Equal (Boolean)"
    description = "Outputs True if both Booleans contain the same value"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories = ["Control Flow", "Operators"]
    color = constants.COLOR_CONTROL_FLOW

    input_1 = InputSocket(datatype=Boolean, name="Boolean 1", description="The first boolean to compare.")
    input_2 = InputSocket(datatype=Boolean, name="Boolean 2", description="The second boolean to compare.")

    result = OutputSocket(datatype=Boolean, name="Result", description="True if the booleans are equal.")

    def run(self):
        self.result = self.input_1 == self.input_2


class BooleanNotEqual(Node):
    name = "Not Equal (Boolean)"
    description = "Outputs True if the input Booleans contain the different values"
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/expressions.html#value-comparisons"]
    categories = ["Control Flow", "Operators"]
    color = constants.COLOR_CONTROL_FLOW

    input_1 = InputSocket(datatype=Boolean, name="Boolean 1", description="The first boolean to compare.")
    input_2 = InputSocket(datatype=Boolean, name="Boolean 2", description="The second boolean to compare.")

    result = OutputSocket(datatype=Boolean, name="Result", description="True if the booleans are not equal.")

    def run(self):
        self.result = self.input_1 != self.input_2
