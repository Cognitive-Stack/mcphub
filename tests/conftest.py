import json
import os
import pytest
from pathlib import Path
from unittest import mock


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary .mcphub.json file for testing."""
    config_content = {
        "mcpServers": {
            "test-server": {
                "package_name": "test-mcp-server",
                "command": "python",
                "args": ["-m", "test_server"],
                "env": {"TEST_ENV": "test_value"},
                "description": "Test MCP Server",
                "tags": ["test", "demo"]
            }
        }
    }
    
    config_file = tmp_path / ".mcphub.json"
    with open(config_file, "w") as f:
        json.dump(config_content, f)
    
    return config_file


@pytest.fixture
def mock_mcp_preconfigured_servers(tmp_path):
    """Mock the mcphub_preconfigured_servers.json file."""
    content = {
        "predefined-server": {
            "command": "python",
            "args": ["-m", "predefined_server"],
            "description": "Predefined MCP Server",
            "tags": ["predefined", "demo"]
        }
    }
    
    preconfigured_path = tmp_path / "mcphub_preconfigured_servers.json"
    with open(preconfigured_path, "w") as f:
        json.dump(content, f)
    
    return preconfigured_path


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Create and return a mock cache directory."""
    cache_dir = tmp_path / ".mcphub_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


@pytest.fixture
def mock_path_exists():
    """Mock Path.exists to always return True for .mcphub.json files."""
    original_exists = Path.exists
    
    def patched_exists(self):
        if self.name == ".mcphub.json":
            return True
        return original_exists(self)
    
    with mock.patch("pathlib.Path.exists", patched_exists):
        yield


@pytest.fixture
def mock_current_dir(monkeypatch, tmp_path, temp_config_file, mock_cache_dir):
    """Mock the current directory to use the temporary config file."""
    # Create a function that returns the parent directory of temp_config_file
    def mock_cwd():
        return Path(temp_config_file).parent
    
    # Create a function that returns the parent directory as home
    def mock_home():
        return Path(temp_config_file).parent
    
    # Patch Path.cwd() and Path.home() to return our mock directory
    monkeypatch.setattr(Path, "cwd", mock_cwd)
    monkeypatch.setattr(Path, "home", mock_home)
    
    # Return the mock current directory
    return Path(temp_config_file).parent


@pytest.fixture
def mock_find_config_path(monkeypatch, temp_config_file):
    """Mock the _find_config_path method to return our test config file."""
    def mock_find_config(self):  # Add self parameter here to fix TypeError
        return str(temp_config_file)
    
    # Apply the monkeypatch
    monkeypatch.setattr("mcphub.mcphub.MCPHub._find_config_path", mock_find_config)
    
    return str(temp_config_file)


@pytest.fixture
def mock_mcphub_init(monkeypatch, temp_config_file):
    """Mock MCPHub initialization to avoid filesystem operations."""
    # Create patch for _find_config_path
    def mock_find_config(self):
        return str(temp_config_file)
    
    # Create patch for _get_cache_dir in MCPServers
    def mock_get_cache_dir(self):
        cache_dir = Path(temp_config_file).parent / ".mcphub_cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir
    
    # Create patch for _setup_all_servers in MCPServers
    def mock_setup_all_servers(self):
        pass  # No-op to avoid setup operations
    
    # Apply the monkeypatches
    monkeypatch.setattr("mcphub.mcphub.MCPHub._find_config_path", mock_find_config)
    monkeypatch.setattr("mcphub.mcp_servers.servers.MCPServers._get_cache_dir", mock_get_cache_dir)
    monkeypatch.setattr("mcphub.mcp_servers.servers.MCPServers._setup_all_servers", mock_setup_all_servers)
    
    return str(temp_config_file)


@pytest.fixture
def test_config_path(tmp_path) -> Path:
    """Create a temporary config file for testing"""
    config = {
        "mcpServers": {
            "test-mcp": {
                "package_name": "test-package",
                "command": "echo",
                "args": ["test"],
                "env": {"TEST_ENV": "test_value"}
            },
            "python-mcp": {
                "package_name": "python-package",
                "repo_url": "https://github.com/test/python-mcp",
                "command": "python",
                "args": ["-m", "mcp_server"],
                "setup_script": "pip install -e .",
                "env": {"PYTHON_ENV": "test_value"}
            }
        }
    }
    config_file = tmp_path / ".mcphub.json"
    config_file.write_text(json.dumps(config))
    return config_file


@pytest.fixture
def mock_session():
    """Mock MCP session for testing"""
    class MockSession:
        async def initialize(self):
            pass
        
        async def list_tools(self):
            class ToolsList:
                tools = [
                    {"name": "tool1", "description": "Test tool 1"},
                    {"name": "tool2", "description": "Test tool 2"}
                ]
            return ToolsList()
            
    return MockSession()