from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MCPServerConfigSchema(BaseModel):
    """Pydantic model for MCP server configuration."""
    command: str = Field(..., description="The command to run the server")
    args: List[str] = Field(default_factory=list, description="List of command line arguments")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    setup_script: Optional[str] = Field(None, description="Setup script to run before starting the server")
    package_name: Optional[str] = Field(None, description="Package name or identifier")
    repo_url: Optional[str] = Field(None, description="GitHub repository URL")
    description: Optional[str] = Field(None, description="Server description")
    tags: Optional[List[str]] = Field(None, description="List of tags for the server")
    cwd: Optional[str] = Field(None, description="Working directory for the server") 