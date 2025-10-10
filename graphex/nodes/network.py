from graphex import String, Number, Boolean, DataContainer, Node, InputSocket, OptionalInputSocket, OutputSocket, ListOutputSocket, constants, exceptions
import requests
import warnings
import urllib3
import typing
import socket
import ping3
import json
import time
import os
import re


class NetworkHttpRequest(Node):
    name: str = "Network HTTP Request"
    description: str = "Makes a generic HTTP request to a resource."
    hyperlink: typing.List[str] = ["https://docs.python-requests.org/en/latest/index.html"]
    categories: typing.List[str] = ["Miscellaneous", "Network"]
    color: str = constants.COLOR_NETWORK

    url = InputSocket(datatype=String, name="URL", description="The URL/resource to target.")
    method = InputSocket(
        datatype=String,
        name="Method",
        description="The method (e.g. 'GET', 'POST', 'PATCH', 'PUT', 'HEAD', 'DELETE').",
        input_field="GET",
    )
    body_input = OptionalInputSocket(datatype=String, name="Body", description="The payload as a string to send.")
    headers_input = OptionalInputSocket(
        datatype=DataContainer, name="Headers", description="The headers to attach to the request. This should be a Data Container containing key/value pairs."
    )
    cookies = OptionalInputSocket(
        datatype=DataContainer, name="Cookies", description="Cookies to send with the request. This should be a Data Container containing key/value pairs."
    )
    cert = OptionalInputSocket(datatype=String, name="Certificate", description="Path to an SSL client cert file (.pem) to use.")
    auth_username = OptionalInputSocket(datatype=String, name="Auth Username", description="Username to use for Basic Authentication.")
    auth_password = OptionalInputSocket(datatype=String, name="Auth Password", description="Password to use for Basic Authentication.")
    timeout = OptionalInputSocket(datatype=Number, name="Timeout", description="How many seconds to wait for the server to send data before giving up.")
    allow_redirects = InputSocket(datatype=Boolean, name="Allow Redirects", description="Whether to allow HTTP redirection by the server.", input_field=True)
    ignore_certs = InputSocket(datatype=Boolean, name="Ignore Certs", description="Whether to ignore invalid certificates.", input_field=False)
    error_on_failure = InputSocket(
        datatype=Boolean,
        name="Error On Failure",
        description="Whether to raise an error when a bad HTTP status code (e.g. 404) is provided in the response.",
        input_field=True,
    )

    status_result = OutputSocket(datatype=Number, name="Status Code", description="The status code returned by the request.")
    text_response = OutputSocket(datatype=String, name="Text Response", description="Any raw text response returned from the request.")
    response_headers = OutputSocket(datatype=DataContainer, name="Response Headers", description="The headers from the HTTP response.")

    def log_prefix(self) -> str:
        return f"[{self.name} - {self.url}] "

    def run(self):
        auth = None
        if self.auth_username and self.auth_password:
            auth = (self.auth_username, self.auth_password)
        elif self.auth_username:
            raise ValueError(f"An Auth Username was provided without a password.")
        elif self.auth_password:
            raise ValueError(f"An Auth Password was provided without a username.")

        VALID_METHODS = ["HEAD", "GET", "POST", "PATCH", "PUT", "DELETE"]
        if self.method not in ["HEAD", "GET", "POST", "PATCH", "PUT", "DELETE"]:
            raise exceptions.InvalidParameterError(self.name, "Method", self.method, VALID_METHODS)

        headers = {}
        if self.headers_input and isinstance(self.headers_input, dict):
            headers = self.headers_input
        elif self.headers_input:
            raise ValueError(f"HTTP Request headers must be a dictionary-like Data Container.")

        cookies = {}
        if self.cookies and isinstance(self.cookies, dict):
            cookies = self.cookies
        elif self.cookies:
            raise ValueError(f"HTTP Request cookies must be a dictionary-like Data Container.")

        params = {
            "method": self.method,
            "url": self.url,
            "data": self.body_input,
            "headers": headers,
            "auth": auth,
            "cookies": cookies,
            "cert": self.cert,
            "timeout": self.timeout,
            "allow_redirects": self.allow_redirects,
        }

        self.log(f"Performing HTTP {self.method} request")
        if self.ignore_certs:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                req = requests.request(**params, verify=False)
        else:
            req = requests.request(**params)

        self.debug(f"Status: {req.status_code}")

        self.status_result = req.status_code
        self.text_response = req.text
        self.response_headers = dict(req.headers)
        if self.error_on_failure:
            req.raise_for_status()


class NetworkDownload(Node):
    name: str = "Network HTTP Download"
    description: str = "Download a file from a URL. An error will be raised if the file cannot be downloaded."
    hyperlink: typing.List[str] = ["https://docs.python-requests.org/en/latest/index.html"]
    categories: typing.List[str] = ["Miscellaneous", "Network"]
    color: str = constants.COLOR_NETWORK

    url = InputSocket(datatype=String, name="URL", description="The URL/resource to target.")
    path = InputSocket(
        datatype=String,
        name="Path",
        description="The path to download the file to. If this is an existing directory, the file will downloaded into this directory without changing the name. Otherwise, the file will be downloaded to this path (and renamed as needed).",
    )

    output_path = OutputSocket(datatype=String, name="Downloaded File Path", description="The path to the downloaded file.")

    def log_prefix(self) -> str:
        return f"[{self.name} - {self.url}] "

    def run(self):
        self.log(f"Downloading file from URL: {self.url}")
        self.output_path = self.path
        with requests.get(self.url, stream=True) as r:
            r.raise_for_status()
            content_length = r.headers.get("Content-Length")
            size: typing.Optional[int] = int(content_length) if content_length else None
            size_mb = round(size / (1000 * 1000), ndigits=2) if size else None

            if os.path.isdir(self.output_path):
                # Determine the file name
                filename = "file"
                content_disposition = r.headers.get("Content-Disposition")
                if not content_disposition or "filename=" not in content_disposition:
                    # Try to determine the filename from the URL
                    filename = self.url.split("/")[-1]
                else:
                    filename = re.findall("filename=(.+)", content_disposition)[0]
                self.output_path = os.path.join(self.output_path, filename)

            start_time = time.time()
            with open(self.output_path, "wb") as f:
                bytes_written = 0
                last_log_time = start_time
                for chunk in r.iter_content(chunk_size=8192):
                    bytes_written += f.write(chunk)
                    if size and (time.time() - last_log_time > 10 or bytes_written == size):
                        delta_time = (time.time() - start_time) or 0.001
                        megabytes_per_second = round(bytes_written / delta_time / (1000 * 1000), ndigits=1)
                        bytes_written_mb = round(bytes_written / (1000 * 1000), ndigits=2)
                        self.debug(f"{int(bytes_written / size * 100)}% ({bytes_written_mb}MB / {size_mb}MB) | {megabytes_per_second} MB/s")
                        last_log_time = time.time()

        self.debug(f"Downloaded file to {self.output_path}")
        self.output_path = self.output_path


class NetworkPing(Node):
    name: str = "Network Ping"
    description: str = "Send ICMP pings to destination address (Note that on some platforms, ICMP messages can only be sent from processes running as root)."
    hyperlink: typing.List[str] = ["https://pypi.org/project/ping3/"]
    categories: typing.List[str] = ["Miscellaneous", "Network"]
    color: str = constants.COLOR_NETWORK

    target = InputSocket(
        datatype=String, name="Target", description="The IP or URL to ping. Can be an IP address or a domain name. Ex. '0.0.0.0' / 'example.com'"
    )
    attempts = InputSocket(
        datatype=Number,
        name="Attempts",
        description="The number of ping atttempts to make. This will perform up to this many attempts to get a response before exiting. This node will exit after the first successful response, or until all attempts are exhausted.",
        input_field=1,
    )
    timeout = InputSocket(datatype=Number, name="Timeout", description="Time to wait for a response, in seconds.", input_field=4)
    src_address = OptionalInputSocket(
        datatype=String, name="Source Address", description="The IP address to ping from. This is for multiple network interfaces. Ex. '0.0.0.0'."
    )
    interface = OptionalInputSocket(datatype=String, name="Interface", description="LINUX ONLY. The gateway network interface to ping from. Ex. 'wlan0'.")
    ttl = OptionalInputSocket(
        datatype=Number,
        name="TTL",
        description="The Time-To-Live of the outgoing packet. Providing no value means using OS default ttl -- 64 on Linux and macOS, and 128 on Windows.",
    )

    delay = OutputSocket(
        datatype=Number, name="Delay", description="The delay (in seconds) for the ping. If no response is received (i.e. 'Success' is False), this will be -1."
    )
    success = OutputSocket(
        datatype=Boolean,
        name="Success",
        description="Whether a ping response was received from the target. This will be False if either an error or timeout occurred.",
    )

    def run(self):
        self.delay = -1
        self.success = False
        for i in range(1, int(self.attempts) + 1):
            self.debug(f"Pinging {self.target} (Attempt {i} of {int(self.attempts)})")
            status = ping3.ping(
                self.target, timeout=int(self.timeout), src_addr=self.src_address or "", interface=self.interface or "", ttl=int(self.ttl) if self.ttl else 0
            )
            if status is not None and status != False:
                self.debug(f"Received ping response from {self.target}")
                self.delay = status
                self.success = True
                break


class DNSForwardLookup(Node):
    name: str = "DNS Forward Lookup"
    description: str = "Perform a DNS forward lookup to translate a host name to IP addresses."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/socket.html#socket.getaddrinfo"]
    categories: typing.List[str] = ["Miscellaneous", "Network"]
    color: str = constants.COLOR_NETWORK

    hostname = InputSocket(datatype=String, name="Host name", description="The host name. Ex. 'example.com'")
    include_ipv4 = InputSocket(datatype=Boolean, name="Include IPv4", description="Whether to include IPv4 addresses in the list of results.", input_field=True)
    include_ipv6 = InputSocket(datatype=Boolean, name="Include IPv6", description="Whether to include IPv6 addresses in the list of results.", input_field=True)
    raise_error = InputSocket(
        datatype=Boolean,
        name="Raise Errors",
        description="Whether to raise an error when the DNS forward lookup fails. If this is False, 'IP Addresses' will be an empty list on failure instead.",
        input_field=True,
    )

    ips = ListOutputSocket(
        datatype=String,
        name="IP Addresses",
        description="The resolved IP addresses for the given host name. This will be an empty list when the DNS forward lookup fails and 'Raise Errors' is False.",
    )

    def run(self):
        self.debug(f"Resolving {self.hostname}")

        ip_formats = []
        if self.include_ipv4:
            ip_formats.append(socket.AF_INET)
        if self.include_ipv6:
            ip_formats.append(socket.AF_INET6)

        error = None
        try:
            self.ips = [str(data[4][0]) for data in socket.getaddrinfo(self.hostname, 80, proto=socket.IPPROTO_TCP) if data[0] in ip_formats]
            if len(self.ips) == 0:
                error = RuntimeError(f"No IPs found for {self.hostname}")
            self.debug(f"Resolved {self.hostname} to: {str(self.ips)[1:-1]}")
        except Exception as e:
            error = e

        if self.raise_error and error:
            raise error

        if error:
            self.debug(f"Error resolving {self.hostname}: {str(error)}")


class DNSReverseLookup(Node):
    name: str = "DNS Reverse Lookup"
    description: str = "Perform a DNS reverse lookup to translate an IP address to a host name."
    hyperlink: typing.List[str] = ["https://docs.python.org/3/library/socket.html#socket.getnameinfo"]
    categories: typing.List[str] = ["Miscellaneous", "Network"]
    color: str = constants.COLOR_NETWORK

    ip = InputSocket(datatype=String, name="IP", description="The IP address (IPv4 or IPv6).")
    raise_error = InputSocket(
        datatype=Boolean,
        name="Raise Errors",
        description="Whether to raise an error when the DNS reverse lookup fails. If this is False, 'Host Name' will be an empty string on failure instead.",
        input_field=True,
    )

    hostname = OutputSocket(
        datatype=String,
        name="Host Name",
        description="The resolved host name for the given IP. This will be an empty string when the DNS reverse lookup fails and 'Raise Errors' is False.",
    )

    def run(self):
        self.debug(f"Resolving {self.ip}")

        error = None
        try:
            data = socket.getnameinfo((self.ip, 0), 0)
            self.hostname = data[0]
            self.debug(f"Resolved {self.ip} to {self.hostname}")
        except Exception as e:
            error = e

        if self.raise_error and error:
            raise error

        if error:
            self.debug(f"Error resolving {self.ip}: {str(error)}")
            self.hostname = ""
