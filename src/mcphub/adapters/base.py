from abc import ABC
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Union

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from ..mcp_servers.params import MCPServerSSEConfig, MCPServerStdioConfig, MCPServersParams
from ..mcp_servers.exceptions import ServerConfigNotFoundError

class MCPBaseAdapter(ABC):
    def __init__(self, servers_params: MCPServersParams):
        self.servers_params = servers_params

    def get_server_params(self, mcp_name: str) -> Union[MCPServerStdioConfig, MCPServerSSEConfig]:
        """Convert server config to StdioServerParameters or raise error if not found"""
        server_config = self.servers_params.retrieve_server_params(mcp_name)
        return server_config
    
    async def get_tools(self, mcp_name: str) -> List[Tool]:
        """Get tools from the server"""
        async with self.create_session(mcp_name) as session:
            tools = await session.list_tools()
            return tools.tools

    @asynccontextmanager
    async def create_session(self, mcp_name: str) -> AsyncGenerator[ClientSession, None]:
        """Create and initialize a client session for the given MCP server"""
        server_param = self.servers_params.retrieve_server_params(mcp_name)
        if not server_param:
            raise ServerConfigNotFoundError(f"Server configuration not found for '{mcp_name}'")
        
        if isinstance(server_param, MCPServerStdioConfig):
            stdio_server_params = StdioServerParameters(
                command=server_param.command,
                args=server_param.args,
                env=server_param.env,
                cwd=server_param.cwd
            )

            async with stdio_client(stdio_server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        elif isinstance(server_param, MCPServerSSEConfig):
            async with sse_client(
                url=server_param.url,
                headers=server_param.headers,
                timeout=server_param.timeout,
                sse_read_timeout=server_param.sse_read_timeout
            ) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        else:
            raise ValueError(f"Unsupported server type: {type(server_param)}")