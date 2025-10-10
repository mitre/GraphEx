from graphex import InputSocket, OptionalInputSocket, LinkOutputSocket, ListInputSocket, Node, OutputSocket, String, constants
from graphex.runtime import NodeRuntimeError
import typing


class TryCatch(Node, include_forward_link=False):
    name = "Try / Catch"
    description = "Attempt to execute a set of actions and execute another set of actions if an error occurs."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/compound_stmts.html#the-try-statement"]
    categories = ["Control Flow", "Exceptions"]
    color = constants.COLOR_EXCEPTIONS

    errors_to_catch = ListInputSocket(
        datatype=String,
        name="Errors to Catch",
        description="The names of the exceptions to catch (e.g. 'RuntimeError'). If empty, all exception will be caught.",
    )

    try_block = LinkOutputSocket(
        name="Try",
        description="Main branch to execute. An exception anywhere in this branch will not terminate the graph and will instead trigger the 'Catch' branch.",
    )
    catch_block = LinkOutputSocket(
        name="Catch",
        description="Branch to execute if the 'Try' branch fails. Any errors raised in this branch will be raised immediately and the 'Continue' branch will not run.",
    )
    error_message = OutputSocket(
        datatype=String,
        name="Error Message",
        description="The error message when the 'Try' branch encounters an error. This will be an empty string when no error exists.",
    )
    continue_block = LinkOutputSocket(
        name="Continue",
        description="Branch to execute after either the 'Try' or 'Catch' branches complete without errors.",
    )

    def run(self):
        self.error_message = ""

        try:
            for node in self.forward("Try"):
                self._runtime.execute_node(node)
        except NodeRuntimeError as e:
            # Run the 'Catch' block
            if len(self.errors_to_catch) == 0 or any([e.exception.__class__.__name__ == errname for errname in self.errors_to_catch]):
                self.error_message = str(e)
                for node in self.forward("Catch"):
                    self._runtime.execute_node(node)
            else:
                raise e

    def run_next(self):
        for node in self.forward("Continue"):
            self._runtime.execute_node(node)


class TryCatchFinally(Node, include_forward_link=False):
    name = "Try / Catch / Finally"
    description = "Attempt to execute a set of actions, execute another set of actions if an error occurs, and then always execute a third set of actions."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/compound_stmts.html#the-try-statement", "https://docs.python.org/3/reference/compound_stmts.html#finally-clause"]
    categories = ["Control Flow", "Exceptions"]
    color = constants.COLOR_EXCEPTIONS

    errors_to_catch = ListInputSocket(
        datatype=String,
        name="Errors to Catch",
        description="The names of the exceptions to catch (e.g. 'RuntimeError'). If empty, all exception will be caught.",
    )

    try_block = LinkOutputSocket(
        name="Try",
        description="Main branch to execute. An exception anywhere in this branch will not terminate the graph and will instead trigger the 'Catch' branch.",
    )
    catch_block = LinkOutputSocket(
        name="Catch",
        description="Branch to execute if the 'Try' branch fails. Any errors raised in this branch will be raised AFTER the 'Finally' branch completes.",
    )
    error_message = OutputSocket(
        datatype=String,
        name="Error Message",
        description="The error message when the 'Try' branch encounters an error. This will be an empty string when no error exists.",
    )
    finally_block = LinkOutputSocket(
        name="Finally",
        description="Branch to execute after the 'Try'/'Catch' branches complete. This will always be executed, and any errors raised in the 'Catch' branch will instead be raised when this branch completes.",
    )

    def run(self):
        self.error_message = ""

        try:
            for node in self.forward("Try"):
                self._runtime.execute_node(node)
        except NodeRuntimeError as e:
            # Run the 'Catch' block
            if len(self.errors_to_catch) == 0 or any([e.exception.__class__.__name__ == errname for errname in self.errors_to_catch]):
                self.error_message = str(e)
                for node in self.forward("Catch"):
                    self._runtime.execute_node(node)
            else:
                raise e
        finally:
            for node in self.forward("Finally"):
                self._runtime.execute_node(node)

    def run_next(self):
        pass


class TryFinally(Node, include_forward_link=False):
    name = "Try / Finally"
    description = "Attempt to execute a set of actions and execute another set of actions regardless of whether or not an error occurs."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/compound_stmts.html#the-try-statement"]
    categories = ["Control Flow", "Exceptions"]
    color = constants.COLOR_EXCEPTIONS

    try_block = LinkOutputSocket(
        name="Try",
        description="Main branch to execute. An exception anywhere in this block will not terminate the graph and will instead be raised when the 'Finally' block completes.",
    )
    finally_block = LinkOutputSocket(
        name="Finally",
        description="Branch to execute after either the 'Try' block completes successfully or with an error. Any error in the 'Try' branch will be raised after this branch completes.",
    )

    def run(self):
        try:
            for node in self.forward("Try"):
                self._runtime.execute_node(node)
        finally:
            for node in self.forward("Finally"):
                self._runtime.execute_node(node)

    def run_next(self):
        pass


class RaiseException(Node, include_forward_link=False):
    name = "Raise Exception"
    description = "Raise a custom exception (error)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/simple_stmts.html#raise"]
    categories = ["Control Flow", "Exceptions"]
    color = constants.COLOR_EXCEPTIONS

    error_message = InputSocket(datatype=String, name="Error Message", description="The error message for this exception.")
    exception_name = OptionalInputSocket(
        datatype=String, name="Exception Name", description="The name to give this exception. If empty, this will be a 'RuntimeError'."
    )

    def run(self):
        if self.exception_name:
            CustomException = type(self.exception_name, (Exception,), dict())
            raise CustomException(self.error_message)

        raise RuntimeError(self.error_message)


class DeferException(Node):
    name = "Defer Exception"
    description = "Raises a custom exception (error) at the END of the program (program will continue after this node is reached)."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/reference/simple_stmts.html#raise"]
    categories = ["Control Flow", "Exceptions"]
    color = constants.COLOR_EXCEPTIONS

    error_message = InputSocket(datatype=String, name="Error Message", description="The error message for this exception.")
    exception_name = OptionalInputSocket(
        datatype=String, name="Exception Name", description="The name to give this exception. If empty, this will be a 'RuntimeError'."
    )

    def run(self):
        if self.exception_name:
            CustomException = type(self.exception_name, (Exception,), dict())
            e = CustomException(self.error_message)
        else:
            e = RuntimeError(self.error_message)
        try:
            raise e
        except Exception:
            e = NodeRuntimeError(runtime=self._runtime, node=self, exception=e, is_deferred=True)
        self._runtime.defer_exception(e)
