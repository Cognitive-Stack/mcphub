from pathlib import Path
from unittest import mock

import pytest

from mcphub.mcp_servers import MCPServerConfig
from mcphub.mcp_servers.exceptions import ServerConfigNotFoundError
from mcphub.mcphub import MCPHub


class TestMCPHub:
    @mock.patch('pathlib.Path.cwd')
    @mock.patch('pathlib.Path.exists')
    @mock.patch('pathlib.Path.home')
    def test_find_config_path_success(self, mock_home, mock_exists, mock_cwd, temp_config_file):
        """Test successfully finding config path."""
        # Mock cwd, home and exists to find the config file
        mock_cwd.return_value = Path(temp_config_file).parent
        mock_home.return_value = Path(temp_config_file).parent
        mock_exists.return_value = True
        
        # Initialize MCPHub which will call _find_config_path
        hub = MCPHub()
        
        # Test that server_params was initialized correctly
        assert hub.servers_params is not None
    
    @mock.patch('pathlib.Path.cwd')
    @mock.patch('pathlib.Path.exists')
    @mock.patch('pathlib.Path.home')
    def test_find_config_path_failure(self, mock_home, mock_exists, mock_cwd):
        """Test failure to find config path."""
        # Mock cwd, home and exists to not find the config file
        mock_cwd.return_value = Path("/some/path")
        mock_home.return_value = Path("/some/home")
        mock_exists.return_value = False
        
        # Initializing MCPHub should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            hub = MCPHub()
    
    @mock.patch('mcphub.adapters.openai.MCPOpenAIAgentsAdapter')
    def test_fetch_openai_mcp_server(self, MockAdapter, mock_mcphub_init, temp_config_file):
        """Test fetching an OpenAI MCP server."""
        # Create mock adapter and server
        mock_server = mock.MagicMock()
        mock_adapter = mock.MagicMock()
        mock_adapter.create_server.return_value = mock_server
        
        hub = MCPHub()
        # Mock the property directly
        hub._openai_adapter = mock_adapter
        
        server = hub.fetch_openai_mcp_server("test-server")
        
        # Verify create_server was called correctly
        mock_adapter.create_server.assert_called_once_with("test-server", cache_tools_list=True)
        
        # Verify we got the mock server back
        assert server == mock_server
    
    @mock.patch('mcphub.mcp_servers.MCPServers.get_langchain_mcp_tools')
    async def test_fetch_langchain_mcp_tools(self, mock_get_tools, mock_mcphub_init, temp_config_file):
        """Test fetching Langchain MCP tools."""
        mock_tools = ["tool1", "tool2"]
        mock_get_tools.return_value = mock_tools
        
        hub = MCPHub()
        tools = await hub.fetch_langchain_mcp_tools("test-server")
        
        assert tools == mock_tools
        mock_get_tools.assert_called_once_with("test-server", True)
    
    @mock.patch('mcphub.mcp_servers.MCPServers.make_autogen_mcp_adapters')
    async def test_fetch_autogen_mcp_adapters(self, mock_make_adapters, mock_mcphub_init, temp_config_file):
        """Test fetching Autogen MCP adapters."""
        mock_adapters = ["adapter1", "adapter2"]
        mock_make_adapters.return_value = mock_adapters
        
        hub = MCPHub()
        adapters = await hub.fetch_autogen_mcp_adapters("test-server")
        
        assert adapters == mock_adapters
        mock_make_adapters.assert_called_once_with("test-server")
    
    @mock.patch('mcphub.mcp_servers.MCPServers.list_tools')
    async def test_list_tools(self, mock_list_tools, mock_mcphub_init, temp_config_file):
        """Test listing tools from an MCP server."""
        mock_tools = ["tool1", "tool2"]
        mock_list_tools.return_value = mock_tools
        
        hub = MCPHub()
        tools = await hub.list_tools("test-server")
        
        assert tools == mock_tools
        mock_list_tools.assert_called_once_with("test-server")

@pytest.mark.asyncio
@mock.patch('pathlib.Path.cwd')
@mock.patch('pathlib.Path.exists')
async def test_mcphub_adapters_initialization(mock_exists, mock_cwd, test_config_path):
    """Test that adapters are not initialized until accessed."""
    # Mock config file location
    mock_cwd.return_value = Path(test_config_path).parent
    mock_exists.return_value = True
    
    hub = MCPHub()
    
    # Test that adapters are not initialized until accessed
    assert hub._openai_adapter is None
    assert hub._langchain_adapter is None
    assert hub._autogen_adapter is None
    
    # Verify servers_params was initialized correctly
    assert hub.servers_params is not None
    
    # Optional: Test that accessing property initializes adapter
    _ = hub.openai_adapter
    assert hub._openai_adapter is not None
    assert hub._langchain_adapter is None  # Still None because not accessed
    assert hub._autogen_adapter is None    # Still None because not accessed

@pytest.mark.asyncio
@mock.patch('pathlib.Path.cwd')
@mock.patch('pathlib.Path.exists')
@mock.patch('mcphub.adapters.openai.MCPOpenAIAgentsAdapter.create_server')  # Mock the method directly
async def test_mcphub_openai_integration(mock_create_server, mock_exists, mock_cwd, test_config_path):
    """Test OpenAI adapter integration."""
    # Mock config file location
    mock_cwd.return_value = Path(test_config_path).parent
    mock_exists.return_value = True
    
    # Setup mock server
    mock_server = mock.MagicMock(name='mock_server')
    mock_create_server.return_value = mock_server
    
    hub = MCPHub()
    server = hub.fetch_openai_mcp_server("test-mcp")
    
    # Verify everything worked
    assert server is mock_server  # Should pass now
    mock_create_server.assert_called_once_with("test-mcp", cache_tools_list=True)

@pytest.mark.asyncio
@mock.patch('pathlib.Path.cwd')
@mock.patch('pathlib.Path.exists')
@mock.patch('mcphub.adapters.langchain.MCPLangChainAdapter.create_tools')  # Mock the method directly
async def test_mcphub_langchain_integration(mock_create_tools, mock_exists, mock_cwd, test_config_path):
    """Test LangChain adapter integration."""
    # Mock config file location
    mock_cwd.return_value = Path(test_config_path).parent
    mock_exists.return_value = True
    
    # Setup mock tools
    mock_tools = ["tool1", "tool2"]
    mock_create_tools.return_value = mock_tools
    
    hub = MCPHub()
    tools = await hub.fetch_langchain_mcp_tools("test-mcp")
    
    # Verify everything worked
    assert tools is mock_tools  # Use 'is' for identity comparison
    mock_create_tools.assert_called_once_with("test-mcp")

@pytest.mark.asyncio
@mock.patch('pathlib.Path.cwd')
@mock.patch('pathlib.Path.exists')
@mock.patch('mcphub.adapters.autogen.MCPAutogenAdapter.create_adapters')  # Mock the method directly
async def test_mcphub_autogen_integration(mock_create_adapters, mock_exists, mock_cwd, test_config_path):
    """Test Autogen adapter integration."""
    # Mock config file location
    mock_cwd.return_value = Path(test_config_path).parent
    mock_exists.return_value = True
    
    # Setup mock adapters
    mock_adapters = ["adapter1", "adapter2"]
    mock_create_adapters.return_value = mock_adapters
    
    hub = MCPHub()
    adapters = await hub.fetch_autogen_mcp_adapters("test-mcp")
    
    # Verify everything worked
    assert adapters is mock_adapters  # Use 'is' for identity comparison
    mock_create_adapters.assert_called_once_with("test-mcp")