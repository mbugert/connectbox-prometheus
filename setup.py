from pathlib import Path
from setuptools import find_packages, setup

with open("README.md", "rb") as f:
    long_descr = f.read().decode("utf-8")

with (Path("requirements") / "production.txt").open() as f:
    install_requires = [s.strip() for s in f.readlines()]

setup(
    name="connectbox-prometheus",
    version="0.2.1",
    author="Michael Bugert",
    author_email="git@mbugert.de",
    description='Prometheus exporter for Compal CH7465LG cable modems, commonly sold as "Connect Box"',
    long_description=long_descr,
    long_description_content_type="text/markdown",
    url="https://github.com/mbugert/connectbox-prometheus",
    entry_points={
        "console_scripts": [
            "connectbox_exporter = connectbox_exporter.connectbox_exporter:main"
        ]
    },
    packages=find_packages(exclude=["tests"]),
    install_requires=install_requires,
    include_package_data=True,
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Networking :: Monitoring",
    ],
)
