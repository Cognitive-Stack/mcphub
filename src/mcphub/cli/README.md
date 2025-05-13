# MCPHub CLI

The MCPHub CLI is a command-line interface tool for managing Model Context Protocol (MCP) server configurations. It provides a user-friendly way to add, remove, monitor, and run MCP servers.

## Installation

The CLI is included with the MCPHub package. Install it using pip:

```bash
pip install mcphub
```

## Available Commands

### 1. Add a Server (`add`)
Add a new MCP server from a GitHub repository to your local configuration.

```bash
mcphub add <repo_url> [mcp_name]
```

Options:
- `repo_url`: GitHub repository URL of the MCP server
- `mcp_name` (optional): Custom name for the MCP server
- `-n, --non-interactive`: Skip environment variable prompts

Example:
```bash
mcphub add https://github.com/username/repo my-server
```

### 2. Remove a Server (`remove`)
Remove an MCP server configuration from your local config.

```bash
mcphub remove <mcp_name>
```

Example:
```bash
mcphub remove my-server
```

### 3. List Configured Servers (`list` or `ls`)
List all MCP servers configured in your local configuration file.

```bash
mcphub list
# or
mcphub ls
```

Shows:
- Server name
- Command
- Package name
- Repository URL
- Number of environment variables

This command provides a quick overview of your configured servers without process details.

### 4. List Running Processes (`ps`)
List all configured MCP servers with detailed process information, plus any detected MCP processes that aren't configured.

```bash
mcphub ps
```

Shows:
- Server name
- Status (running/not running/zombie)
- PID
- Ports
- Command
- Creation time
- Uptime
- Any detected MCP processes not in configuration

This command helps you track all MCP related processes running on your system, even those not configured in MCPHub.

### 5. Check Server Status (`status`)
Show detailed status information for a specific MCP server.

```bash
mcphub status <mcp_name>
```

Example:
```bash
mcphub status my-server
```

### 6. Run a Server (`run`)
Run a configured MCP server with optional SSE support.

```bash
mcphub run <mcp_name> [options]
```

Options:
- `--sse`: Enable Server-Sent Events support
- `--port`: Port for SSE server (default: 3000)
- `--base-url`: Base URL for SSE server (default: http://localhost:3000)
- `--sse-path`: Path for SSE endpoint (default: /sse)
- `--message-path`: Path for message endpoint (default: /message)

Example:
```bash
mcphub run my-server --sse --port 3001
```

## Configuration File

MCPHub uses a global configuration file located at `~/.mcphub/.mcphub.json`. This file stores MCP server configurations, including commands, arguments, and environment variables.

Example configuration:
```json
{
  "mcpServers": {
    "sequential-thinking-mcp": {
      "package_name": "smithery-ai/server-sequential-thinking",
      "command": "npx",
      "args": [
        "-y",
        "@smithery/cli@latest",
        "run",
        "@smithery-ai/server-sequential-thinking"
      ]
    },
    "azure-storage-mcp": {
      "package_name": "mashriram/azure_mcp_server",
      "repo_url": "https://github.com/mashriram/azure_mcp_server",
      "command": "uv",
      "args": ["run", "mcp_server_azure_cmd"],
      "setup_script": "uv pip install -e .",
      "env": {
        "AZURE_STORAGE_CONNECTION_STRING": "${AZURE_STORAGE_CONNECTION_STRING}",
        "AZURE_STORAGE_CONTAINER_NAME": "${AZURE_STORAGE_CONTAINER_NAME}",
        "AZURE_STORAGE_BLOB_NAME": "${AZURE_STORAGE_BLOB_NAME}"
      }
    }
  }
}
```

## CLI Code Architecture

The MCPHub CLI is structured with a clean, modular design following professional Python coding patterns:

### Module Structure

- **commands.py**: Command-line arguments parsing and entry points
- **handlers.py**: Implementation of command handlers
- **process_manager.py**: Process management and monitoring
- **utils.py**: Utility functions for configuration, UI, and logging
- **__init__.py**: Package initialization

### Component Responsibilities

1. **Command Parser**
   - Parses command-line arguments
   - Routes to appropriate handlers

2. **Command Handlers**
   - Implements business logic for each command
   - Manages command-specific functionality

3. **Process Manager**
   - Tracks and manages MCP server processes
   - Handles process lifecycle (start, stop, monitor)
   - Manages port allocation and conflict resolution
   - Detects and monitors all MCP-related processes

4. **Utilities**
   - Configuration management
   - Environment variable handling
   - UI components for rich terminal output
   - Logging functionality

### Design Patterns

The CLI implementation follows these design principles:

- **Separation of concerns**: UI, business logic, and data management are separated
- **Single responsibility**: Each module has a clear, focused purpose
- **Type hinting**: Comprehensive type annotations for better IDE support and code quality
- **Error handling**: Consistent error management and user feedback
- **Resource management**: Clean handling of processes and files

## Development

To extend the CLI with new commands:

1. Add new argument parser in `commands.py`
2. Implement handler function in `handlers.py`
3. Connect them in the `main()` function

For process management features:
- Extend the `ProcessManager` class in `process_manager.py`

For UI and utility functions:
- Add to the appropriate section in `utils.py`

## Environment Variables

MCPHub CLI can detect and prompt for environment variables required by MCP servers. Variables specified in the format `${VAR_NAME}` in the configuration file will be detected and processed.

## Features

- Rich terminal interface with progress bars and colored output
- Interactive prompts for configuration
- Process management and monitoring
- Server-Sent Events (SSE) support
- Environment variable management
- GitHub repository integration
- Detailed status reporting
- Process monitoring with detection of unconfigured MCP servers

## Error Handling

The CLI provides clear error messages and helpful suggestions when something goes wrong. Common error scenarios include:

- Invalid GitHub repository URLs
- Missing environment variables
- Server configuration issues
- Process management errors

## Contributing

To contribute to the CLI development:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 