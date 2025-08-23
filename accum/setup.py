"""
Setup script for RSA Accumulator package.
"""

from setuptools import setup, find_packages

with open("requirements-dev.txt", "r") as f:
    dev_requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="rsa-accumulator",
    version="0.1.0",
    description="RSA Accumulator for IoT Device Identity Management",
    author="BTP Research Project",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # No runtime dependencies - uses only Python stdlib
    ],
    extras_require={
        "dev": dev_requirements,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
