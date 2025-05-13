from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from mcp import Tool

from .adapters.autogen import MCPAutogenAdapter
from .adapters.langchain import MCPLangChainAdapter
from .adapters.openai import MCPOpenAIAgentsAdapter
from .mcp_servers import MCPServers, MCPServersParams, MCPServerConfig


@dataclass
class MCPHub:
    servers_params: MCPServersParams = field(init=False)
    _openai_adapter: Optional[MCPOpenAIAgentsAdapter] = field(init=False, default=None)
    _langchain_adapter: Optional[MCPLangChainAdapter] = field(init=False, default=None)
    _autogen_adapter: Optional[MCPAutogenAdapter] = field(init=False, default=None)
    
    def __post_init__(self):
        config_path = self._find_config_path()
        self.servers_params = MCPServersParams(config_path)
        self.servers = MCPServers(self.servers_params)

    def _find_config_path(self) -> Optional[str]:
        global_config = Path.home() / ".mcphub" / ".mcphub.json"
        if global_config.exists():
            return str(global_config)
        raise FileNotFoundError("Global configuration file '~/.mcphub/.mcphub.json' not found")

    @property
    def openai_adapter(self) -> MCPOpenAIAgentsAdapter:
        if self._openai_adapter is None:
            self._openai_adapter = MCPOpenAIAgentsAdapter(self.servers_params)
        return self._openai_adapter

    @property
    def langchain_adapter(self) -> MCPLangChainAdapter:
        if self._langchain_adapter is None:
            self._langchain_adapter = MCPLangChainAdapter(self.servers_params)
        return self._langchain_adapter

    @property
    def autogen_adapter(self) -> MCPAutogenAdapter:
        if self._autogen_adapter is None:
            self._autogen_adapter = MCPAutogenAdapter(self.servers_params)
        return self._autogen_adapter

    def fetch_openai_mcp_server(self, mcp_name: str, cache_tools_list: bool = True) -> Any:
        return self.openai_adapter.create_server(mcp_name, cache_tools_list=cache_tools_list)
    
    async def fetch_langchain_mcp_tools(self, mcp_name: str) -> List[Any]:
        return await self.langchain_adapter.create_tools(mcp_name)
    
    async def fetch_autogen_mcp_adapters(self, mcp_name: str) -> List[Any]:
        return await self.autogen_adapter.create_adapters(mcp_name)
    
    async def list_tools(self, server_name: str) -> List[Tool]:
        return await self.servers.list_tools(server_name)
    
    def list_servers(self) -> List[MCPServerConfig]:
        return self.servers_params.list_servers()

    