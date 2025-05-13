import subprocess
from pathlib import Path
from typing import List

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client

from .exceptions import SetupError
from .params import MCPServerConfig, MCPServersParams


class MCPServers:
    def __init__(self, servers_params: MCPServersParams):
        self.servers_params = servers_params
        self.cache_dir = self._get_cache_dir()
        # Run setup for all servers during initialization
        self._setup_all_servers()

    def _get_cache_dir(self) -> Path:
        """Get the cache directory path, creating it if it doesn't exist."""
        # Use global cache directory
        cache_dir = Path.home() / ".mcphub" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _clone_repository(self, repo_url: str, repo_name: str) -> Path:
        """Clone a repository into the cache directory."""
        if not repo_url:
            raise SetupError(
                "Repository URL is required but was not provided. "
                "Please configure the repo_url field in .mcphub.json for this server."
            )
            
        repo_dir = self.cache_dir / repo_name.split('/')[-1]
        
        if repo_dir.exists():
            print(f"Repository already exists at {repo_dir}")
            return repo_dir

        try:
            subprocess.run(
                ["git", "clone", repo_url, str(repo_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Successfully cloned repository to {repo_dir}")
            return repo_dir
        except subprocess.CalledProcessError as e:
            raise SetupError(f"Failed to clone repository {repo_url}: {e.stderr}")

    def _run_setup_script(self, script_path: Path, setup_script: str) -> None:
        """Run the setup script in the repository directory."""
        try:
            # Create a temporary shell script
            script_file = script_path / "setup_temp.sh"
            with open(script_file, "w") as f:
                f.write("#!/bin/bash\n")
                f.write(setup_script + "\n")
            
            # Make the script executable
            script_file.chmod(0o755)
            
            # Run the script
            subprocess.run(
                [str(script_file)],
                check=True,
                capture_output=True,
                text=True,
                cwd=script_path
            )
            
            # Clean up
            script_file.unlink()
            
            print(f"Successfully executed setup script: {setup_script} in {script_path}")
        except subprocess.CalledProcessError as e:
            raise SetupError(f"Failed to run setup script '{setup_script}' in {script_path}: {e.stderr}")
        except Exception as e:
            raise SetupError(f"Error during setup script execution: {str(e)}")

    def _update_server_path(self, server_config: MCPServerConfig, repo_dir: Path) -> None:
        """Update the server_path in the server configuration."""
        self.servers_params.update_server_path(server_config.server_name, str(repo_dir))
        print(f"Updated server path for {server_config.server_name}: {repo_dir}")

    def setup_server(self, server_config: MCPServerConfig) -> None:
        """Set up a single server if it has repo_url and setup_script."""
        if not (server_config.repo_url and server_config.setup_script):
            print(f"Skipping setup for {server_config.package_name}: No repo_url or setup_script specified")
            return

        try:
            # Clone the repository
            repo_dir = self._clone_repository(server_config.repo_url, server_config.package_name)
            
            # Run setup script
            if repo_dir.exists():
                self._run_setup_script(repo_dir, server_config.setup_script)
                # Update server_path after successful setup
                self._update_server_path(server_config, repo_dir)
            else:
                raise SetupError(f"Setup script not found: {repo_dir}")

        except (SetupError, FileNotFoundError) as e:
            print(f"Error setting up server {server_config.package_name}: {str(e)}")
            raise

    def _setup_all_servers(self) -> None:
        """Set up all servers that have repo_url and setup_script configured."""
        print("Starting setup of all MCP servers...")
        
        for server_config in self.servers_params.servers_params:
            try:
                self.setup_server(server_config)
            except Exception as e:
                print(f"Failed to set up server {server_config.package_name}: {str(e)}")
                # Continue with other servers even if one fails
                continue

        print("Completed server setup process")

    async def list_tools(self, server_name: str) -> List[Tool]:
        """List all tools available in the server."""
        server_params = self.servers_params.retrieve_server_params(server_name)
        server_params = StdioServerParameters(
            command=server_params.command,
            args=server_params.args,
            env=server_params.env,
            cwd=server_params.cwd
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return tools.tools
    
