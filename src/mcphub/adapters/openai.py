from typing import Union

from mcphub.mcp_servers.params import MCPServerSSEConfig, MCPServerStdioConfig

try:
    from agents.mcp import MCPServerSse, MCPServerStdio

    from .base import MCPBaseAdapter

    class MCPOpenAIAgentsAdapter(MCPBaseAdapter):
        def create_server(self, mcp_name: str, cache_tools_list: bool = True) -> Union[MCPServerStdio, MCPServerSse]:
            server_params = self.get_server_params(mcp_name)
            if isinstance(server_params, MCPServerStdioConfig):
                return MCPServerStdio(
                    params=server_params,
                    cache_tools_list=cache_tools_list
                )
            elif isinstance(server_params, MCPServerSSEConfig):
                return MCPServerSse(
                    params=server_params,
                    cache_tools_list=cache_tools_list
                )
            else:
                raise ValueError(f"Unsupported server params type: {type(server_params)}")
except ImportError:
    class MCPOpenAIAgentsAdapter:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("OpenAI Agents dependencies not found. Install with: pip install mcphub[openai]") 