from config.settings import Settings


def test_supadata_mcp_args_json():
    settings = Settings(SUPADATA_MCP_ARGS='["-y","custom-package"]')
    assert settings.get_supadata_mcp_args() == ["-y", "custom-package"]


def test_supadata_mcp_args_shlex():
    settings = Settings(SUPADATA_MCP_ARGS="--flag value --another")
    assert settings.get_supadata_mcp_args() == ["--flag", "value", "--another"]

