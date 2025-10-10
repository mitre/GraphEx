from graphex import (
    String,
    Boolean,
    Node,
    InputSocket,
    OutputSocket,
    constants,
    exceptions,
)

import typing
import subprocess


class runSubProccess(Node):
    name: str = "Run Sub Proccess"
    description: str = (
        "Run process on machine running graphex server or running graph via cli."
    )
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/subprocess.html#subprocess.run"]
    categories: typing.List[str] = ["Miscellaneous"]
    color: str = constants.COLOR_SPECIAL

    command = InputSocket(
        datatype=String, name="Command", description="Command to run in the subprocess."
    )

    fail_on_error = InputSocket(
        datatype=Boolean,
        name="Fail on Error?",
        description="If True, the node will fail on error",
        input_field=True,
    )

    output = OutputSocket(
        datatype=String, name="Output", description="stdout of command"
    )

    error_msg = OutputSocket(
        datatype=String, name="Error Message", description="stderr of command"
    )

    has_failed = OutputSocket(
        datatype=Boolean,
        name="Has Failed?",
        description="Whether the command has failed or not.",
    )

    def run(self):

        result = subprocess.run(self.command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # type: ignore

        self.has_failed = result.returncode != 0
        self.output = result.stdout.strip() if result.stdout else ""
        self.error_msg = result.stderr.strip() if result.stderr else ""

        if self.output:
            self.log(self.output)

        if self.error_msg and self.fail_on_error:
            self.log_error(self.error_msg)
        elif self.error_msg:
            self.log_warning(self.error_msg)

        if self.has_failed and self.fail_on_error:
            raise exceptions.SubProcessFailed(
                command=self.command,
                stdout=self.output,
                stderr=self.error_msg,
                error_code=result.returncode,
            )
