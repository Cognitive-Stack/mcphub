"""CLI commands for mcphub."""
import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from .utils import (
    load_config,
    save_config,
    DEFAULT_CONFIG,
    get_config_path,
    add_server_config,
    remove_server_config,
    list_available_servers,
    list_configured_servers
)

def init_command(args):
    """Initialize a new .mcphub.json configuration file in the current directory."""
    config_path = get_config_path()
    if config_path.exists():
        print(f"Configuration file already exists at: {config_path}")
        return

    save_config(DEFAULT_CONFIG)
    print(f"Created new configuration file at: {config_path}")

def add_command(args):
    """Add a preconfigured MCP server to the local config."""
    server_name = args.mcp_name
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False
    
    success, missing_env_vars = add_server_config(server_name, interactive=not non_interactive)
    
    if not success:
        print(f"Error: MCP server '{server_name}' not found in preconfigured servers")
        # Show available options
        print("\nAvailable preconfigured servers:")
        available_servers = list_available_servers()
        for name in available_servers:
            print(f"- {name}")
        sys.exit(1)
    
    print(f"Added configuration for '{server_name}' to .mcphub.json")
    
    # Notify about missing environment variables
    if missing_env_vars:
        print("\nWarning: The following environment variables are required but not set:")
        for var in missing_env_vars:
            print(f"- {var}")
        print("\nYou can either:")
        print("1. Set them in your environment before using this server")
        print("2. Run 'mcphub add-env' to add them to your configuration")
        print("3. Edit .mcphub.json manually to set the values")

def remove_command(args):
    """Remove an MCP server configuration from the local config."""
    server_name = args.mcp_name
    if remove_server_config(server_name):
        print(f"Removed configuration for '{server_name}' from .mcphub.json")
    else:
        print(f"Error: MCP server '{server_name}' not found in current configuration")
        # Show what's currently configured
        configured = list_configured_servers()
        if configured:
            print("\nCurrently configured servers:")
            for name in configured:
                print(f"- {name}")
        sys.exit(1)

def list_command(args):
    """List all configured and available MCP servers."""
    show_all = args.all if hasattr(args, 'all') else False
    
    configured = list_configured_servers()
    print("Configured MCP servers:")
    if configured:
        for name in configured:
            print(f"- {name}")
    else:
        print("  No servers configured in local .mcphub.json")
    
    if show_all:
        available = list_available_servers()
        print("\nAvailable preconfigured MCP servers:")
        if available:
            for name in available:
                print(f"- {name}")
        else:
            print("  No preconfigured servers available")

def run_command(args):
    """Run an MCP server with optional SSE support."""
    server_name = args.mcp_name
    config = load_config()
    
    if server_name not in config.get("mcpServers", {}):
        print(f"Error: MCP server '{server_name}' not found in configuration")
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
        print(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error running server: {e}")
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
        help="Add a preconfigured MCP server to your local config"
    )
    add_parser.add_argument(
        "mcp_name", 
        help="Name of the preconfigured MCP server to add"
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
    list_parser.add_argument(
        "-a", "--all", 
        action="store_true", 
        help="Show all available preconfigured servers"
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