"""Unit tests for mcphub CLI commands."""
import json
import os
import sys
from pathlib import Path
from unittest import mock
import pytest
from datetime import datetime

from mcphub.cli import commands, utils
from mcphub.cli.process_manager import ProcessManager
from mcphub.mcp_servers.params import MCPServersParams


@pytest.fixture
def mock_cli_config_file(tmp_path):
    """Create a temporary .mcphub.json file for CLI testing."""
    config_content = {
        "mcpServers": {
            "test-server": {
                "package_name": "test-mcp-server",
                "command": "python",
                "args": ["-m", "test_server"],
                "env": {"TEST_ENV": "test_value"},
                "description": "Test MCP Server",
                "tags": ["test", "demo"],
                "last_run": datetime.now().isoformat()
            }
        }
    }
    
    config_file = tmp_path / ".mcphub.json"
    with open(config_file, "w") as f:
        json.dump(config_content, f)
    
    return config_file


@pytest.fixture
def mock_process_manager():
    """Create a mock process manager for testing."""
    with mock.patch("mcphub.cli.commands.ProcessManager") as mock_pm:
        mock_pm.return_value.get_process_info.return_value = {
            "pid": 1234,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "memory_usage": "100MB"
        }
        mock_pm.return_value.start_process.return_value = 1234  # Return a mock PID
        mock_pm.return_value.list_processes.return_value = [{
            "name": "test-server",
            "status": "running",
            "pid": 1234,
            "start_time": datetime.now().isoformat(),
            "memory_usage": "100MB",
            "command": "python -m test_server",
            "ports": [8000],
            "uptime": "1h"
        }]
        yield mock_pm


@pytest.fixture
def cli_env(mock_cli_config_file, monkeypatch):
    """Set up the environment for CLI testing."""
    # Mock get_config_path to return our test config
    def mock_get_config_path():
        return mock_cli_config_file
    
    # Apply patches
    monkeypatch.setattr(utils, "get_config_path", mock_get_config_path)
    
    # Return paths for test verification
    return {
        "config_path": mock_cli_config_file
    }


class TestCliAdd:
    def test_add_server_from_repo(self, cli_env, monkeypatch):
        """Test adding a server from a GitHub repository."""
        # Mock MCPServersParams
        mock_servers_params = mock.Mock()
        mock_servers_params.add_server_from_repo.return_value = None
        mock_servers_params.retrieve_server_params.return_value = mock.Mock(env=None)
        
        # Mock the MCPServersParams class to return our mock instance
        mock_mcp_servers_params_class = mock.Mock(return_value=mock_servers_params)
        monkeypatch.setattr("mcphub.mcp_servers.params.MCPServersParams", mock_mcp_servers_params_class)
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Set up command arguments
        args = mock.Mock()
        args.repo_url = "https://github.com/test/repo"
        args.mcp_name = None
        
        # Execute add command
        commands.add_command(args)
        
        # Verify server was added
        mock_servers_params.add_server_from_repo.assert_called_once_with(
            "test/repo", "https://github.com/test/repo"
        )

    def test_add_server_invalid_url(self, cli_env, capfd, monkeypatch):
        """Test adding a server with an invalid GitHub URL."""
        # Set up command arguments
        args = mock.Mock()
        args.repo_url = "https://invalid.com/repo"
        args.mcp_name = None
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Execute add command
        commands.add_command(args)
        
        # Verify error message
        out, _ = capfd.readouterr()
        assert "Only GitHub repositories are supported" in out


class TestCliRemove:
    def test_remove_existing_server(self, cli_env, capfd):
        """Test removing a server that exists in the config."""
        # First ensure the server exists in config
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
            config["mcpServers"]["server-to-remove"] = {"command": "test"}
        
        with open(cli_env["config_path"], "w") as f:
            json.dump(config, f)
        
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "server-to-remove"
        
        # Execute remove command
        commands.remove_command(args)
        
        # Verify server was removed
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
        
        assert "server-to-remove" not in config["mcpServers"]
        
        # Check output
        out, _ = capfd.readouterr()
        assert "Removed configuration for 'server-to-remove'" in out

    def test_remove_nonexistent_server(self, cli_env, capfd, monkeypatch):
        """Test removing a server that doesn't exist in the config."""
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "nonexistent-server"
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Execute remove command
        commands.remove_command(args)
        
        # Verify error message
        out, _ = capfd.readouterr()
        assert "MCP server 'nonexistent-server' not found" in out


class TestCliPs:
    def test_ps_command(self, cli_env, mock_process_manager, capfd):
        """Test the ps command listing server processes."""
        # Set up command arguments
        args = mock.Mock()
        
        # Execute ps command
        commands.ps_command(args)
        
        # Verify output
        out, _ = capfd.readouterr()
        assert "test-server" in out
        assert "running" in out
        assert "8000" in out  # Port from mock
        assert "1h" in out  # Uptime from mock


class TestCliStatus:
    def test_status_command(self, cli_env, mock_process_manager, capfd):
        """Test the status command showing server status."""
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "test-server"
        
        # Execute status command
        commands.status_command(args)
        
        # Verify output
        out, _ = capfd.readouterr()
        assert "test-server" in out
        assert "test-mcp-server" in out  # Package name from config
        assert "python" in out  # Command from config


class TestCliRun:
    def test_run_command(self, cli_env, mock_process_manager, capfd, monkeypatch):
        """Test running a server."""
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "test-server"
        args.detach = False
        args.sse = False
        
        # Execute run command
        commands.run_command(args)
        
        # Verify process manager was called
        mock_process_manager.return_value.start_process.assert_called_once()
        call_args = mock_process_manager.return_value.start_process.call_args[0]
        assert call_args[0] == "test-server"  # name
        assert isinstance(call_args[1], list)  # command
        assert isinstance(call_args[2], dict)  # env

    def test_run_detached(self, cli_env, mock_process_manager, capfd, monkeypatch):
        """Test running a server in detached mode."""
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "test-server"
        args.detach = True
        args.sse = False
        
        # Execute run command
        commands.run_command(args)
        
        # Verify process manager was called
        mock_process_manager.return_value.start_process.assert_called_once()
        call_args = mock_process_manager.return_value.start_process.call_args[0]
        assert call_args[0] == "test-server"  # name
        assert isinstance(call_args[1], list)  # command
        assert isinstance(call_args[2], dict)  # env


class TestCliParsing:
    def test_parse_run_command(self, monkeypatch):
        """Test parsing the run command."""
        # Mock the command function
        mock_run = mock.Mock()
        monkeypatch.setattr(commands, "run_command", mock_run)
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Test without detach
        args = commands.parse_args(["run", "test-server"])
        commands.run_command(args)
        mock_run.assert_called_once()
        
        # Reset mock for next test
        mock_run.reset_mock()
        
        # Test with detach
        args = commands.parse_args(["run", "--detach", "test-server"])
        commands.run_command(args)
        assert mock_run.call_count == 1

    def test_parse_add_command(self, monkeypatch):
        """Test parsing the add command."""
        # Mock the command function
        mock_add = mock.Mock()
        monkeypatch.setattr(commands, "add_command", mock_add)
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Test with repo URL
        args = commands.parse_args(["add", "https://github.com/test/repo"])
        commands.add_command(args)
        mock_add.assert_called_once()
        
        # Reset mock for next test
        mock_add.reset_mock()
        
        # Test with custom name
        args = commands.parse_args(["add", "--name", "custom-name", "https://github.com/test/repo"])
        commands.add_command(args)
        assert mock_add.call_count == 1

    def test_parse_remove_command(self, monkeypatch):
        """Test parsing the remove command."""
        # Mock the command function
        mock_remove = mock.Mock()
        monkeypatch.setattr(commands, "remove_command", mock_remove)
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        args = commands.parse_args(["remove", "test-server"])
        commands.remove_command(args)
        mock_remove.assert_called_once()

    def test_parse_ps_command(self, monkeypatch):
        """Test parsing the ps command."""
        # Mock the command function
        mock_ps = mock.Mock()
        monkeypatch.setattr(commands, "ps_command", mock_ps)
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        args = commands.parse_args(["ps"])
        commands.ps_command(args)
        mock_ps.assert_called_once()

    def test_parse_status_command(self, monkeypatch):
        """Test parsing the status command."""
        # Mock the command function
        mock_status = mock.Mock()
        monkeypatch.setattr(commands, "status_command", mock_status)
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        args = commands.parse_args(["status", "test-server"])
        commands.status_command(args)
        mock_status.assert_called_once()