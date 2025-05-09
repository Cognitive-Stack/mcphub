"""CLI commands for mcphub."""
import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
from urllib.parse import urlparse
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
import time
from rich.prompt import Confirm
import psutil
from datetime import datetime

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
    show_animated_checklist,
    show_help_text,
    show_status,
    show_code_block,
    get_server_status
)
from .process_manager import ProcessManager

def check_env_var(var: str) -> Optional[str]:
    """Check if an environment variable exists and return its value."""
    try:
        result = subprocess.run(
            f"echo ${var}",
            shell=True,
            capture_output=True,
            text=True
        )
        value = result.stdout.strip()
        if not value or value == f"${var}":
            return None
        return value
    except Exception:
        return None

def add_command(args):
    """Add an MCP server from a GitHub repository to the local config."""
    steps = [
        "Validating repository URL",
        "Fetching repository README",
        "Parsing MCP configuration",
        "Adding server configuration"
    ]
    
    repo_url = args.repo_url
    # Extract server name from repo URL if not provided
    if args.mcp_name:
        server_name = args.mcp_name
    else:
        # Extract username/repo from GitHub URL
        parsed_url = urlparse(repo_url)
        if parsed_url.netloc != "github.com":
            show_error(
                "Only GitHub repositories are supported",
                help_text="Please provide a valid GitHub repository URL"
            )
            sys.exit(1)
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) != 2:
            show_error(
                "Invalid GitHub repository URL",
                help_text="URL should be in the format: https://github.com/username/repo"
            )
            sys.exit(1)
        server_name = "/".join(path_parts)
    
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
            progress.update(task, description="[cyan]Fetching repository README")
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
            servers_params.add_server_from_repo(server_name, repo_url)
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
            if missing_vars:
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

def remove_command(args):
    """Remove an MCP server configuration from the local config."""
    steps = [
        "Checking server configuration",
        "Removing server settings",
        "Updating configuration file"
    ]
    
    server_name = args.mcp_name
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
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 2: Remove server settings
        progress.update(task, description="[cyan]Removing server settings")
        if remove_server_config(server_name):
            progress.update(task, advance=33)
            
            # Step 3: Update config file
            progress.update(task, description="[cyan]Updating configuration file")
            time.sleep(0.5)  # Simulate work
            progress.update(task, advance=34)
            
            show_success(
                f"Removed configuration for '{server_name}' from .mcphub.json",
                "The server has been removed from your configuration"
            )
        else:
            show_error(
                f"MCP server '{server_name}' not found in current configuration",
                help_text="Use 'mcphub list' to see available servers"
            )
            # Show what's currently configured
            configured = list_configured_servers()
            if configured:
                console.print("\n[info]Currently configured servers:[/]")
                for name in configured:
                    console.print(f"[info]- {name}[/]")
            sys.exit(1)

def ps_command(args):
    """List all configured MCP servers with process details."""
    steps = [
        "Loading configuration",
        "Retrieving server list",
        "Displaying results"
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Listing MCP Servers", total=100)
        
        # Step 1: Load config
        progress.update(task, description="[cyan]Loading configuration")
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 2: Get server list
        progress.update(task, description="[cyan]Retrieving server list")
        configured = list_configured_servers()
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=33)
        
        # Step 3: Display results
        progress.update(task, description="[cyan]Displaying results")
        time.sleep(0.5)  # Simulate work
        progress.update(task, advance=34)
    
    if configured:
        # Create a table similar to docker ps
        table = Table(title="MCP Servers")
        table.add_column("NAME", style="cyan")
        table.add_column("STATUS", style="status")
        table.add_column("PORTS", style="cyan")
        table.add_column("COMMAND", style="cyan", no_wrap=False)
        table.add_column("CREATED", style="cyan")
        table.add_column("UPTIME", style="cyan")
        
        # Get process information from ProcessManager
        process_manager = ProcessManager()
        processes = process_manager.list_processes()
        
        # Create a map of process info by name
        process_map = {p["name"]: p for p in processes}
        
        for name, server_config in configured.items():
            # Get process info if running
            process_info = process_map.get(name, {})
            
            # Format status with color
            status = process_info.get("status", "Not Running")
            if status == "running":
                status = f"[green]{status}[/]"
            else:
                status = f"[red]{status}[/]"
            
            # Format ports
            ports = ", ".join(map(str, process_info.get("ports", []))) or "N/A"
            
            # Format command (truncate if too long)
            command = process_info.get("command", server_config.get("command", "N/A"))
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
                status,
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
        
        # Show summary
        running = sum(1 for p in processes if p["status"] == "running")
        total = len(configured)
        console.print(f"\n[info]Running: {running}, Total: {total}[/]")
    else:
        show_warning(
            "No servers configured in local .mcphub.json",
            "Use 'mcphub add' to add a new server"
        )

def status_command(args):
    """Show detailed status of an MCP server."""
    server_name = args.mcp_name
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

def run_command(args):
    """Run an MCP server with optional SSE support."""
    steps = [
        "Loading server configuration",
        "Preparing command",
        "Starting server"
    ]
    
    server_name = args.mcp_name
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
        if args.sse:
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
            
            cmd.extend([
                "npx", "-y", "supergateway",
                "--stdio", stdio_str,
                "--port", str(args.port),
                "--baseUrl", args.base_url,
                "--ssePath", args.sse_path,
                "--messagePath", args.message_path
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

def parse_args(args=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCPHub CLI tool for managing MCP server configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Add command
    add_parser = subparsers.add_parser(
        "add", 
        help="Add an MCP server from a GitHub repository to your local config",
        description="Add a new MCP server from a GitHub repository to your local configuration."
    )
    add_parser.add_argument(
        "repo_url",
        help="GitHub repository URL of the MCP server"
    )
    add_parser.add_argument(
        "mcp_name", 
        nargs="?",
        help="Name to give to the MCP server (defaults to username/repo from the GitHub URL)"
    )
    add_parser.add_argument(
        "-n", "--non-interactive",
        action="store_true",
        help="Don't prompt for environment variables"
    )
    
    # Remove command
    remove_parser = subparsers.add_parser(
        "remove", 
        help="Remove an MCP server configuration from your local config",
        description="Remove an MCP server configuration from your local configuration."
    )
    remove_parser.add_argument(
        "mcp_name",
        help="Name of the MCP server to remove"
    )
    
    # PS command (replaces list command)
    ps_parser = subparsers.add_parser(
        "ps",
        help="List all configured MCP servers with process details",
        description="List all MCP servers configured in your local configuration with detailed process information."
    )
    
    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show detailed status of an MCP server",
        description="Show detailed status information for a configured MCP server."
    )
    status_parser.add_argument(
        "mcp_name",
        help="Name of the MCP server to check"
    )
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run an MCP server with optional SSE support",
        description="Run a configured MCP server with optional Server-Sent Events (SSE) support."
    )
    run_parser.add_argument(
        "mcp_name",
        help="Name of the MCP server to run"
    )
    run_parser.add_argument(
        "--sse",
        action="store_true",
        help="Enable Server-Sent Events support"
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for SSE server (default: 3000)"
    )
    run_parser.add_argument(
        "--base-url",
        default="http://localhost:3000",
        help="Base URL for SSE server (default: http://localhost:3000)"
    )
    run_parser.add_argument(
        "--sse-path",
        default="/sse",
        help="Path for SSE endpoint (default: /sse)"
    )
    run_parser.add_argument(
        "--message-path",
        default="/message",
        help="Path for message endpoint (default: /message)"
    )
    
    return parser.parse_args(args)

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    if args.command == "add":
        add_command(args)
    elif args.command == "remove":
        remove_command(args)
    elif args.command == "ps":
        ps_command(args)
    elif args.command == "status":
        status_command(args)
    elif args.command == "run":
        run_command(args)
    else:
        show_help_text(
            "mcphub",
            "MCPHub CLI tool for managing MCP server configurations",
            [
                "mcphub add https://github.com/username/repo",
                "mcphub ps",
                "mcphub run server-name",
                "mcphub status server-name"
            ]
        )
        sys.exit(1)

if __name__ == "__main__":
    main()