from abc import ABC
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Tuple, Any

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
from ..mcp_servers.params import MCPServersParams
from ..mcp_servers.exceptions import ServerConfigNotFoundError

class MCPBaseAdapter(ABC):
    def __init__(self, servers_params: MCPServersParams):
        self.servers_params = servers_params

    def get_server_params(self, mcp_name: str) -> StdioServerParameters:
        """Convert server config to StdioServerParameters or raise error if not found"""
        server_config = self.servers_params.retrieve_server_params(mcp_name)
        if not server_config:
            raise ServerConfigNotFoundError(f"Server configuration not found for '{mcp_name}'")
        return StdioServerParameters(
            command=server_config.command,
            args=server_config.args,
            env=server_config.env,
            cwd=server_config.cwd
        )
    
    async def get_tools(self, mcp_name: str) -> List[Tool]:
        """Get tools from the server"""
        async with self.create_session(mcp_name) as session:
            tools = await session.list_tools()
            return tools.tools

    @asynccontextmanager
    async def create_session(self, mcp_name: str) -> AsyncGenerator[ClientSession, None]:
        """Create and initialize a client session for the given MCP server"""
        server_params = self.get_server_params(mcp_name)
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session