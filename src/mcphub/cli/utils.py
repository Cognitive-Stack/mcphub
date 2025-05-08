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
import logging

# Initialize rich console with custom theme
console = Console(theme=Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green",
    "command": "blue",
    "step": "magenta",
    "input": "bright_blue",
}))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)

logger = logging.getLogger("mcphub")

def show_steps(steps: List[str], title: str = "Progress"):
    """Show a list of steps with checkmarks."""
    table = Table(show_header=False, box=None)
    table.add_column("Status", style="green")
    table.add_column("Step", style="step")
    
    for step in steps:
        table.add_row("✓", step)
    
    console.print(Panel(table, title=title, border_style="blue"))

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
    """Load the config file if it exists, otherwise return an empty config dict."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> None:
    """Save the config to the .mcphub.json file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def load_preconfigured_servers() -> Dict[str, Any]:
    """Load the preconfigured servers from mcphub_preconfigured_servers.json."""
    preconfigured_path = Path(__file__).parent.parent / "mcphub_preconfigured_servers.json"
    if preconfigured_path.exists():
        with open(preconfigured_path, "r") as f:
            return json.load(f)
    return {"mcpServers": {}}

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

def prompt_env_vars(env_vars: List[str], existing_values: Dict[str, str] = None) -> Dict[str, str]:
    """Prompt user for environment variable values.
    
    Args:
        env_vars: List of environment variable names to prompt for
        existing_values: Optional dictionary of existing values
        
    Returns:
        Dictionary mapping environment variable names to values
    """
    values = existing_values or {}
    
    console.print("\n[info]Environment Variables Setup[/]")
    console.print("[info]Please provide values for the following environment variables:[/]")
    
    for var in env_vars:
        # Skip if already set in environment
        if os.getenv(var):
            console.print(f"[success]✓ {var} is already set in your environment[/]")
            continue
            
        # Show existing value if any
        current_value = values.get(var, "")
        if current_value:
            console.print(f"[info]Current value for {var}: {current_value}[/]")
            
        # Prompt for new value
        value = Prompt.ask(
            f"[input]Enter value for {var}[/]",
            default=current_value,
            show_default=True
        )
        
        if value:
            values[var] = value
            
    return values

def validate_env_vars(env_vars: Dict[str, str]) -> bool:
    """Validate environment variable values.
    
    Args:
        env_vars: Dictionary of environment variable values
        
    Returns:
        True if all values are valid, False otherwise
    """
    for var, value in env_vars.items():
        if not value:
            log_warning(f"Environment variable {var} is empty")
            if not Confirm.ask(f"Do you want to continue without setting {var}?"):
                return False
    return True

def save_env_vars_to_config(config: Dict[str, Any], server_name: str, env_vars: Dict[str, str]) -> None:
    """Save environment variables to the server configuration.
    
    Args:
        config: Configuration dictionary
        server_name: Name of the server
        env_vars: Dictionary of environment variable values
    """
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    if server_name not in config["mcpServers"]:
        config["mcpServers"][server_name] = {}
    if "env" not in config["mcpServers"][server_name]:
        config["mcpServers"][server_name]["env"] = {}
        
    config["mcpServers"][server_name]["env"].update(env_vars)
    save_config(config)

def process_env_vars(server_config: Dict[str, Any], env_values: Dict[str, str]) -> Dict[str, Any]:
    """Process environment variables in a server configuration.
    
    Args:
        server_config: Server configuration dict
        env_values: Dictionary of environment variable values
        
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
            
            # Use provided value or environment variable
            if env_var in env_values:
                new_env[key] = env_values[env_var]
            else:
                # Keep the template if not provided
                new_env[key] = value
        else:
            # Keep non-template values as is
            new_env[key] = value
    
    # Update the env section
    config["env"] = new_env
    return config

def add_server_config(name: str, interactive: bool = True) -> Tuple[bool, Optional[List[str]]]:
    """Add a preconfigured server to the local config.
    
    Args:
        name: Name of the preconfigured server to add
        interactive: Whether to prompt for environment variables
        
    Returns:
        Tuple of (success, missing_env_vars):
          - success: True if the server was added, False if it wasn't found
          - missing_env_vars: List of environment variables that weren't set (None if no env vars needed)
    """
    preconfigured = load_preconfigured_servers()
    if name not in preconfigured.get("mcpServers", {}):
        return False, None
    
    # Get the server config
    server_config = preconfigured["mcpServers"][name]
    
    # Detect environment variables
    env_vars = detect_env_vars(server_config)
    missing_env_vars = []
    
    # Process environment variables if needed
    if env_vars and interactive:
        env_values = prompt_env_vars(env_vars)
        server_config = process_env_vars(server_config, env_values)
        
        # Check for missing environment variables
        for var in env_vars:
            if var not in env_values and var not in os.environ:
                missing_env_vars.append(var)
    
    # Save to config
    config = load_config()
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    config["mcpServers"][name] = server_config
    save_config(config)
    
    return True, missing_env_vars if missing_env_vars else None

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

def list_available_servers() -> Dict[str, Any]:
    """List all available preconfigured servers."""
    preconfigured = load_preconfigured_servers()
    return preconfigured.get("mcpServers", {})

def list_configured_servers() -> Dict[str, Any]:
    """List all servers in the local config."""
    config = load_config()
    return config.get("mcpServers", {})