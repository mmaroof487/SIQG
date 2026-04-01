"""Argus SDK - Python client for the Secure Intelligent Query Gateway.

This package provides a clean interface to interact with Argus:
- Query execution with security, performance, and observability
- Natural language to SQL conversion (NL→SQL)
- Query explanation (plain English)
- Health and metrics monitoring

Installation:
    pip install argus-sdk

Quick Start:
    from argus import Gateway

    gw = Gateway("http://localhost:8000").login("user", "pass")
    result = gw.query("SELECT * FROM users LIMIT 10")
    print(result["rows"])
"""

from .client import Gateway

__version__ = "0.1.0"
__author__ = "Argus Team"
__all__ = ["Gateway"]
