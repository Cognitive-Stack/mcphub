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

### 3. List Servers (`ps`)
List all configured MCP servers with detailed process information.

```bash
mcphub ps
```

Shows:
- Server name
- Status (running/not running)
- Ports
- Command
- Creation time
- Uptime

### 4. Check Server Status (`status`)
Show detailed status information for a specific MCP server.

```bash
mcphub status <mcp_name>
```

Example:
```bash
mcphub status my-server
```

### 5. Run a Server (`run`)
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

The CLI uses a `.mcphub.json` configuration file in your project directory. Here's an example structure:

```json
{
  "mcpServers": {
    "server-name": {
      "package_name": "package-name",
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      },
      "description": "Server description",
      "tags": ["tag1", "tag2"],
      "last_run": "timestamp"
    }
  }
}
```

## Features

- Rich terminal interface with progress bars and colored output
- Interactive prompts for configuration
- Process management and monitoring
- Server-Sent Events (SSE) support
- Environment variable management
- GitHub repository integration
- Detailed status reporting
- Process monitoring and management

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