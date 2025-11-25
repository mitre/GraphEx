import os
import io
from pathlib import Path
from setuptools import find_packages, setup


def get_package_data():
    ROOT_PATH = os.path.abspath("./graphex")
    WEBSITE_PATH = os.path.join(ROOT_PATH, "website")
    files = []
    for directory, _, filenames in os.walk(WEBSITE_PATH):
        for filename in filenames:
            path = os.path.join(directory, filename)
            path = path[len(ROOT_PATH) :].strip("/")
            files.append(path)
    return {"graphex": files}

def read_readme():
    readme_path = Path(__file__).parent / "README.md"
    with io.open(readme_path, "r", encoding="utf-8") as f:
        return f.read()

setup(
    name="mitre-graphex",
    version="1.18.0",
    author="The MITRE Corporation",
    description="Visual programming tool for environment automation.",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/mitre/GraphEx",
    project_urls={
        "Documentation": "https://github.com/mitre/GraphEx/blob/main/docs/markdown/index.md",
        "Source": "https://github.com/mitre/GraphEx",
        "Issues": "https://github.com/mitre/GraphEx/issues",
        "Changelog": "https://github.com/mitre/GraphEx/blob/main/docs/markdown/other/changelog.md",
    },
    license="Apache-2.0",
    license_files=["LICENSE"],
    keywords=["automation", "visual-programming", "flask", "network", "graph"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Framework :: Flask",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(include=["graphex*"]),
    package_data=get_package_data(),
    python_requires=">=3.10",
    install_requires=[ # NOTE: some deps may be in the top level (e.g. cryptography dep of pyopenssl)
        "cryptography==46.0.3",
            ## start cryptography deps
            "cffi==2.0.0",
            "pycparser==2.23",
            # end cryptography deps
        "eventlet==0.40.3",
            # start eventlet dep
            "dnspython==2.8.0",
            "greenlet==3.0.3",
            # end eventlet deps
        "flask-socketio==5.5.1",
            ## start flask-socketio deps
            "bidict==0.23.1",
            "blinker==1.9.0",
            "click==8.3.1",
            "flask==3.1.2",
            "h11==0.16.0",
            "itsdangerous==2.2.0",
            "Jinja2==3.1.6",
            "MarkupSafe==3.0.3",
            "python-engineio==4.12.3",
            "python-socketio==5.15.0",
            "simple-websocket===1.1.0",
            "Werkzeug==3.1.3",
            "wsproto==1.3.2",
            # end flask-socketio deps
        "gitPython==3.1.45",
            ## start gitPython deps
            "gitdb==4.0.12",
            "smmap==5.0.2",
            # end gitPython deps
        "matplotlib==3.10.7",
            ## start matplotlib deps
            "contourpy==1.3.2",
            "cycler==0.12.1",
            "fonttools==4.60.1",
            "kiwisolver==1.4.9",
            "packaging==25.0",
            "pillow==12.0.0",
            "pyparsing==3.2.5",
            "six==1.17.0",
            # end matplotlib deps
        "networkx==3.4.2",
        "numpy==2.2.6",
        "ping3==4.0.4",
        "pyopenssl==25.3.0",
        "python-dateutil==2.8.2",
        "pyyaml==6.0.3",
        "requests==2.32.3",
            ## start requests deps
            "certifi==2025.11.12",
            "charset-normalizer==3.4.4",
            "idna==3.11",
            "urllib3==2.5.0",
            # end requests deps
        "service_identity==24.2.0",
            ## start service_identity deps
            "attrs==25.4.0",
            "pyasn1==0.6.1",
            "pyasn1_modules==0.4.2",
            # end service_identity deps
        "setuptools==80.9.0",
        "typeguard==4.4.4",
        "typing_extensions==4.15.0",
    ],
)
