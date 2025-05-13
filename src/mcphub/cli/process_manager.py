"""Process manager for MCP servers."""
import os
import json
import psutil
import subprocess
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Set
from datetime import datetime
import logging
import socket
import time

logger = logging.getLogger("mcphub")


class ProcessManager:
    """Manages MCP server processes and their metadata.
    
    This class handles process creation, monitoring, and cleanup for MCP servers.
    It keeps track of running processes in a JSON file at ~/.mcphub/processes.json.
    
    Attributes:
        data_dir: Directory to store process metadata
        processes_file: Path to the processes.json file
        processes: Dictionary of process metadata indexed by instance ID (name:port)
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the process manager.
        
        Args:
            data_dir: Directory to store process metadata (defaults to ~/.mcphub)
        """
        if data_dir is None:
            self.data_dir = Path.home() / ".mcphub"
        else:
            self.data_dir = data_dir
            
        self.processes_file = self.data_dir / "processes.json"
        self._ensure_data_dir()
        self._load_processes()
    
    # ==========================================
    # Private Methods
    # ==========================================
    
    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_processes(self) -> None:
        """Load process metadata from file."""
        if self.processes_file.exists():
            with open(self.processes_file, "r") as f:
                self.processes = json.load(f)
        else:
            self.processes = {}
            self._save_processes()
    
    def _save_processes(self) -> None:
        """Save process metadata to file."""
        with open(self.processes_file, "w") as f:
            json.dump(self.processes, f, indent=2)
    
    def _get_instance_id(self, name: str, port: int) -> str:
        """Generate a unique instance ID for a server.
        
        Args:
            name: Server name
            port: Server port
            
        Returns:
            Unique instance ID string
        """
        return f"{name}:{port}"
    
    def _find_available_port(self, start_port: int = 3000, max_attempts: int = 100) -> int:
        """Find an available port starting from start_port.
        
        Args:
            start_port: Port to start checking from
            max_attempts: Maximum number of ports to check
            
        Returns:
            Available port number
            
        Raises:
            RuntimeError: If no available port is found after max_attempts
        """
        for port in range(start_port, start_port + max_attempts):
            try:
                # Try to bind to the port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        
        raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")
    
    def _check_port_conflict(self, port: int) -> Optional[Dict[str, Any]]:
        """Check if a port is already in use by another process.
        
        Args:
            port: Port number to check
            
        Returns:
            Process info dictionary if port is in use, None otherwise
        """
        for instance_id, process_info in self.processes.items():
            if port in process_info.get("ports", []):
                try:
                    # Verify process is still running
                    process = psutil.Process(process_info["pid"])
                    if process.is_running():
                        return process_info
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return None
    
    def _get_process_ports(self, process: psutil.Process) -> List[int]:
        """Get all ports used by a process.
        
        Args:
            process: Process to check
            
        Returns:
            List of port numbers
        """
        ports = set()
        try:
            for conn in process.connections(kind='inet'):
                if conn.laddr:
                    ports.add(conn.laddr.port)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return sorted(list(ports))
    
    def _get_uptime(self, process: psutil.Process) -> str:
        """Get the uptime of a process as a formatted string.
        
        Args:
            process: Process to get uptime for
            
        Returns:
            Formatted uptime string (e.g. "2 days, 01:23:45" or "00:01:30")
        """
        try:
            create_time = datetime.fromtimestamp(process.create_time())
            now = datetime.now()
            uptime = now - create_time
            
            # Format as days, hours, minutes, seconds
            days = uptime.days
            seconds = uptime.seconds
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                return f"{days} days, {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "Unknown"
    
    def _clean_defunct_processes(self) -> None:
        """Remove entries for processes that are no longer running."""
        to_remove = []
        for instance_id, info in self.processes.items():
            try:
                process = psutil.Process(info["pid"])
                if not process.is_running():
                    to_remove.append(instance_id)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                to_remove.append(instance_id)
        
        for instance_id in to_remove:
            del self.processes[instance_id]
        
        if to_remove:
            self._save_processes()
    
    # ==========================================
    # Public Methods
    # ==========================================
    
    def start_process(self, name: str, command: List[str], env: Optional[Dict[str, str]] = None) -> int:
        """Start a new MCP server process.
        
        Args:
            name: Name of the MCP server
            command: Command to run
            env: Environment variables
            
        Returns:
            Process ID of the started process
            
        Raises:
            RuntimeError: If no available port is found
            subprocess.SubprocessError: If the process fails to start
        """
        # Extract port from command if present
        port = None
        port_index = -1
        for i, arg in enumerate(command):
            if arg == "--port" and i + 1 < len(command):
                try:
                    port = int(command[i + 1])
                    port_index = i + 1
                except ValueError:
                    pass
                break
        
        # If no port specified, find an available one
        if port is None:
            try:
                port = self._find_available_port()
                # Add port to command
                command.extend(["--port", str(port)])
                logger.info(f"Automatically selected port {port}")
            except RuntimeError as e:
                logger.error(f"Failed to find available port: {e}")
                raise
        
        # Check for port conflicts
        if port:
            conflict = self._check_port_conflict(port)
            if conflict:
                logger.warning(
                    f"Port {port} is already in use by process {conflict['pid']} "
                    f"({conflict['name']}): {conflict['command']}"
                )
                # Try to find another available port
                try:
                    new_port = self._find_available_port(port + 1)
                    if port_index >= 0:
                        command[port_index] = str(new_port)
                    else:
                        command.extend(["--port", str(new_port)])
                    logger.info(f"Automatically switched to port {new_port}")
                    port = new_port
                except RuntimeError as e:
                    logger.error(f"Failed to find alternative port: {e}")
                    raise
        
        # Create process metadata
        instance_id = self._get_instance_id(name, port)
        process_info = {
            "name": name,
            "command": " ".join(command),
            "start_time": datetime.now().isoformat(),
            "env": env or {},
            "pid": None,
            "ports": [port] if port else [],
            "status": "starting",
            "warnings": []
        }
        
        try:
            # Start the process
            process = subprocess.Popen(
                command,
                env={**os.environ, **(env or {})},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Update process info
            process_info["pid"] = process.pid
            process_info["status"] = "running"
            
            # Check for port conflicts after process starts
            if port:
                # Wait a moment for the process to start
                time.sleep(1)
                
                # Check if our process got the port
                try:
                    # For SSE mode, we trust the port from the command
                    if "--stdio" in command:
                        process_info["ports"] = [port]
                    else:
                        our_ports = self._get_process_ports(process)
                        if port not in our_ports:
                            process_info["warnings"].append(
                                f"Port {port} is not available. The process may not be running correctly."
                            )
                except Exception as e:
                    logger.debug(f"Failed to check process ports: {e}")
            
            # Store process info using instance ID
            self.processes[instance_id] = process_info
            self._save_processes()
            
            return process.pid
            
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            raise
    
    def stop_process(self, pid: int) -> bool:
        """Stop a running MCP server process.
        
        Args:
            pid: Process ID to stop
            
        Returns:
            True if the process was stopped, False otherwise
        """
        try:
            process = psutil.Process(pid)
            
            # First try a graceful stop with SIGTERM
            process.terminate()
            
            # Wait for the process to exit
            try:
                process.wait(timeout=5)
                logger.info(f"Process {pid} stopped gracefully")
            except psutil.TimeoutExpired:
                # Force kill if it doesn't exit in time
                logger.warning(f"Process {pid} not responding to SIGTERM, sending SIGKILL")
                process.kill()
            
            # Find and remove the process entry
            instance_id_to_remove = None
            for instance_id, info in self.processes.items():
                if info["pid"] == pid:
                    instance_id_to_remove = instance_id
                    break
            
            if instance_id_to_remove:
                del self.processes[instance_id_to_remove]
                self._save_processes()
            
            return True
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} does not exist")
            return False
        except Exception as e:
            logger.error(f"Failed to stop process {pid}: {e}")
            return False
    
    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific process.
        
        Args:
            pid: Process ID to query
            
        Returns:
            Process information dictionary or None if not found
        """
        # Find process info by PID
        for instance_id, info in self.processes.items():
            if info["pid"] == pid:
                # Get stored info
                info = info.copy()
                
                # Update with current info from psutil
                try:
                    process = psutil.Process(pid)
                    if process.is_running():
                        # Update status
                        info["status"] = "running"
                        
                        # For non-SSE mode, update ports from process
                        if "--stdio" not in info.get("command", ""):
                            info["ports"] = self._get_process_ports(process)
                        
                        # Update uptime
                        info["uptime"] = self._get_uptime(process)
                        
                        # Check for zombie state
                        if process.status() == "zombie":
                            info["status"] = "zombie"
                            info["warnings"].append("Process is in zombie state")
                    else:
                        info["status"] = "not running"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    info["status"] = "not running"
                
                return info
        
        return None
    
    def list_processes(self) -> List[Dict[str, Any]]:
        """List all MCP server processes.
        
        Returns:
            List of process information dictionaries
        """
        # Clean up defunct processes first
        self._clean_defunct_processes()
        
        result = []
        
        # Get info for each process
        for instance_id, info in self.processes.items():
            try:
                pid = info["pid"]
                updated_info = self.get_process_info(pid)
                if updated_info:
                    # Add instance ID for reference
                    updated_info["instance_id"] = instance_id
                    result.append(updated_info)
            except (ValueError, TypeError):
                # Skip invalid PIDs
                continue
        
        return result
    
    def stop_all_processes(self) -> int:
        """Stop all running MCP server processes.
        
        Returns:
            Number of processes successfully stopped
        """
        stopped_count = 0
        
        for info in self.processes.values():
            try:
                pid = info["pid"]
                if self.stop_process(pid):
                    stopped_count += 1
            except (ValueError, TypeError):
                continue
        
        return stopped_count 