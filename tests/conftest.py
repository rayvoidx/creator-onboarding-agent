import os

import pytest

# Disable authentication for all tests by default
# This must be set before 'src.app.main' is imported
os.environ["ENABLE_AUTH"] = "false"
