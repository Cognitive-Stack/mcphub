from mcphub.mcp_servers.params import MCPServerSSEConfig

try:
    from typing import List

    from autogen_ext.tools.mcp import (SseServerParams, StdioMcpToolAdapter,
                                       StdioServerParams, mcp_server_tools)

    from ..mcp_servers.params import MCPServerStdioConfig
    from .base import MCPBaseAdapter

    class MCPAutogenAdapter(MCPBaseAdapter):
        async def create_adapters(self, mcp_name: str) -> List[StdioMcpToolAdapter]:
            server_params = self.get_server_params(mcp_name)
            autogen_mcp_server_params = None
            if isinstance(server_params, MCPServerStdioConfig):
                autogen_mcp_server_params = StdioServerParams(
                    command=server_params.command,
                    args=server_params.args,
                    env=server_params.env,
                    cwd=server_params.cwd
                )
            elif isinstance(server_params, MCPServerSSEConfig):
                autogen_mcp_server_params = SseServerParams(
                    url=server_params.url,
                    headers=server_params.headers,
                    timeout=server_params.timeout,
                    sse_read_timeout=server_params.sse_read_timeout
                )
            else:
                raise ValueError(f"Unsupported server params type: {type(server_params)}")
            
            tools = await mcp_server_tools(autogen_mcp_server_params)
            return tools
                
except ImportError:
    class MCPAutogenAdapter:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("Autogen dependencies not found. Install with: pip install mcphub[autogen]") 