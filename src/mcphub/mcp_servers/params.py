import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import openai
import requests
from urllib.parse import urlparse

from mcp import StdioServerParameters

from .exceptions import ServerConfigNotFoundError
from .schemas import MCPServerConfigSchema

@dataclass
class MCPServerConfig:
    package_name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    server_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    repo_url: Optional[str] = None
    setup_script: Optional[str] = None
    cwd: Optional[str] = None
    
class MCPServersParams:
    def __init__(self, config_path: Optional[str]):
        self.config_path = config_path
        self._servers_params = self._load_servers_params()
        # Initialize OpenAI client if API key is available
        self.openai_client = None
        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = openai.OpenAI()

    @property
    def servers_params(self) -> List[MCPServerConfig]:
        """Return the list of server parameters."""
        server_configs = []
        for server_name, server_params in self._servers_params.items():
            server_params.server_name = server_name
            server_configs.append(server_params)
        return server_configs

    def _load_user_config(self) -> Dict:
        """Load user configuration from JSON file."""
        # If no config path is provided, return empty dict
        if not self.config_path:
            raise ServerConfigNotFoundError("No configuration file path provided")
            
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                return config.get("mcpServers", {})
        except FileNotFoundError:
            # For test compatibility: raise FileNotFoundError when path is specified but file doesn't exist
            # Only return empty dict when path is None
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

    def _get_github_readme(self, repo_url: str) -> str:
        """Fetch README content from GitHub repository."""
        parsed_url = urlparse(repo_url)
        if parsed_url.netloc != "github.com":
            raise ValueError("Only GitHub repositories are supported")
        
        # Convert github.com URL to raw content URL
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) != 2:
            raise ValueError("Invalid GitHub repository URL")
        
        owner, repo = path_parts
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
        
        response = requests.get(raw_url)
        if response.status_code == 200:
            return response.text
        else:
            # Try master branch if main doesn't exist
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
            response = requests.get(raw_url)
            if response.status_code == 200:
                return response.text
            raise ValueError(f"Could not fetch README from {repo_url}")

    def _parse_readme_with_openai(self, readme_content: str) -> Dict:
        """Use OpenAI to parse README and extract MCP server configuration."""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")

        prompt = f"""Please analyze this MCP server README and extract the configuration in JSON format.
        The configuration should include:
        - command: The command to run the server
        - args: List of command line arguments
        - env: Environment variables (if any)
        - setup_script: Any setup script needed (if any)
        
        README content:
        {readme_content}
        
        Return only the JSON configuration, nothing else."""

        try:
            response = self.openai_client.responses.parse(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": "You are a helpful assistant that extracts MCP server configuration from READMEs."},
                    {"role": "user", "content": prompt}
                ],
                text_format=MCPServerConfigSchema
            )
            # Validate response structure
            if not hasattr(response, "output_parsed") or not hasattr(response.output_parsed, "model_dump"):
                raise ValueError("Unexpected OpenAI API response format")
            config = response.output_parsed.model_dump()
            return config
        except json.JSONDecodeError as e:
            # Log the problematic response content for debugging
            raise ValueError(f"Failed to parse OpenAI response as JSON: {e}")
        except openai.error.OpenAIError as e:
            # Log OpenAI-specific errors
            raise RuntimeError(f"OpenAI API error: {e}")
        except Exception as e:
            # Catch-all for any other unexpected exceptions
            raise RuntimeError(f"Unexpected error while parsing OpenAI response: {e}")

    def add_server_from_repo(self, server_name: str, repo_url: str) -> None:
        """Add a new server configuration by analyzing its GitHub repository README."""
        try:
            # Fetch README content
            readme_content = self._get_github_readme(repo_url)
            
            # Parse README with OpenAI
            config = self._parse_readme_with_openai(readme_content)
            
            # Create server configuration
            server_config = MCPServerConfig(
                package_name=server_name,
                command=config["command"],
                args=config["args"],
                env=config.get("env", {}),
                repo_url=repo_url,
                setup_script=config.get("setup_script")
            )
            
            # Add to existing configuration
            self._servers_params[server_name] = server_config
            
            # Save to .mcphub.json
            self._save_config()
            
        except Exception as e:
            raise ValueError(f"Failed to add server from repository: {str(e)}")

    def _save_config(self) -> None:
        """Save current configuration to .mcphub.json."""
        if not self.config_path:
            raise ValueError("No configuration path specified")
            
        config = {"mcpServers": {}}
        for server_name, server_params in self._servers_params.items():
            config["mcpServers"][server_name] = {
                "package_name": server_params.package_name,
                "command": server_params.command,
                "args": server_params.args,
                "env": server_params.env,
                "repo_url": server_params.repo_url,
                "setup_script": server_params.setup_script
            }
            
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    def _load_servers_params(self) -> Dict[str, MCPServerConfig]:
        config = self._load_user_config()
        servers = {}
        
        for mcp_name, server_config in config.items():
            package_name = server_config.get("package_name")
            
            if not package_name:
                raise ValueError(
                    f"Configuration for server '{mcp_name}' is missing the required 'package_name' field. "
                    "As of the latest update, all server configurations must explicitly include a 'package_name'. "
                    "Please update your configuration file to include this field."
                )
            
            # Get command and args with defaults
            command = server_config.get("command", None)
            args = server_config.get("args", None)
            
            # Skip if command or args is None
            if command is None or args is None:
                raise ValueError(
                    f"Invalid server '{mcp_name}' configuration: command or args is None. "
                    f"Command: {command}, Args: {args}"
                )
                
            servers[mcp_name] = MCPServerConfig(
                package_name=package_name,
                command=command,
                args=args,
                env=server_config.get("env", {}),
                description=server_config.get("description"),
                tags=server_config.get("tags"),
                repo_url=server_config.get("repo_url"),
                setup_script=server_config.get("setup_script")
            )
        
        return servers
    
    def list_servers(self) -> List[MCPServerConfig]:
        return self.servers_params
    
    def retrieve_server_params(self, server_name: str) -> MCPServerConfig:
        # First check in the loaded servers
        if server_name in self._servers_params:
            return self._servers_params[server_name]
        raise ServerConfigNotFoundError(f"Server '{server_name}' not found")
    
    def convert_to_stdio_params(self, server_name: str) -> StdioServerParameters:
        server_params = self.retrieve_server_params(server_name)
        if not server_params:
            raise ServerConfigNotFoundError(f"Server '{server_name}' not found")
        return StdioServerParameters(
            command=server_params.command,
            args=server_params.args,
            env=server_params.env,
        )
    
    def update_server_path(self, server_name: str, server_path: str) -> None:
        if server_name not in self._servers_params:
            raise ServerConfigNotFoundError(f"Server '{server_name}' not found")
        self._servers_params[server_name].cwd = server_path
