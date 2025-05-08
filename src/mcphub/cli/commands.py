"""CLI commands for mcphub."""
import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
from urllib.parse import urlparse

from .utils import (
    load_config,
    save_config,
    DEFAULT_CONFIG,
    get_config_path,
    remove_server_config,
    list_configured_servers,
    console,
    log_error,
    log_warning,
    log_info,
    log_success,
    log_step,
    show_steps
)

def init_command(args):
    """Initialize a new .mcphub.json configuration file in the current directory."""
    steps = [
        "Checking for existing configuration",
        "Creating new configuration file",
        "Initializing default settings"
    ]
    show_steps(steps, "Initializing MCPHub")
    
    config_path = get_config_path()
    if config_path.exists():
        log_warning(f"Configuration file already exists at: {config_path}")
        return

    save_config(DEFAULT_CONFIG)
    log_success(f"Created new configuration file at: {config_path}")

def add_command(args):
    """Add an MCP server from a GitHub repository to the local config."""
    steps = [
        "Validating repository URL",
        "Fetching repository README",
        "Parsing MCP configuration",
        "Adding server configuration"
    ]
    show_steps(steps, "Adding MCP Server")
    
    repo_url = args.repo_url
    # Extract server name from repo URL if not provided
    if args.mcp_name:
        server_name = args.mcp_name
    else:
        # Extract username/repo from GitHub URL
        parsed_url = urlparse(repo_url)
        if parsed_url.netloc != "github.com":
            log_error("Only GitHub repositories are supported")
            sys.exit(1)
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) != 2:
            log_error("Invalid GitHub repository URL")
            sys.exit(1)
        server_name = "/".join(path_parts)
    
    try:
        # Step 1: Validating repository URL
        log_step("Validating repository URL...")
        # URL validation is already done above
        
        # Step 2: Fetching repository README
        log_step("Fetching repository README...")
        # Load config to get MCPServersParams instance
        config = load_config()
        config_path = get_config_path()
        
        # Step 3: Parsing MCP configuration
        log_step("Parsing MCP configuration...")
        from ..mcp_servers.params import MCPServersParams
        servers_params = MCPServersParams(str(config_path))
        
        # Step 4: Adding server configuration
        log_step("Adding server configuration...")
        servers_params.add_server_from_repo(server_name, repo_url)
        
        log_success(f"Successfully added configuration for '{server_name}' from {repo_url}")
        
        # Check required environment variables
        server_config = servers_params.retrieve_server_params(server_name)
        required_env_vars = [var for var in server_config.env if not os.getenv(var)]
        
        if required_env_vars:
            log_warning("\nThe following environment variables are required but not set:")
            for var in required_env_vars:
                console.print(f"[warning]- {var}[/]")
            console.print("\n[info]You can either:[/]")
            console.print("[info]1. Set them in your environment before using this server[/]")
            console.print("[info]2. Edit .mcphub.json manually to set the values[/]")
            
    except ValueError as e:
        log_error("Failed to add server", e)
        sys.exit(1)
    except Exception as e:
        log_error("Failed to add server", e)
        sys.exit(1)

def remove_command(args):
    """Remove an MCP server configuration from the local config."""
    steps = [
        "Checking server configuration",
        "Removing server settings",
        "Updating configuration file"
    ]
    show_steps(steps, "Removing MCP Server")
    
    server_name = args.mcp_name
    if remove_server_config(server_name):
        log_success(f"Removed configuration for '{server_name}' from .mcphub.json")
    else:
        log_error(f"MCP server '{server_name}' not found in current configuration")
        # Show what's currently configured
        configured = list_configured_servers()
        if configured:
            console.print("\n[info]Currently configured servers:[/]")
            for name in configured:
                console.print(f"[info]- {name}[/]")
        sys.exit(1)

def list_command(args):
    """List all configured MCP servers."""
    steps = [
        "Loading configuration",
        "Retrieving server list",
        "Displaying results"
    ]
    show_steps(steps, "Listing MCP Servers")
    
    configured = list_configured_servers()
    console.print("[info]Configured MCP servers:[/]")
    if configured:
        for name in configured:
            console.print(f"[info]- {name}[/]")
    else:
        console.print("[warning]  No servers configured in local .mcphub.json[/]")

def run_command(args):
    """Run an MCP server with optional SSE support."""
    steps = [
        "Loading server configuration",
        "Preparing command",
        "Starting server"
    ]
    show_steps(steps, "Running MCP Server")
    
    server_name = args.mcp_name
    config = load_config()
    
    if server_name not in config.get("mcpServers", {}):
        log_error(f"MCP server '{server_name}' not found in configuration")
        sys.exit(1)
    
    server_config = config["mcpServers"][server_name]
    
    # Build the command
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
    
    try:
        console.print(f"[command]Running command: {' '.join(cmd)}[/]")
        log_info("Server is running...")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        log_info("\nServer stopped")
    except Exception as e:
        log_error("Error running server", e)
        sys.exit(1)

def parse_args(args=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCPHub CLI tool for managing MCP server configurations"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Init command
    init_parser = subparsers.add_parser(
        "init", 
        help="Create a new .mcphub.json file in the current directory"
    )
    
    # Add command
    add_parser = subparsers.add_parser(
        "add", 
        help="Add an MCP server from a GitHub repository to your local config"
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
        help="Remove an MCP server from your local config"
    )
    remove_parser.add_argument(
        "mcp_name", 
        help="Name of the MCP server to remove"
    )
    
    # List command
    list_parser = subparsers.add_parser(
        "list", 
        help="List configured MCP servers"
    )
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run an MCP server with optional SSE support"
    )
    run_parser.add_argument(
        "mcp_name",
        help="Name of the MCP server to run"
    )
    run_parser.add_argument(
        "--sse",
        action="store_true",
        help="Enable SSE support using supergateway"
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    run_parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the server (default: http://localhost:8000)"
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
    
    if args.command == "init":
        init_command(args)
    elif args.command == "add":
        add_command(args)
    elif args.command == "remove":
        remove_command(args)
    elif args.command == "list":
        list_command(args)
    elif args.command == "run":
        run_command(args)
    else:
        # Show help if no command is provided
        parse_args(["-h"])

if __name__ == "__main__":
    main()