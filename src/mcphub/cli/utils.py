"""Utility functions for the mcphub CLI."""
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from rich.console import Console
from rich.theme import Theme
from rich.logging import RichHandler
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.live import Live
from rich.text import Text
import time
import logging
import sys
import subprocess
import psutil
import socket
from datetime import datetime

# Initialize rich console with custom theme
console = Console(theme=Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green",
    "command": "blue",
    "step": "magenta",
    "input": "bright_blue",
    "help": "dim",
    "status": "bright_green",
    "code": "bright_black",
    "check": "green",
    "pending": "yellow",
    "current": "cyan",
}))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)

logger = logging.getLogger("mcphub")

def show_animated_checklist(steps: List[str], title: str = "Progress"):
    """Show an animated checklist of steps."""
    def generate_checklist(completed_steps: int) -> Table:
        table = Table(show_header=False, box=None)
        table.add_column("Status", style="check", width=3)
        table.add_column("Step", style="step")
        
        for i, step in enumerate(steps):
            if i < completed_steps:
                status = "✓"
                style = "check"
            elif i == completed_steps:
                status = "⟳"
                style = "current"
            else:
                status = "○"
                style = "pending"
            table.add_row(status, step)
        
        return Panel(table, title=title, border_style="blue")
    
    with Live(generate_checklist(0), refresh_per_second=4) as live:
        for i in range(len(steps) + 1):
            live.update(generate_checklist(i))
            if i < len(steps):
                time.sleep(0.5)  # Simulate work being done

def show_progress(steps: List[str], title: str = "Progress"):
    """Show a progress bar with steps."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        tasks = {}
        for step in steps:
            task = progress.add_task(f"[cyan]{step}", total=100)
            tasks[step] = task
            progress.update(task, completed=100)
            progress.refresh()

def show_steps(steps: List[str], title: str = "Progress"):
    """Show a list of steps with checkmarks."""
    table = Table(show_header=False, box=None)
    table.add_column("Status", style="green")
    table.add_column("Step", style="step")
    
    for step in steps:
        table.add_row("✓", step)
    
    console.print(Panel(table, title=title, border_style="blue"))

def show_help_text(command: str, description: str, examples: List[str] = None):
    """Show help text for a command."""
    console.print(f"\n[help]Command: {command}[/]")
    console.print(f"[help]Description: {description}[/]")
    
    if examples:
        console.print("\n[help]Examples:[/]")
        for example in examples:
            console.print(f"[code]$ {example}[/]")

def show_error(message: str, error: Exception = None, help_text: str = None):
    """Show an error message with optional exception details and help text."""
    console.print(f"\n[error]Error: {message}[/]")
    if error:
        console.print(f"[error]Details: {str(error)}[/]")
    if help_text:
        console.print(f"\n[help]{help_text}[/]")

def show_warning(message: str, help_text: str = None):
    """Show a warning message with optional help text."""
    console.print(f"\n[warning]Warning: {message}[/]")
    if help_text:
        console.print(f"\n[help]{help_text}[/]")

def show_success(message: str, details: str = None):
    """Show a success message with optional details."""
    console.print(f"\n[success]✓ {message}[/]")
    if details:
        console.print(f"[info]{details}[/]")

def show_status(server_name: str, status: str, details: Dict[str, Any] = None):
    """Show server status information."""
    table = Table(title=f"Server Status: {server_name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="status")
    
    table.add_row("Status", status)
    if details:
        for key, value in details.items():
            table.add_row(key, str(value))
    
    console.print(table)

def show_code_block(code: str, language: str = "bash"):
    """Show a code block with syntax highlighting."""
    syntax = Syntax(code, language, theme="monokai")
    console.print(syntax)

def log_error(message: str, error: Exception = None):
    """Log an error message with optional exception details."""
    if error:
        logger.error(f"{message}: {str(error)}", exc_info=error)
    else:
        logger.error(message)

def log_warning(message: str):
    """Log a warning message."""
    logger.warning(message)

def log_info(message: str):
    """Log an info message."""
    logger.info(message)

def log_success(message: str):
    """Log a success message."""
    console.print(f"[success]✓ {message}[/]")

def log_step(message: str):
    """Log a step message."""
    console.print(f"[step]→ {message}[/]")

DEFAULT_CONFIG = {
    "mcpServers": {}
}

def get_config_path() -> Path:
    """Get the path to the .mcphub.json config file."""
    return Path.cwd() / ".mcphub.json"

def load_config() -> Dict[str, Any]:
    """Load the config file if it exists, otherwise create a new one."""
    config_path = get_config_path()
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
    with open(config_path, "r") as f:
        return json.load(f)

def save_config(config: Dict[str, Any]) -> None:
    """Save the config to the .mcphub.json file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def detect_env_vars(server_config: Dict[str, Any]) -> List[str]:
    """Detect environment variables in a server configuration.
    
    Args:
        server_config: Server configuration dict
        
    Returns:
        List of environment variable names found in the configuration
    """
    env_vars = []
    
    # Check if the server has env section
    if "env" in server_config and isinstance(server_config["env"], dict):
        for key, value in server_config["env"].items():
            # Check if value is a template like ${ENV_VAR}
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]  # Extract ENV_VAR from ${ENV_VAR}
                env_vars.append(env_var)
    
    return env_vars

def check_env_var(var: str) -> Optional[str]:
    """Check if an environment variable exists and return its value.
    
    Args:
        var: Environment variable name
        
    Returns:
        The value of the environment variable if it exists, None otherwise
    """
    try:
        # Use subprocess to run echo command and capture output
        result = subprocess.run(
            f"echo ${var}",
            shell=True,
            capture_output=True,
            text=True
        )
        value = result.stdout.strip()
        # If echo returns empty or the variable name, the variable doesn't exist
        if not value or value == f"${var}":
            return None
        return value
    except Exception:
        return None

def prompt_env_vars(env_vars: List[str]) -> Dict[str, str]:
    """Check and prompt for environment variables.
    
    Args:
        env_vars: List of environment variable names to check
        
    Returns:
        Dictionary of environment variable values that were found
    """
    found_vars = {}
    missing_vars = []
    
    console.print("\n[info]Checking Environment Variables[/]")
    
    for var in env_vars:
        # Check if variable exists
        value = check_env_var(var)
        if value:
            console.print(f"[success]✓ Found {var} in environment[/]")
            found_vars[var] = value
        else:
            console.print(f"[warning]✗ {var} not found in environment[/]")
            missing_vars.append(var)
    
    # If there are missing variables, prompt user to set them
    if missing_vars:
        console.print("\n[info]Please set the following environment variables:[/]")
        for var in missing_vars:
            console.print(f"\n[code]export {var}=<value>[/]")
            console.print(f"[code]echo ${var}[/]")
            
            # Prompt for confirmation
            if not Confirm.ask(f"Have you set {var}?"):
                show_warning(
                    f"Environment variable {var} is required",
                    "Please set it using export before continuing"
                )
                sys.exit(1)
            
            # Check again after user confirmation
            value = check_env_var(var)
            if value:
                console.print(f"[success]✓ Found {var} in environment[/]")
                found_vars[var] = value
            else:
                show_error(
                    f"Environment variable {var} is still not set",
                    "Please make sure to set it correctly"
                )
                sys.exit(1)
    
    return found_vars

def process_env_vars(server_config: Dict[str, Any]) -> Dict[str, Any]:
    """Process environment variables in a server configuration.
    
    Args:
        server_config: Server configuration dict
        
    Returns:
        Updated server configuration with processed environment variables
    """
    # Create a copy of the config to avoid modifying the original
    config = server_config.copy()
    
    # If there's no env section, nothing to do
    if "env" not in config or not isinstance(config["env"], dict):
        return config
    
    # New env dict to store processed values
    new_env = {}
    
    for key, value in config["env"].items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Extract ENV_VAR from ${ENV_VAR}
            
            # Check if variable exists in environment
            env_value = check_env_var(env_var)
            if env_value:
                new_env[key] = env_value
            else:
                show_error(
                    f"Required environment variable {env_var} is not set",
                    help_text=f"Please set it using: export {env_var}=<value>"
                )
                sys.exit(1)
        else:
            # Keep non-template values as is
            new_env[key] = value
    
    # Update the env section
    config["env"] = new_env
    return config

def remove_server_config(name: str) -> bool:
    """Remove a server config from the local .mcphub.json file.
    
    Args:
        name: Name of the server to remove
        
    Returns:
        bool: True if the server was removed, False if it wasn't in the config
    """
    config = load_config()
    if name in config.get("mcpServers", {}):
        del config["mcpServers"][name]
        save_config(config)
        return True
    return False

def list_configured_servers() -> Dict[str, Any]:
    """List all servers in the local config."""
    config = load_config()
    return config.get("mcpServers", {})

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use.
    
    Args:
        port: Port number to check
        
    Returns:
        bool: True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_process_uptime(pid: int) -> Optional[str]:
    """Get the uptime of a process.
    
    Args:
        pid: Process ID
        
    Returns:
        str: Uptime in human readable format, or None if process not found
    """
    try:
        process = psutil.Process(pid)
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time
        
        # Format uptime
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def get_server_status(server_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get the status of a server including process details.
    
    Args:
        server_config: Server configuration dict
        
    Returns:
        Dict with status information:
        {
            "status": "Running" or "Not Running",
            "pid": process ID or None,
            "name": process name or None,
            "command": full command or None,
            "created": creation time or None,
            "ports": list of ports or None,
            "uptime": uptime string or None
        }
    """
    status = {
        "status": "Not Running",
        "pid": None,
        "name": None,
        "command": None,
        "created": None,
        "ports": None,
        "uptime": None
    }
    
    # Get expected command and package name from config
    expected_command = server_config.get("command", "")
    expected_package = server_config.get("package_name", "")
    expected_port = server_config.get("port", 3000)
    
    # First check for Docker containers
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}} {{.Ports}}"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            if line.strip():
                name, ports = line.split(" ", 1)
                # Check if this container matches our server
                if expected_command and expected_command in name:
                    # Get container details
                    inspect = subprocess.run(
                        ["docker", "inspect", name],
                        capture_output=True,
                        text=True
                    )
                    if inspect.returncode == 0:
                        status["status"] = "Running"
                        status["name"] = f"docker:{name}"
                        status["command"] = expected_command
                        # Extract ports from docker ps output
                        port_list = []
                        for port in ports.split(", "):
                            if "->" in port:
                                host_port = port.split("->")[0].split(":")[-1]
                                port_list.append(int(host_port))
                        status["ports"] = port_list
                        return status
    except Exception:
        pass
    
    # If no Docker match, check regular processes
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = " ".join(proc.cmdline())
            
            # Check if this process matches our server
            is_match = False
            
            # Check by command (exact match or contains)
            if expected_command:
                if expected_command in cmdline or cmdline in expected_command:
                    is_match = True
            
            # Check by package name (for npm/npx processes)
            if not is_match and expected_package:
                # Check for npx or npm running the package
                if f"npx {expected_package}" in cmdline or f"npm {expected_package}" in cmdline:
                    is_match = True
                # Check for direct package execution
                elif expected_package in cmdline:
                    is_match = True
            
            # Check by port
            if not is_match:
                try:
                    for conn in proc.connections():
                        if conn.laddr.port == expected_port:
                            is_match = True
                            break
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            
            if is_match:
                status["status"] = "Running"
                status["pid"] = proc.pid
                status["name"] = proc.name()
                status["command"] = cmdline
                status["created"] = datetime.fromtimestamp(proc.create_time()).strftime("%Y-%m-%d %H:%M:%S")
                try:
                    status["ports"] = [conn.laddr.port for conn in proc.connections()]
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    status["ports"] = [expected_port]
                status["uptime"] = get_process_uptime(proc.pid)
                break
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return status