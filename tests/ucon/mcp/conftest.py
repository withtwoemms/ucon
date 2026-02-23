# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""MCP test configuration - requires Python 3.10+."""

import sys

import pytest

# Skip all MCP tests on Python < 3.10
if sys.version_info < (3, 10):
    collect_ignore_glob = ["test_*.py"]
