import re
import threading
import typing
from datetime import datetime

RESET = "\u001b[0m"
RED = "\u001b[31m"
GREEN = "\u001b[32m"
YELLOW = "\u001b[33m"
BLUE = "\u001b[34m"
MAGENTA = "\u001b[35m"
CYAN = "\u001b[36m"
WHITE = "\u001b[37m"
BOLD = "\u001b[1m"

RE_ANSI = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
RE_LINES = re.compile(r"^.+$", flags=re.MULTILINE)


class GraphexLogger:
    """
    Default logger for GraphEX.
    When running a graph from the server: self.callback is overwritten for socket use.
    """

    LEVELS = {"DEBUG": 0, "INFO": 1, "NOTICE": 2, "WARNING": 3, "ERROR": 4, "CRITICAL": 5, "IMAGE": 7}

    def __init__(self, level: str = "INFO", azure_integration: bool = False):
        self._assert_level(level)

        self.level = level
        """The minimum level of logs to print."""

        self.azure_integration: bool = azure_integration
        """Boolean whether or not the logs should also incorporate Azure DevOps Pipeline specific logging"""

        self.callback: typing.Optional[typing.Callable[[str, str, str], None]] = None
        """
        Callback for outputting logs. This is a function that takes the following arguments:
        - The message (without color codes).
        - The formatted message (with color codes, based on log level).
        - The log level (DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL).
        """

        self.lock: threading.Lock = threading.Lock()
        """A mutex for use in multithreading. This lock is locked during the duration that a log is being created."""

        self.colors = {"DEBUG": MAGENTA, "INFO": None, "NOTICE": CYAN, "WARNING": YELLOW, "ERROR": RED, "CRITICAL": f"{BOLD}{RED}", "IMAGE": GREEN}
        """The colors to use for logging each type of message. ``None`` represents no color."""

        self.reset_callback()

    def clone(self) -> "GraphexLogger":
        """Create a copy of this logger."""
        cloned_logger = GraphexLogger(level=self.level, azure_integration=self.azure_integration)
        cloned_logger.callback = self.callback
        cloned_logger.colors = self.colors
        return cloned_logger

    def set_level(self, level: str):
        """
        Set the logger to a certain level.
        """
        self._assert_level(level)
        self.level = level

    def _assert_level(self, level: str):
        """
        Assert that the given level string is valid.
        """
        if level not in self.LEVELS:
            raise RuntimeError(f"{level} is not a recognized log level. Available log levels: {str(list(self.LEVELS.keys()))[1:-1]}")

    def debug(self, msg: str):
        """
        Write a debug message.

        :param msg: The message to write.
        """
        self.write(msg, level="DEBUG")

    def info(self, msg: str):
        """
        Write an info message.

        :param msg: The message to write.
        """
        self.write(msg, level="INFO")

    def notice(self, msg: str):
        """
        Write a 'notice' message.

        :param msg: The message to write.
        """
        self.write(msg, level="NOTICE")

    def warning(self, msg: str):
        """
        Write a warning message.

        :param msg: The message to write.
        """
        self.write(msg, level="WARNING")

    def error(self, msg: str):
        """
        Write an error message.

        :param msg: The message to write.
        """
        self.write(msg, level="ERROR")

    def critical(self, msg: str):
        """
        Write a critical error message.

        :param msg: The message to write.
        """
        self.write(msg, level="CRITICAL")

    def image(self, msg: str):
        """
        Write an image as a base64 string. Calling this function will add the following prefix to your base64 string:
        'data:image/jpeg;base64,'.

        :param msg: The image to write.
        """
        self.write("data:image/jpeg;base64," + msg, level="IMAGE")

    def reset_callback(self):
        """
        Reset the callback for this logger to the default callback (printing to screen).
        """

        def log_callback(msg: str, formatted_msg: str, level: str):
            print(formatted_msg, flush=True)

        self.callback = log_callback

    def _apply_color(self, msg: str, level: str):
        """
        Apply coloring to the given string based on the log level.
        """
        self._assert_level(level)
        if self.colors[level]:
            # Apply color
            # Color must be applied to each line separately to avoid issues with how different terminals handle coloring
            return RE_LINES.sub(rf"{self.colors[level]}\g<0>{RESET}", msg)
        return msg


    def add_azure_build_tag(self, build_tag:str):
        """
            Add a tag to a current build. Will only print if self.azure_integration is true.

        Args:
            build_tag str: Tag to add to build.
        """
        if self.azure_integration and build_tag:
            print(f'##vso[build.addbuildtag]{build_tag}')

    def write(self, msg: str, level: str, acquire_lock: bool = True, skip_printing_level: bool = False):
        """
        Write a single log message at the given level.

        :param msg: The message to write.
        :param level: The level to write the message at.
        :param acquire_lock: Whether to acquire the lock on this logger before writing.
        :param skip_printing_level: Set to True to have the output appear as a normal python print statement (without the logging level and timestamp)
        """
        self._assert_level(level)
        if self.LEVELS[level] < self.LEVELS[self.level]:
            return

        if acquire_lock:
            self.lock.acquire()
        try:
            msg = msg.replace("\r\n", "\n").replace("\r", "\n")
            msg = RE_ANSI.sub("", msg)

            # if self.azure_integration and level == "WARNING":
            #     first_line = msg.split("\n")[0].strip()
            #     print(f"##vso[task.logissue type=warning]{first_line}")

            # if self.azure_integration and (level == "ERROR" or level == "CRITICAL"):
            #     first_line = msg.split("\n")[0].strip()
            #     print(f"##vso[task.logissue type=error]{first_line}")

            datestr = datetime.now().strftime(r"%Y-%m-%d %H:%M:%S.%f")[:-4]
            if not skip_printing_level:
                msg = f"[{level} - {datestr}] {msg}"

            formatted_msg = self._apply_color(msg, level)
            if self.callback:
                self.callback(msg, formatted_msg, level)
            
        finally:
            if acquire_lock:
                self.lock.release()
