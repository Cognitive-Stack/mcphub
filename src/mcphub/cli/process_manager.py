"""Process manager for MCP servers."""
import os
import json
import psutil
import subprocess
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import socket

logger = logging.getLogger("mcphub")

class ProcessManager:
    """Manages MCP server processes and their metadata."""
    
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
    
    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_processes(self):
        """Load process metadata from file."""
        if self.processes_file.exists():
            with open(self.processes_file, "r") as f:
                self.processes = json.load(f)
        else:
            self.processes = {}
            self._save_processes()
    
    def _save_processes(self):
        """Save process metadata to file."""
        with open(self.processes_file, "w") as f:
            json.dump(self.processes, f, indent=2)
    
    def _check_port_conflict(self, port: int) -> Optional[Dict[str, Any]]:
        """Check if a port is already in use by another process.
        
        Args:
            port: Port to check
            
        Returns:
            Process info dict if port is in use, None otherwise
        """
        for pid_str, info in self.processes.items():
            try:
                pid = int(pid_str)
                process = psutil.Process(pid)
                if process.is_running():
                    ports = self._get_process_ports(process)
                    if port in ports:
                        return {
                            "pid": pid,
                            "name": info.get("name", "Unknown"),
                            "command": info.get("command", "Unknown")
                        }
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                continue
        return None

    def _find_available_port(self, start_port: int = 3000, max_attempts: int = 100) -> int:
        """Find an available port starting from start_port.
        
        Args:
            start_port: Port to start checking from
            max_attempts: Maximum number of ports to check
            
        Returns:
            Available port number
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

    def start_process(self, name: str, command: List[str], env: Dict[str, str] = None) -> int:
        """Start a new MCP server process.
        
        Args:
            name: Name of the MCP server
            command: Command to run
            env: Environment variables
            
        Returns:
            Process ID of the started process
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
        process_info = {
            "name": name,
            "command": " ".join(command),
            "start_time": datetime.now().isoformat(),
            "env": env or {},
            "pid": None,
            "ports": [],
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
                import time
                time.sleep(1)
                
                # Check if our process got the port
                try:
                    our_ports = self._get_process_ports(process)
                    if port not in our_ports:
                        process_info["warnings"].append(
                            f"Port {port} is not available. The process may not be running correctly."
                        )
                except Exception as e:
                    logger.debug(f"Failed to check process ports: {e}")
            
            # Store process info
            self.processes[str(process.pid)] = process_info
            self._save_processes()
            
            return process.pid
            
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            process_info["status"] = "failed"
            process_info["error"] = str(e)
            self.processes[str(process.pid)] = process_info
            self._save_processes()
            raise
    
    def stop_process(self, pid: int) -> bool:
        """Stop a running MCP server process.
        
        Args:
            pid: Process ID to stop
            
        Returns:
            True if process was stopped, False otherwise
        """
        pid_str = str(pid)
        if pid_str not in self.processes:
            return False
        
        try:
            # Try graceful shutdown first
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to terminate
            try:
                process = psutil.Process(pid)
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Force kill if process doesn't terminate
                os.kill(pid, signal.SIGKILL)
            
            # Update process info
            self.processes[pid_str]["status"] = "stopped"
            self.processes[pid_str]["stop_time"] = datetime.now().isoformat()
            self._save_processes()
            
            return True
            
        except ProcessLookupError:
            # Process already gone
            self.processes[pid_str]["status"] = "stopped"
            self.processes[pid_str]["stop_time"] = datetime.now().isoformat()
            self._save_processes()
            return True
        except Exception as e:
            logger.error(f"Failed to stop process {pid}: {e}")
            return False
    
    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get information about a process.
        
        Args:
            pid: Process ID
            
        Returns:
            Process information dictionary or None if not found
        """
        pid_str = str(pid)
        if pid_str not in self.processes:
            return None
        
        info = self.processes[pid_str].copy()
        
        try:
            process = psutil.Process(pid)
            
            # Update runtime info
            info["status"] = "running" if process.is_running() else "stopped"
            info["uptime"] = self._get_uptime(process)
            
            # Get ports with retry for Docker containers
            ports = self._get_process_ports(process)
            if not ports and "docker" in info.get("command", "").lower():
                # Retry after a short delay for Docker containers
                import time
                time.sleep(1)
                ports = self._get_process_ports(process)
            
            info["ports"] = ports
            
            # Check for port conflicts
            if ports:
                for port in ports:
                    conflict = self._check_port_conflict(port)
                    if conflict and conflict["pid"] != pid:
                        warning = (
                            f"Port {port} is also in use by process {conflict['pid']} "
                            f"({conflict['name']}): {conflict['command']}"
                        )
                        if warning not in info.get("warnings", []):
                            if "warnings" not in info:
                                info["warnings"] = []
                            info["warnings"].append(warning)
            
            # Update process info
            self.processes[pid_str].update(info)
            self._save_processes()
            
        except psutil.NoSuchProcess:
            info["status"] = "stopped"
            info["stop_time"] = datetime.now().isoformat()
            self.processes[pid_str].update(info)
            self._save_processes()
        
        return info
    
    def list_processes(self) -> List[Dict[str, Any]]:
        """List all managed processes with their current status.
        
        Returns:
            List of process information dictionaries
        """
        processes = []
        for pid_str, info in self.processes.items():
            try:
                pid = int(pid_str)
                process_info = self.get_process_info(pid)
                if process_info:
                    processes.append(process_info)
            except ValueError:
                continue
        return processes
    
    def _get_uptime(self, process: psutil.Process) -> str:
        """Get process uptime in human readable format."""
        try:
            create_time = datetime.fromtimestamp(process.create_time())
            uptime = datetime.now() - create_time
            
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
            return "N/A"
    
    def _get_process_ports(self, process: psutil.Process) -> List[int]:
        """Get list of ports used by a process and its children.
        
        Args:
            process: Process to check
            
        Returns:
            List of ports in use
        """
        ports = set()
        
        try:
            # Check the main process
            for conn in process.connections():
                if conn.laddr and conn.status == 'LISTEN':
                    ports.add(conn.laddr.port)
            
            # Check child processes
            for child in process.children(recursive=True):
                try:
                    for conn in child.connections():
                        if conn.laddr and conn.status == 'LISTEN':
                            ports.add(conn.laddr.port)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Check for Docker containers
            if "docker" in process.name().lower():
                try:
                    # Get container ID from process command line
                    cmdline = " ".join(process.cmdline())
                    if "docker" in cmdline:
                        # Extract container ID or name
                        container_id = None
                        for arg in process.cmdline():
                            if arg.startswith("--name="):
                                container_id = arg.split("=")[1]
                                break
                            elif arg.startswith("--cidfile="):
                                with open(arg.split("=")[1], "r") as f:
                                    container_id = f.read().strip()
                                break
                        
                        if container_id:
                            # Get container ports using docker inspect
                            result = subprocess.run(
                                ["docker", "inspect", "-f", "{{range $p, $conf := .NetworkSettings.Ports}}{{$p}} {{end}}", container_id],
                                capture_output=True,
                                text=True
                            )
                            if result.returncode == 0:
                                for port_mapping in result.stdout.split():
                                    if "->" in port_mapping:
                                        host_port = port_mapping.split("->")[0].split(":")[-1]
                                        ports.add(int(host_port))
                except Exception as e:
                    logger.debug(f"Failed to get Docker container ports: {e}")
            
            return sorted(list(ports))
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return [] 