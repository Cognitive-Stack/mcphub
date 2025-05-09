"""Tests for the ProcessManager class."""
import os
import json
import pytest
import signal
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import psutil
import socket
from datetime import datetime
from mcphub.cli.process_manager import ProcessManager

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for testing."""
    temp_dir = tmp_path / "mcphub_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

@pytest.fixture
def mock_processes_file():
    """Mock the processes.json file."""
    return {
        "1234": {
            "name": "test-server",
            "command": "python server.py --port 3000",
            "start_time": "2024-03-20T10:00:00",
            "env": {},
            "pid": 1234,
            "ports": [3000],
            "status": "running",
            "warnings": []
        }
    }

@pytest.fixture
def process_manager(temp_data_dir):
    """Create a ProcessManager instance with a temporary data directory."""
    # Create the processes.json file
    processes_file = temp_data_dir / "processes.json"
    processes_file.write_text("{}")
    return ProcessManager(data_dir=temp_data_dir)

def test_init_default_data_dir():
    """Test ProcessManager initialization with default data directory."""
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = Path("/tmp/test")  # Use /tmp instead of /home
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("builtins.open", mock_open(read_data="{}")):
                manager = ProcessManager()
                assert manager.data_dir == Path("/tmp/test/.mcphub")
                assert manager.processes_file == Path("/tmp/test/.mcphub/processes.json")
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

def test_init_custom_data_dir(temp_data_dir):
    """Test ProcessManager initialization with custom data directory."""
    with patch("builtins.open", mock_open(read_data="{}")):
        manager = ProcessManager(data_dir=temp_data_dir)
        assert manager.data_dir == temp_data_dir
        assert manager.processes_file == temp_data_dir / "processes.json"

def test_ensure_data_dir(temp_data_dir):
    """Test that data directory is created if it doesn't exist."""
    manager = ProcessManager(data_dir=temp_data_dir)
    assert temp_data_dir.exists()
    assert temp_data_dir.is_dir()

def test_load_processes_empty(temp_data_dir):
    """Test loading processes from an empty file."""
    # Create an empty processes.json file
    processes_file = temp_data_dir / "processes.json"
    processes_file.write_text("{}")
    
    manager = ProcessManager(data_dir=temp_data_dir)
    assert manager.processes == {}
    assert processes_file.exists()

def test_load_processes_existing(mock_processes_file, temp_data_dir):
    """Test loading processes from an existing file."""
    # Create a processes.json file with mock data
    processes_file = temp_data_dir / "processes.json"
    processes_file.write_text(json.dumps(mock_processes_file))
    
    manager = ProcessManager(data_dir=temp_data_dir)
    assert manager.processes == mock_processes_file

def test_save_processes(process_manager, mock_processes_file):
    """Test saving processes to file."""
    process_manager.processes = mock_processes_file.copy()
    process_manager._save_processes()
    
    # Read the saved file and verify its contents
    saved_data = json.loads(process_manager.processes_file.read_text())
    assert saved_data == mock_processes_file

def test_check_port_conflict(process_manager, mock_processes_file):
    """Test checking for port conflicts."""
    process_manager.processes = mock_processes_file.copy()
    with patch("psutil.Process") as mock_process:
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_process.return_value = mock_proc
        
        # Mock _get_process_ports to return a list containing the test port
        with patch.object(process_manager, "_get_process_ports", return_value=[3000]):
            conflict = process_manager._check_port_conflict(3000)
            assert conflict is not None
            assert conflict["pid"] == 1234
            assert conflict["name"] == "test-server"

def test_find_available_port(process_manager):
    """Test finding an available port."""
    with patch("socket.socket") as mock_socket:
        mock_socket.return_value.__enter__.return_value.bind.side_effect = [
            OSError,  # First port is taken
            None      # Second port is available
        ]
        port = process_manager._find_available_port(start_port=3000, max_attempts=2)
        assert port == 3001

def test_start_process_with_port(process_manager):
    """Test starting a process with a specified port."""
    command = ["python", "server.py", "--port", "3000"]
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_popen.return_value = mock_process
        
        with patch.object(process_manager, "_check_port_conflict", return_value=None):
            with patch.object(process_manager, "_get_process_ports", return_value=[3000]):
                pid = process_manager.start_process("test-server", command)
                assert pid == 1234
                assert str(pid) in process_manager.processes
                assert process_manager.processes[str(pid)]["status"] == "running"

def test_start_process_without_port(process_manager):
    """Test starting a process without a specified port."""
    command = ["python", "server.py"]
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_popen.return_value = mock_process
        
        with patch.object(process_manager, "_find_available_port", return_value=3000):
            with patch.object(process_manager, "_check_port_conflict", return_value=None):
                with patch.object(process_manager, "_get_process_ports", return_value=[3000]):
                    pid = process_manager.start_process("test-server", command)
                    assert pid == 1234
                    assert "--port" in process_manager.processes[str(pid)]["command"]
                    assert "3000" in process_manager.processes[str(pid)]["command"]

def test_stop_process(process_manager, mock_processes_file):
    """Test stopping a running process."""
    process_manager.processes = mock_processes_file.copy()
    with patch("os.kill") as mock_kill:
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_process.return_value = mock_proc
            mock_proc.wait.return_value = None
            
            result = process_manager.stop_process(1234)
            assert result is True
            assert process_manager.processes["1234"]["status"] == "stopped"
            mock_kill.assert_called_once_with(1234, signal.SIGTERM)

def test_stop_process_not_found(process_manager):
    """Test stopping a non-existent process."""
    result = process_manager.stop_process(9999)
    assert result is False

def test_get_process_info(process_manager, mock_processes_file):
    """Test getting information about a process."""
    process_manager.processes = mock_processes_file.copy()
    with patch("psutil.Process") as mock_process:
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_process.return_value = mock_proc
        
        info = process_manager.get_process_info(1234)
        assert info is not None
        assert info["name"] == "test-server"
        assert info["status"] == "running"

def test_get_process_info_not_found(process_manager):
    """Test getting information about a non-existent process."""
    info = process_manager.get_process_info(9999)
    assert info is None

def test_list_processes(process_manager, mock_processes_file):
    """Test listing all processes."""
    process_manager.processes = mock_processes_file.copy()
    with patch("psutil.Process") as mock_process:
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        mock_process.return_value = mock_proc
        
        processes = process_manager.list_processes()
        assert len(processes) == 1
        assert processes[0]["name"] == "test-server"
        assert processes[0]["status"] == "running"

def test_get_uptime(process_manager):
    """Test getting process uptime."""
    with patch("psutil.Process") as mock_process:
        mock_proc = MagicMock()
        mock_proc.create_time.return_value = datetime.now().timestamp() - 3600  # 1 hour ago
        mock_process.return_value = mock_proc
        
        uptime = process_manager._get_uptime(mock_proc)
        assert "1h" in uptime

def test_get_process_ports(process_manager):
    """Test getting ports used by a process."""
    with patch("psutil.Process") as mock_process:
        mock_proc = MagicMock()
        mock_conn = MagicMock()
        mock_conn.laddr = MagicMock(port=3000)
        mock_conn.status = "LISTEN"
        mock_proc.connections.return_value = [mock_conn]
        mock_process.return_value = mock_proc
        
        ports = process_manager._get_process_ports(mock_proc)
        assert 3000 in ports 