import os

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


setup(
    name="mitre-graphex",
    version="1.16.0",
    author="The MITRE Corporation",
    description="Visual programming tool for environment automation.",
    packages=find_packages(include=["graphex*"]),
    package_data=get_package_data(),
    python_requires=">=3.10",
    install_requires=[
        "build",
        "cryptography",
        "flask-socketio>=5.3.4",
        "flask>=2.2.3",
        "gitPython==3.1.*",
        "matplotlib",
        "networkx",
        "numpy",
        "ping3==4.0.4",
        "pyopenssl",
        "python-dateutil==2.8.2",
        "pyyaml>=6.0.1",
        "requests>=2.31.0",
        "service_identity",
        "typeguard>=4.0.0",
        "typing-extensions>=4.7.1",
        "wheel",
    ],
)
