"""Command handlers for MCPHub CLI."""
import sys
import time
import os
import psutil
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Confirm

from .utils import (
    load_config,
    save_config,
    DEFAULT_CONFIG,
    get_config_path,
    remove_server_config,
    list_configured_servers,
    console,
    show_error,
    show_warning,
    show_success,
    show_code_block,
    show_status,
    check_env_var
)
from .process_manager import ProcessManager


def handle_add(repo_url: str, server_name: Optional[str] = None, 
               non_interactive: bool = False) -> None:
    """Add an MCP server from a GitHub repository to the local config.
    
    Args:
        repo_url: URL of the GitHub repository to add
        server_name: Custom name for the server (defaults to repo name)
        non_interactive: Whether to skip prompts for environment variables
    """
    steps = [
        "Validating repository URL",
        "Fetching repository README",
        "Parsing MCP configuration",
        "Adding server configuration"
    ]
    
    # Extract server name from repo URL if not provided
    if not server_name:
        # Parse GitHub URL to handle various formats including subdirectories
        parsed_url = urlparse(repo_url)
        
        if parsed_url.netloc != "github.com":
            show_error(
                "Only GitHub repositories are supported",
                help_text="Please provide a valid GitHub repository URL"
            )
            sys.exit(1)
            
        # Split the path to handle different GitHub URL formats
        path_parts = parsed_url.path.strip("/").split("/")
        
        # Standard repo URL: github.com/username/repo
        if len(path_parts) == 2:
            server_name = "/".join(path_parts)
            actual_repo_url = repo_url
        # Tree URL format: github.com/username/repo/tree/branch/path/to/subdir
        elif len(path_parts) >= 5 and path_parts[2] == "tree":
            username, repo = path_parts[0], path_parts[1]
            server_name = path_parts[-1]  # Use the last directory name
            # Use the base repo URL for fetching
            actual_repo_url = f"https://github.com/{username}/{repo}"
        else:
            show_error(
                "Invalid GitHub repository URL",
                help_text="URL should be in the format: https://github.com/username/repo or https://github.com/username/repo/tree/branch/path/to/dir"
            )
            sys.exit(1)
    else:
        actual_repo_url = repo_url
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Adding MCP Server", total=100)
            
            # Step 1: Validating repository URL
            progress.update(task, description="[cyan]Validating repository URL")
            time.sleep(0.5)  # Simulate work
            progress.update(task, advance=25)
            
            # Step 2: Fetching repository README
            progress.update(task, description="[cyan]Fetching repository README from " + actual_repo_url)
            config_path = get_config_path()
            
            # Create config file if it doesn't exist
            if not config_path.exists():
                console.print("[info]Creating new configuration file...[/]")
                save_config(DEFAULT_CONFIG)
            
            config = load_config()
            time.sleep(0.5)  # Simulate work
            progress.update(task, advance=25)
            
            # Step 3: Parsing MCP configuration
            progress.update(task, description="[cyan]Parsing MCP configuration")
            from ..mcp_servers.params import MCPServersParams
            servers_params = MCPServersParams(str(config_path))
            time.sleep(0.5)  # Simulate work
            progress.update(task, advance=25)
            
            # Step 4: Adding server configuration
            progress.update(task, description="[cyan]Adding server configuration")
            # Extract the specific subdirectory path if in tree format
            if "tree" in repo_url:
                path_parts = urlparse(repo_url).path.strip("/").split("/")
                tree_index = path_parts.index("tree") 
                if tree_index + 2 < len(path_parts):  # Has subdirectory after branch
                    # Get the path after the branch name
                    subdirectory = "/".join(path_parts[tree_index+2:])
                    servers_params.add_server_from_repo(server_name, actual_repo_url, subdirectory=subdirectory)
                else:
                    servers_params.add_server_from_repo(server_name, actual_repo_url)
            else:
                servers_params.add_server_from_repo(server_name, actual_repo_url)
            time.sleep(0.5)  # Simulate work
            progress.update(task, advance=25)
        
        show_success(
            f"Successfully added configuration for '{server_name}' from {repo_url}",
            "You can now run the server using 'mcphub run'"
        )
        
        # Check required environment variables
        server_config = servers_params.retrieve_server_params(server_name)
        if hasattr(server_config, 'env') and server_config.env is not None:
            console.print("\n[info]Checking Environment Variables[/]")
            
            # Initialize config for this server if needed
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            if server_name not in config["mcpServers"]:
                config["mcpServers"][server_name] = {}
            if "env" not in config["mcpServers"][server_name]:
                config["mcpServers"][server_name]["env"] = {}
            
            # Check each environment variable
            found_vars = {}
            missing_vars = []
            
            for var in server_config.env:
                value = check_env_var(var)
                if value:
                    console.print(f"[success]✓ Found {var} in environment[/]")
                    found_vars[var] = value
                else:
                    console.print(f"[warning]✗ {var} not found in environment[/]")
                    missing_vars.append(var)
            
            # Add found variables to config
            if found_vars:
                config["mcpServers"][server_name]["env"].update(found_vars)
                save_config(config)
                console.print("\n[success]Added existing environment variables to config[/]")
            
            # Handle missing variables
            if missing_vars and not non_interactive:
                console.print("\n[info]The following environment variables must be added to .mcphub.json:[/]")
                for var in missing_vars:
                    console.print(f"\n[info]Add to .mcphub.json under mcpServers.{server_name}.env:[/]")
                    console.print(f"[code]\"{var}\": \"your-value-here\"[/]")
                
                if not Confirm.ask("\nDo you want to continue without setting these variables?"):
                    show_warning(
                        "Required environment variables are missing",
                        "Please add them to .mcphub.json before running the server"
                    )
                    sys.exit(1)
            
    except ValueError as e:
        show_error("Failed to add server", e)
        sys.exit(1)
    except Exception as e:
        show_error("Failed to add server", e)
        sys.exit(1)


def handle_remove(server_name: str) -> None:
    """Remove an MCP server configuration from the local config.
    
    Args:
        server_name: The name of the server to remove
    """
    steps = [
        "Checking server configuration",
        "Removing server settings",
        "Updating configuration file"
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Removing MCP Server", total=100)
        
        # Step 1: Check server config
        progress.update(task, description="[cyan]Checking server configuration")
        config = load_config()
        server_exists = server_name in config.get("mcpServers", {})
        
        if not server_exists:
            progress.stop()
            show_error(
                f"MCP server '{server_name}' not found in configuration",
                help_text="Use 'mcphub ps' to see available servers"
            )
            sys.exit(1)
        
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 2: Remove server settings
        progress.update(task, description="[cyan]Removing server settings")
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 3: Update config file
        progress.update(task, description="[cyan]Updating configuration file")
        remove_server_config(server_name)
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=34)
    
    show_success(
        f"Successfully removed server '{server_name}'",
        "The configuration has been updated"
    )


def handle_list() -> None:
    """List all configured MCP servers without process details.
    
    This provides a simple overview of all configured servers in the 
    ~/.mcphub/.mcphub.json configuration file.
    """
    # Load configured servers
    configured = list_configured_servers()
    
    if configured:
        # Create a table for servers
        table = Table(title="MCP Servers")
        table.add_column("NAME", style="cyan")
        table.add_column("COMMAND", style="cyan", no_wrap=False)
        table.add_column("PACKAGE", style="cyan")
        table.add_column("REPOSITORY", style="cyan")
        table.add_column("ENV VARS", style="cyan")
        
        for name, server_config in configured.items():
            # Format command (truncate if too long)
            command = server_config.get("command", "N/A")
            if "args" in server_config:
                command_args = " ".join(server_config["args"])
                command = f"{command} {command_args}"
            
            if len(command) > 40:
                command = command[:37] + "..."
            
            # Get package name
            package = server_config.get("package_name", "N/A")
            
            # Get repository
            repo = server_config.get("repo_url", "N/A")
            
            # Count environment variables
            env_vars = len(server_config.get("env", {}))
            env_vars_display = str(env_vars) if env_vars > 0 else "None"
            
            table.add_row(
                name,
                command,
                package,
                repo,
                env_vars_display
            )
        
        console.print(table)
        console.print(f"\n[info]Total: {len(configured)} server(s)[/]")
        console.print("[info]Use 'mcphub ps' to see process details[/]")
    else:
        show_warning(
            "No servers configured in global config (~/.mcphub/.mcphub.json)",
            "Use 'mcphub add' to add a new server"
        )


def handle_ps() -> None:
    """List all running MCP server processes, similar to docker ps.
    
    Shows no output when no processes are running, making it similar to docker ps.
    """
    # Load configuration and initialize process manager
    configured = list_configured_servers()
    process_manager = ProcessManager()
    
    # Get process information
    processes = process_manager.list_processes()
    
    # If no processes are running, return with no output
    if not processes:
        return
    
    # Create a table similar to docker ps
    table = Table(title="MCP Servers")
    table.add_column("NAME", style="cyan")
    table.add_column("INSTANCE", style="cyan")
    table.add_column("STATUS", style="status")
    table.add_column("PID", style="cyan")
    table.add_column("PORTS", style="cyan")
    table.add_column("COMMAND", style="cyan", no_wrap=False)
    table.add_column("CREATED", style="cyan")
    table.add_column("UPTIME", style="cyan")
    
    # Sort processes by name and port for consistent display
    processes.sort(key=lambda p: (p["name"], p.get("ports", [None])[0] or 0))
    
    # Track instances per server for numbering
    instance_counts = {}
    
    for process_info in processes:
        name = process_info["name"]
        
        # Get instance number for this server
        instance_counts[name] = instance_counts.get(name, 0) + 1
        instance_num = instance_counts[name]
        
        # Format instance identifier
        instance = f"#{instance_num}"
        if "ports" in process_info and process_info["ports"]:
            instance += f" (:{process_info['ports'][0]})"
        
        # Format status with color
        status = "[green]running[/]"
        if process_info.get("status") == "zombie":
            status = "[yellow]zombie[/]"
        elif process_info.get("status") != "running":
            status = f"[yellow]{process_info.get('status', 'unknown')}[/]"
        
        # Format PID
        pid = str(process_info.get("pid", "N/A"))
        
        # Format ports
        ports = ", ".join(map(str, process_info.get("ports", []))) or "N/A"
        
        # Format command (truncate if too long)
        command = process_info.get("command", "N/A")
        if len(command) > 50:
            command = command[:47] + "..."
        
        # Format created time
        created = process_info.get("start_time", "N/A")
        if created != "N/A":
            created = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Format uptime
        uptime = process_info.get("uptime", "N/A")
        
        table.add_row(
            name,
            instance,
            status,
            pid,
            ports,
            command,
            created,
            uptime
        )
        
        # Show warnings if any
        warnings = process_info.get("warnings", [])
        if warnings:
            for warning in warnings:
                console.print(f"[warning]⚠ {warning}[/]")
    
    console.print(table)
    
    # Show summary count
    total_instances = sum(instance_counts.values())
    if len(instance_counts) == total_instances:
        console.print(f"\n[info]Running: {total_instances} server(s)[/]")
    else:
        console.print(f"\n[info]Running: {total_instances} instance(s) of {len(instance_counts)} server(s)[/]")


def handle_status(server_name: str) -> None:
    """Show detailed status of an MCP server.
    
    Args:
        server_name: The name of the server to check
    """
    config = load_config()
    
    if server_name not in config.get("mcpServers", {}):
        show_error(
            f"MCP server '{server_name}' not found in configuration",
            help_text="Use 'mcphub list' to see available servers"
        )
        sys.exit(1)
    
    server_config = config["mcpServers"][server_name]
    
    # TODO: Add actual status check
    status = "Not Running"
    details = {
        "Command": server_config.get("command", "N/A"),
        "Working Directory": server_config.get("cwd", "N/A"),
        "Package": server_config.get("package_name", "N/A"),
        "Repository": server_config.get("repo_url", "N/A")
    }
    
    show_status(server_name, status, details)


def handle_run(server_name: str, sse: bool = False, port: int = 3000,
              base_url: str = "http://localhost:3000", 
              sse_path: str = "/sse", 
              message_path: str = "/message") -> None:
    """Run an MCP server with optional SSE support.
    
    Args:
        server_name: The name of the server to run
        sse: Whether to enable SSE support
        port: Port for the SSE server
        base_url: Base URL for the SSE server
        sse_path: Path for the SSE endpoint
        message_path: Path for the message endpoint
    """
    steps = [
        "Loading server configuration",
        "Preparing command",
        "Starting server"
    ]
    
    config = load_config()
    
    if server_name not in config.get("mcpServers", {}):
        show_error(
            f"MCP server '{server_name}' not found in configuration",
            help_text="Use 'mcphub list' to see available servers"
        )
        sys.exit(1)
    
    server_config = config["mcpServers"][server_name]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Running MCP Server", total=100)
        
        # Step 1: Load config
        progress.update(task, description="[cyan]Loading server configuration")
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 2: Prepare command
        progress.update(task, description="[cyan]Preparing command")
        cmd = []
        
        # Add SSE support if requested
        if sse:
            # Construct the stdio command based on server configuration
            stdio_cmd = []
            if "command" in server_config:
                stdio_cmd.append(server_config["command"])
            if "args" in server_config:
                stdio_cmd.extend(server_config["args"])
            
            # If no command specified, use package_name with npx
            if not stdio_cmd and "package_name" in server_config:
                stdio_cmd = ["npx", "-y", server_config["package_name"]]
            
            # Join the stdio command parts
            stdio_str = " ".join(stdio_cmd)
            
            # Add port to server config for tracking
            server_config["ports"] = [port]
            
            cmd.extend([
                "npx", "-y", "supergateway",
                "--stdio", stdio_str,
                "--port", str(port),
                "--baseUrl", base_url,
                "--ssePath", sse_path,
                "--messagePath", message_path
            ])
        else:
            # Use the server's configured command
            if "command" in server_config:
                cmd.append(server_config["command"])
            if "args" in server_config:
                cmd.extend(server_config["args"])
        
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 3: Start server
        progress.update(task, description="[cyan]Starting server")
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=34)
    
    try:
        show_code_block(" ".join(cmd))
        console.print("[info]Server is running...[/]")
        
        # Set up environment variables from config
        env = os.environ.copy()
        if "env" in server_config:
            env.update(server_config["env"])
        
        # Start process using ProcessManager
        process_manager = ProcessManager()
        pid = process_manager.start_process(server_name, cmd, env)
        
        # Wait for process to complete
        process = psutil.Process(pid)
        process.wait()
        
    except KeyboardInterrupt:
        show_success("Server stopped")
    except Exception as e:
        show_error("Error running server", e)
        sys.exit(1)


def handle_kill(pid: int, force: bool = False) -> None:
    """Kill a running MCP server process.
    
    Args:
        pid: Process ID to kill
        force: Whether to force kill the process (SIGKILL)
    """
    steps = [
        "Checking process",
        "Stopping process",
        "Cleaning up"
    ]
    
    process_manager = ProcessManager()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Killing MCP Server", total=100)
        
        # Step 1: Check process
        progress.update(task, description="[cyan]Checking process")
        
        # Get process info
        process_info = process_manager.get_process_info(pid)
        if not process_info:
            progress.stop()
            show_error(
                f"Process {pid} not found or not an MCP server",
                help_text="Use 'mcphub ps' to see running MCP servers"
            )
            sys.exit(1)
            return  # This ensures we don't continue if process_info is None
        
        # Store process name before we potentially lose it
        process_name = process_info.get("name", str(pid))
        
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 2: Stop process
        progress.update(task, description="[cyan]Stopping process")
        
        # Try to stop the process
        if force:
            try:
                process = psutil.Process(pid)
                process.kill()  # Send SIGKILL
                show_success(f"Process {pid} killed forcefully")
            except psutil.NoSuchProcess:
                show_error(f"Process {pid} not found")
                sys.exit(1)
            except psutil.AccessDenied:
                show_error(
                    f"Access denied when trying to kill process {pid}",
                    help_text="Try running with sudo if you have permission"
                )
                sys.exit(1)
        else:
            if not process_manager.stop_process(pid):
                show_error(
                    f"Failed to stop process {pid}",
                    help_text="Try using -f/--force to force kill"
                )
                sys.exit(1)
        
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 3: Clean up
        progress.update(task, description="[cyan]Cleaning up")
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=34)
    
    show_success(
        f"Successfully stopped MCP server process {pid}",
        f"Server '{process_name}' is no longer running"
    ) 