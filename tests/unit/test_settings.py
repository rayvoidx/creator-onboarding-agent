import os
from unittest import mock

from config.settings import Settings


def test_supadata_mcp_args_json():
    with mock.patch.dict(os.environ, {"SUPADATA_MCP_ARGS": '["-y","custom-package"]'}):
        settings = Settings()
        assert settings.get_supadata_mcp_args() == ["-y", "custom-package"]


def test_supadata_mcp_args_shlex():
    with mock.patch.dict(os.environ, {"SUPADATA_MCP_ARGS": "--flag value --another"}):
        settings = Settings()
        assert settings.get_supadata_mcp_args() == ["--flag", "value", "--another"]
