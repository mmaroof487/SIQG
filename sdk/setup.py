"""Argus SDK setup and installation configuration."""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="argus-sdk",
    version="0.1.0",
    author="Argus Team",
    description="Python SDK for Argus - Secure Intelligent Query Gateway",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mmaroof487/SIQG",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        "httpx>=0.27.0",
        "typer>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "argus=argus.cli:app",
        ],
    },
    keywords="query gateway database security performance intelligence observability",
)
