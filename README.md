# MCPHub

MCPHub is an embeddable Model Context Protocol (MCP) solution for AI services. It enables seamless integration of MCP servers into any AI framework, allowing developers to easily configure, set up, and manage MCP servers within their applications. Whether you're using OpenAI Agents, LangChain, or Autogen, MCPHub provides a unified way to connect your AI services with MCP tools and resources.

## Quick Start

### Prerequisites

Ensure you have the following tools installed:
```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install git (for repository cloning)
sudo apt-get install git  # Ubuntu/Debian
brew install git         # macOS

# Install npx (comes with Node.js)
npm install -g npx

# Install MCPHub
pip install mcphub
```

### Configuration

Create a `.mcphub.json` file in your project root:

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
        }
    }
}
```

### Usage with OpenAI Agents

```python
import asyncio
import json
from agents import Agent, Runner
from mcphub import MCPHub

async def main():
    """
    Example of using MCPHub to integrate MCP servers with OpenAI Agents.
    
    This example demonstrates:
    1. Initializing MCPHub
    2. Fetching and using an MCP server
    3. Listing available tools
    4. Creating and running an agent with MCP tools
    """
    
    # Step 1: Initialize MCPHub
    # MCPHub will automatically:
    # - Find .mcphub.json in your project
    # - Load server configurations
    # - Set up servers (clone repos, run setup scripts if needed)
    hub = MCPHub()
    
    # Step 2: Create an MCP server instance using async context manager
    # Parameters:
    # - mcp_name: The name of the server from your .mcphub.json
    # - cache_tools_list: Cache the tools list for better performance
    async with hub.fetch_openai_mcp_server(
        mcp_name="sequential-thinking-mcp",
        cache_tools_list=True
    ) as server:
        # Step 3: List available tools from the MCP server
        # This shows what capabilities are available to your agent
        tools = await server.list_tools()
        
        # Pretty print the tools for better readability
        tools_dict = [
            dict(tool) if hasattr(tool, "__dict__") else tool for tool in tools
        ]
        print("Available MCP Tools:")
        print(json.dumps(tools_dict, indent=2))

        # Step 4: Create an OpenAI Agent with MCP server
        # The agent can now use all tools provided by the MCP server
        agent = Agent(
            name="Assistant",
            instructions="Use the available tools to accomplish the given task",
            mcp_servers=[server]  # Provide the MCP server to the agent
        )
        
        # Step 5: Run your agent with a complex task
        # The agent will automatically have access to all MCP tools
        complex_task = """Please help me analyze the following complex problem: 
                      We need to design a new feature for our product that balances user privacy 
                      with data collection for improving the service. Consider the ethical implications, 
                      technical feasibility, and business impact. Break down your thinking process 
                      step by step, and provide a detailed recommendation with clear justification 
                      for each decision point."""
        
        # Execute the task and get the result
        result = await Runner.run(agent, complex_task)
        print("\nAgent Response:")
        print(result)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
```

## Features and Guidelines

### Server Configuration

- **JSON-based Configuration**: Simple `.mcphub.json` configuration file
- **Environment Variable Support**: Use environment variables in configuration
- **Predefined Servers**: Access to a growing list of pre-configured MCP servers
- **Custom Server Support**: Easy integration of custom MCP servers

Configure your MCP servers in `.mcphub.json`:

```json
{
    "mcpServers": {
        // TypeScript-based MCP server using NPX
        "sequential-thinking-mcp": {
            "package_name": "smithery-ai/server-sequential-thinking",  // NPM package name
            "command": "npx",                                         // Command to run server
            "args": [                                                // Command arguments
                "-y",
                "@smithery/cli@latest",
                "run",
                "@smithery-ai/server-sequential-thinking"
            ]
        },
        // Python-based MCP server from GitHub
        "azure-storage-mcp": {
            "package_name": "mashriram/azure_mcp_server",            // Package identifier
            "repo_url": "https://github.com/mashriram/azure_mcp_server", // GitHub repository
            "command": "uv",                                         // Python package manager
            "args": ["run", "mcp_server_azure_cmd"],                // Run command
            "setup_script": "uv pip install -e .",                  // Installation script
            "env": {                                                // Environment variables
                "AZURE_STORAGE_CONNECTION_STRING": "${AZURE_STORAGE_CONNECTION_STRING}",
                "AZURE_STORAGE_CONTAINER_NAME": "${AZURE_STORAGE_CONTAINER_NAME}",
                "AZURE_STORAGE_BLOB_NAME": "${AZURE_STORAGE_BLOB_NAME}"
            }
        }
    }
}
```

### MCP Server Installation and Management

- **Flexible Server Setup**: Supports both TypeScript and Python-based MCP servers
- **Multiple Installation Sources**:
  - NPM packages via `npx`
  - Python packages via GitHub repository URLs
  - Local development servers
- **Automatic Setup**: Handles repository cloning, dependency installation, and server initialization

### Transport Support

- **stdio Transport**: Run MCP servers as local subprocesses
- **Automatic Path Management**: Manages server paths and working directories
- **Environment Variable Handling**: Configurable environment variables per server

### Framework Integration

Provides adapters for popular AI frameworks:
- OpenAI Agents
- LangChain
- Autogen

```python
from mcphub import MCPHub

async def framework_examples():
    hub = MCPHub()
    
    # 1. OpenAI Agents Integration
    async with hub.fetch_openai_mcp_server(
        mcp_name="sequential-thinking-mcp",
        cache_tools_list=True
    ) as server:
        # Use server with OpenAI agents
        agent = Agent(
            name="Assistant",
            mcp_servers=[server]
        )
    
    # 2. LangChain Tools Integration
    langchain_tools = await hub.fetch_langchain_mcp_tools(
        mcp_name="sequential-thinking-mcp",
        cache_tools_list=True
    )
    # Use tools with LangChain
    
    # 3. Autogen Adapters Integration
    autogen_adapters = await hub.fetch_autogen_mcp_adapters(
        mcp_name="sequential-thinking-mcp"
    )
    # Use adapters with Autogen
```

### Tool Management

- **Tool Discovery**: Automatically list and manage available tools from MCP servers
- **Tool Caching**: Optional caching of tool lists for improved performance
- **Framework-specific Adapters**: Convert MCP tools to framework-specific formats

Discover and manage MCP server tools:

```python
from mcphub import MCPHub

async def tool_management():
    hub = MCPHub()
    
    # List all tools from a specific MCP server
    tools = await hub.list_tools(mcp_name="sequential-thinking-mcp")
    
    # Print tool information
    for tool in tools:
        print(f"Tool Name: {tool.name}")
        print(f"Description: {tool.description}")
        print(f"Parameters: {tool.parameters}")
        print("---")
    
    # Tools can be:
    # - Cached for better performance using cache_tools_list=True
    # - Converted to framework-specific formats automatically
    # - Used directly with AI frameworks through adapters
```

## MCPHub: High-Level Overview

MCPHub simplifies the integration of Model Context Protocol (MCP) servers into AI applications through four main components:

![MCPHub Architecture](./docs/simple_mcphub_work.png)

### Core Components

1. **Params Hub**
   - Manages configurations from `.mcphub.json`
   - Defines which MCP servers to use and how to set them up
   - Stores server parameters like commands, arguments, and environment variables

2. **MCP Servers Manager**
   - Handles server installation and setup
   - Supports two types of servers:
     * TypeScript-based servers (installed via npx)
     * Python-based servers (installed via uv from GitHub)
   - Manages server lifecycle and environment

3. **MCP Client**
   - Establishes communication with MCP servers
   - Uses stdio transport for server interaction
   - Handles two main operations:
     * `list_tools`: Discovers available server tools
     * `call_tool`: Executes server tools

4. **Framework Adapters**
   - Converts MCP tools to framework-specific formats
   - Supports multiple AI frameworks:
     * OpenAI Agents
     * LangChain
     * Autogen

### Workflow

1. **Configuration & Setup**
   - Params Hub reads configuration
   - Servers Manager sets up required servers
   - Servers start and become available

2. **Communication**
   - MCP Client connects to servers via stdio
   - Tools are discovered and made available
   - Requests and responses flow between client and server

3. **Integration**
   - Framework adapters convert MCP tools
   - AI applications use adapted tools through their preferred framework
   - Tools are executed through the established communication channel

This architecture provides a seamless way to integrate MCP capabilities into any AI application while maintaining clean separation of concerns and framework flexibility.

## Development

### Testing

Run the unit tests with pytest:

```bash
pytest tests/ -v
```

### CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment:

1. **Automated Testing**: Tests are run on Python 3.10, 3.11, and 3.12 for every push to main and release branches and for pull requests.

2. **Automatic Version Bumping**: When code is pushed to the `release` branch, the patch version is automatically incremented.

3. **PyPI Publishing**: When code is merged to the `release` branch and tests pass, the package is automatically built and published to PyPI.

#### Setting Up PyPI Deployment

To enable automatic PyPI deployment, you need to add a PyPI API token as a GitHub Secret:

1. Generate a PyPI API token at https://pypi.org/manage/account/token/
2. Go to your GitHub repository settings → Secrets and variables → Actions
3. Add a new repository secret named `PYPI_API_TOKEN` with the token value from PyPI

## Contributing

We welcome contributions! Please check out our [Contributing Guide](CONTRIBUTING.md) for guidelines on how to proceed.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.