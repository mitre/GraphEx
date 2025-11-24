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
    install_requires=[
        "cryptography",
        "eventlet",
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
        "setuptools<81",
        "typeguard>=4.0.0",
        "typing-extensions>=4.7.1",
    ],
)
