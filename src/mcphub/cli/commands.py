"""CLI commands for mcphub."""
import argparse
import sys
from typing import Optional, List

from .utils import (
    show_help_text
)
from .handlers import (
    handle_add, 
    handle_remove, 
    handle_ps, 
    handle_status,
    handle_run,
    handle_list,
    handle_kill
)


def parse_args(args=None):
    """Parse command line arguments.
    
    Args:
        args: Command line arguments to parse
        
    Returns:
        Parsed arguments
    """
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
    
    # List command (with 'ls' alias)
    list_parser = subparsers.add_parser(
        "list",
        aliases=["ls"],
        help="List all configured MCP servers in your local config",
        description="List all MCP servers configured in your local configuration."
    )
    
    # PS command
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
    
    # Kill command
    kill_parser = subparsers.add_parser(
        "kill",
        help="Kill a running MCP server process",
        description="Kill a running MCP server process by its PID."
    )
    kill_parser.add_argument(
        "pid",
        type=int,
        help="Process ID of the MCP server to kill"
    )
    kill_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force kill the process immediately (SIGKILL)"
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
        handle_add(args.repo_url, args.mcp_name, args.non_interactive)
    elif args.command == "remove":
        handle_remove(args.mcp_name)
    elif args.command in ["list", "ls"]:
        handle_list()
    elif args.command == "ps":
        handle_ps()
    elif args.command == "status":
        handle_status(args.mcp_name)
    elif args.command == "kill":
        handle_kill(args.pid, args.force)
    elif args.command == "run":
        handle_run(
            args.mcp_name, 
            args.sse, 
            args.port, 
            args.base_url, 
            args.sse_path, 
            args.message_path
        )
    else:
        show_help_text(
            "mcphub",
            "MCPHub CLI tool for managing MCP server configurations",
            [
                "mcphub add https://github.com/username/repo",
                "mcphub list",
                "mcphub ps",
                "mcphub run server-name",
                "mcphub status server-name",
                "mcphub kill <pid>"
            ]
        )
        sys.exit(1)


if __name__ == "__main__":
    main()