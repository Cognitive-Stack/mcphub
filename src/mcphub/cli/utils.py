"""Utility functions for the mcphub CLI."""
import json
import os
import re
import sys
import time
import logging
import subprocess
import psutil
import socket
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from rich.console import Console
from rich.theme import Theme
from rich.logging import RichHandler
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.text import Text

# ==========================================
# Console and Logging Setup
# ==========================================

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

# ==========================================
# Configuration Management
# ==========================================

DEFAULT_CONFIG: Dict[str, Any] = {
    "mcpServers": {}
}

def get_config_path() -> Path:
    """Get the path to the .mcphub.json config file.
    
    Returns:
        Path to the config file
    """
    config_dir = Path.home() / ".mcphub"
    config_dir.mkdir(exist_ok=True)
    return config_dir / ".mcphub.json"

def load_config() -> Dict[str, Any]:
    """Load the config file if it exists, otherwise create a new one.
    
    Returns:
        Config dictionary loaded from the config file
    """
    config_path = get_config_path()
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
    with open(config_path, "r") as f:
        return json.load(f)

def save_config(config: Dict[str, Any]) -> None:
    """Save the config to the .mcphub.json file.
    
    Args:
        config: Config dictionary to save
    """
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def list_configured_servers() -> Dict[str, Any]:
    """List all servers in the local config.
    
    Returns:
        Dictionary of server configurations from the local config
    """
    config = load_config()
    return config.get("mcpServers", {})

def remove_server_config(name: str) -> bool:
    """Remove a server config from the local .mcphub.json file.
    
    Args:
        name: Name of the server to remove
        
    Returns:
        True if the server was removed, False if it wasn't in the config
    """
    config = load_config()
    if name in config.get("mcpServers", {}):
        del config["mcpServers"][name]
        save_config(config)
        return True
    return False

# ==========================================
# Environment Variable Utilities
# ==========================================

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

# ==========================================
# Network Utilities
# ==========================================

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use.
    
    Args:
        port: Port number to check
        
    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_process_uptime(pid: int) -> Optional[str]:
    """Get the uptime of a process.
    
    Args:
        pid: Process ID
        
    Returns:
        Uptime as string (formatted as "X days, HH:MM:SS") or None if process doesn't exist
    """
    try:
        process = psutil.Process(pid)
        create_time = datetime.fromtimestamp(process.create_time())
        now = datetime.now()
        uptime = now - create_time
        
        # Format as days, hours, minutes, seconds
        days = uptime.days
        seconds = uptime.seconds
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days} days, {hours:02}:{minutes:02}:{seconds:02}"
        else:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def get_server_status(server_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get the status of a server.
    
    Args:
        server_config: Server configuration dict
        
    Returns:
        Dictionary with server status information
    """
    # TODO: Implement actual status check
    return {
        "status": "Not Running",
        "ports": [],
        "uptime": "N/A",
        "pid": None
    }

# ==========================================
# UI Components
# ==========================================

def show_animated_checklist(steps: List[str], title: str = "Progress") -> None:
    """Show an animated checklist of steps.
    
    Args:
        steps: List of step descriptions
        title: Title of the checklist panel
    """
    def generate_checklist(completed_steps: int) -> Panel:
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

def show_progress(steps: List[str], title: str = "Progress") -> None:
    """Show a progress bar with steps.
    
    Args:
        steps: List of step descriptions
        title: Title of the progress panel
    """
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

def show_steps(steps: List[str], title: str = "Progress") -> None:
    """Show a list of steps with checkmarks.
    
    Args:
        steps: List of step descriptions
        title: Title of the steps panel
    """
    table = Table(show_header=False, box=None)
    table.add_column("Status", style="green")
    table.add_column("Step", style="step")
    
    for step in steps:
        table.add_row("✓", step)
    
    console.print(Panel(table, title=title, border_style="blue"))

def show_help_text(command: str, description: str, examples: List[str] = None) -> None:
    """Show help text for a command.
    
    Args:
        command: Command name
        description: Command description
        examples: List of example commands
    """
    console.print(f"\n[help]Command: {command}[/]")
    console.print(f"[help]Description: {description}[/]")
    
    if examples:
        console.print("\n[help]Examples:[/]")
        for example in examples:
            console.print(f"[code]$ {example}[/]")

def show_error(message: str, error: Exception = None, help_text: str = None) -> None:
    """Show an error message with optional exception details and help text.
    
    Args:
        message: Error message
        error: Exception object
        help_text: Additional help text
    """
    console.print(f"\n[error]Error: {message}[/]")
    if error:
        console.print(f"[error]Details: {str(error)}[/]")
    if help_text:
        console.print(f"\n[help]{help_text}[/]")

def show_warning(message: str, help_text: str = None) -> None:
    """Show a warning message with optional help text.
    
    Args:
        message: Warning message
        help_text: Additional help text
    """
    console.print(f"\n[warning]Warning: {message}[/]")
    if help_text:
        console.print(f"\n[help]{help_text}[/]")

def show_success(message: str, details: str = None) -> None:
    """Show a success message with optional details.
    
    Args:
        message: Success message
        details: Additional details
    """
    console.print(f"\n[success]✓ {message}[/]")
    if details:
        console.print(f"[info]{details}[/]")

def show_status(server_name: str, status: str, details: Dict[str, Any] = None) -> None:
    """Show server status information.
    
    Args:
        server_name: Name of the server
        status: Status of the server
        details: Dictionary of additional details
    """
    table = Table(title=f"Server Status: {server_name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="status")
    
    table.add_row("Status", status)
    if details:
        for key, value in details.items():
            table.add_row(key, str(value))
    
    console.print(table)

def show_code_block(code: str, language: str = "bash") -> None:
    """Show a code block with syntax highlighting.
    
    Args:
        code: Code to display
        language: Language for syntax highlighting
    """
    syntax = Syntax(code, language, theme="monokai")
    console.print(syntax)

# ==========================================
# Logging Utilities
# ==========================================

def log_error(message: str, error: Exception = None) -> None:
    """Log an error message with optional exception details.
    
    Args:
        message: Error message
        error: Exception object
    """
    if error:
        logger.error(f"{message}: {str(error)}", exc_info=error)
    else:
        logger.error(message)

def log_warning(message: str) -> None:
    """Log a warning message.
    
    Args:
        message: Warning message
    """
    logger.warning(message)

def log_info(message: str) -> None:
    """Log an info message.
    
    Args:
        message: Info message
    """
    logger.info(message)

def log_success(message: str) -> None:
    """Log a success message.
    
    Args:
        message: Success message
    """
    console.print(f"[success]✓ {message}[/]")

def log_step(message: str) -> None:
    """Log a step message.
    
    Args:
        message: Step message
    """
    console.print(f"[step]→ {message}[/]")