"""
Windows Environment Variable Bridge for WSL
===========================================

This module provides utilities to access Windows system environment variables
from within WSL (Windows Subsystem for Linux). This is particularly useful
for accessing API credentials stored as Windows system environment variables.

Usage:
    from src.utils.windows_env_bridge import get_windows_env_var, load_windows_env_vars
    
    # Get a single Windows environment variable
    api_key = get_windows_env_var('KRAKEN_KEY')
    
    # Load all Windows environment variables matching a pattern
    kraken_vars = load_windows_env_vars('KRAKEN_*')
    
    # Apply Windows environment variables to current environment
    apply_windows_env_vars(['KRAKEN_KEY', 'KRAKEN_SECRET'])
"""

import logging
import os
import re
import subprocess
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WindowsEnvBridge:
    """Bridge for accessing Windows environment variables from WSL"""

    def __init__(self):
        self._powershell_path = self._find_powershell()
        self._cache_timeout = 300  # 5 minutes

    def _find_powershell(self) -> Optional[str]:
        """Find PowerShell executable in WSL or Windows"""
        # Check if running on Windows directly
        if os.name == 'nt':
            # Running on Windows, use direct PowerShell command
            possible_commands = ['powershell', 'pwsh']
            for cmd in possible_commands:
                try:
                    result = subprocess.run(
                        [cmd, '-Command', 'echo test'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        logger.debug(f"Found PowerShell command: {cmd}")
                        return cmd
                except Exception:
                    continue
        else:
            # Running on WSL, check mounted paths
            possible_paths = [
                "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                "/mnt/c/Windows/System32/PowerShell/pwsh.exe",
                "/mnt/c/Program Files/PowerShell/7/pwsh.exe",
                "/mnt/c/Program Files (x86)/PowerShell/7/pwsh.exe"
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    logger.debug(f"Found PowerShell at: {path}")
                    return path

            # Try to find powershell.exe in PATH
            try:
                result = subprocess.run(
                    ["which", "powershell.exe"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
                    logger.debug(f"Found PowerShell in PATH: {path}")
                    return path
            except Exception as e:
                logger.debug(f"Failed to find PowerShell in PATH: {e}")

        logger.debug("PowerShell not found - will use environment variables directly")
        return None

    def _sanitize_env_var_name(self, var_name: str) -> bool:
        """
        Validate environment variable name to prevent command injection.
        
        Args:
            var_name: Environment variable name to validate
            
        Returns:
            True if safe, False if potentially malicious
        """
        if not var_name or not isinstance(var_name, str):
            return False

        # Environment variable names should only contain alphanumeric chars and underscores
        # Maximum reasonable length is 255 characters
        if len(var_name) > 255:
            return False

        # Check for malicious characters that could be used for injection
        dangerous_chars = ["'", '"', '`', '$', ';', '&', '|', '<', '>', '(', ')', '{', '}', '[', ']', '\n', '\r', '\t']
        if any(char in var_name for char in dangerous_chars):
            logger.warning(f"Potentially malicious environment variable name rejected: {var_name}")
            return False

        # Must start with letter or underscore, contain only alphanumeric and underscores
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', var_name):
            logger.warning(f"Invalid environment variable name format: {var_name}")
            return False

        return True

    @lru_cache(maxsize=128)
    def get_windows_env_var(self, var_name: str) -> Optional[str]:
        """
        Get a Windows environment variable by name with security validation.
        
        Args:
            var_name: Name of the environment variable
            
        Returns:
            Value of the environment variable or None if not found
        """
        if not self._powershell_path:
            logger.warning("PowerShell not available - cannot access Windows environment variables")
            return None

        # Validate variable name to prevent command injection
        if not self._sanitize_env_var_name(var_name):
            logger.error(f"Security violation: Rejected unsafe environment variable name: {var_name}")
            return None

        try:
            # Use PowerShell with parameterized command to prevent injection
            # Use -EncodedCommand to avoid quote escaping issues
            powershell_script = f"""
                $userVar = [Environment]::GetEnvironmentVariable('{var_name}', 'User')
                $machineVar = [Environment]::GetEnvironmentVariable('{var_name}', 'Machine')
                if ($userVar) {{ Write-Output $userVar }}
                elseif ($machineVar) {{ Write-Output $machineVar }}
            """

            cmd = [
                self._powershell_path,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", powershell_script.strip()
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode == 0:
                value = result.stdout.strip()
                if value and value != "":
                    logger.debug(f"Retrieved Windows environment variable {var_name}")
                    return value
                else:
                    logger.debug(f"Windows environment variable {var_name} is empty or not found")
                    return None
            else:
                logger.warning(f"PowerShell command failed for {var_name}: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout accessing Windows environment variable {var_name}")
            return None
        except Exception as e:
            logger.error(f"Error accessing Windows environment variable {var_name}: {e}")
            return None

    def _sanitize_pattern(self, pattern: str) -> bool:
        """
        Validate pattern string to prevent command injection.
        
        Args:
            pattern: Pattern string to validate
            
        Returns:
            True if safe, False if potentially malicious
        """
        if not pattern or not isinstance(pattern, str):
            return False

        # Reasonable length limit
        if len(pattern) > 100:
            return False

        # Allow only safe characters for environment variable patterns
        # Letters, numbers, underscore, asterisk, and question mark
        if not re.match(r'^[A-Za-z0-9_*?]+$', pattern):
            logger.warning(f"Invalid pattern format rejected: {pattern}")
            return False

        return True

    def load_windows_env_vars(self, pattern: str = "*") -> Dict[str, str]:
        """
        Load Windows environment variables matching a pattern.
        
        Args:
            pattern: Wildcard pattern to match variable names (e.g., 'KRAKEN_*')
            
        Returns:
            Dictionary of environment variables
        """
        if not self._powershell_path:
            logger.warning("PowerShell not available - cannot access Windows environment variables")
            return {}

        # Validate pattern to prevent command injection
        if not self._sanitize_pattern(pattern):
            logger.error(f"Security violation: Rejected unsafe pattern: {pattern}")
            return {}

        try:
            # Convert shell pattern to PowerShell pattern
            ps_pattern = pattern.replace("*", ".*").replace("?", ".")

            # PowerShell command to get environment variables
            cmd = [
                self._powershell_path,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command",
                f"""
                $vars = @{{}}
                $user_vars = [Environment]::GetEnvironmentVariables('User')
                $machine_vars = [Environment]::GetEnvironmentVariables('Machine')
                
                # Combine user and machine variables (user takes precedence)
                foreach ($kv in $machine_vars.GetEnumerator()) {{
                    if ($kv.Key -match '^{ps_pattern}$') {{
                        $vars[$kv.Key] = $kv.Value
                    }}
                }}
                foreach ($kv in $user_vars.GetEnumerator()) {{
                    if ($kv.Key -match '^{ps_pattern}$') {{
                        $vars[$kv.Key] = $kv.Value
                    }}
                }}
                
                # Output as key=value pairs
                foreach ($kv in $vars.GetEnumerator()) {{
                    Write-Output "$($kv.Key)=$($kv.Value)"
                }}
                """
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                check=False
            )

            if result.returncode == 0:
                env_vars = {}
                for line in result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

                logger.info(f"Loaded {len(env_vars)} Windows environment variables matching '{pattern}'")
                return env_vars
            else:
                logger.warning(f"PowerShell command failed: {result.stderr}")
                return {}

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout loading Windows environment variables with pattern '{pattern}'")
            return {}
        except Exception as e:
            logger.error(f"Error loading Windows environment variables: {e}")
            return {}

    def apply_to_current_environment(self, var_names: List[str]) -> Dict[str, bool]:
        """
        Apply Windows environment variables to the current process environment.
        
        Args:
            var_names: List of environment variable names to apply
            
        Returns:
            Dictionary showing which variables were successfully applied
        """
        results = {}

        for var_name in var_names:
            value = self.get_windows_env_var(var_name)
            if value is not None:
                os.environ[var_name] = value
                results[var_name] = True
                logger.info(f"Applied Windows environment variable {var_name} to current environment")
            else:
                results[var_name] = False
                logger.warning(f"Failed to apply Windows environment variable {var_name}")

        return results

    def get_credential_status(self) -> Dict[str, Any]:
        """
        Get status of Windows credential access.
        
        Returns:
            Dictionary with credential access status
        """
        status = {
            "powershell_available": self._powershell_path is not None,
            "powershell_path": self._powershell_path,
            "can_access_windows_env": False,
            "kraken_credentials_found": False,
            "kraken_key_available": False,
            "kraken_secret_available": False,
            "error_message": None
        }

        if not self._powershell_path:
            status["error_message"] = "PowerShell executable not found"
            return status

        try:
            # Test access by checking for KRAKEN_KEY
            test_value = self.get_windows_env_var("KRAKEN_KEY")
            status["can_access_windows_env"] = True

            if test_value:
                status["kraken_key_available"] = True

            # Check for KRAKEN_SECRET
            secret_value = self.get_windows_env_var("KRAKEN_SECRET")
            if secret_value:
                status["kraken_secret_available"] = True

            status["kraken_credentials_found"] = status["kraken_key_available"] and status["kraken_secret_available"]

        except Exception as e:
            status["error_message"] = str(e)

        return status


# Detect if we're running in WSL
def _is_wsl() -> bool:
    """Check if we're running in WSL"""
    try:
        with open('/proc/version') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False

WSL_ENVIRONMENT = _is_wsl()
WINDOWS_ENV_BRIDGE_AVAILABLE = True

# Global instance
_windows_env_bridge = WindowsEnvBridge()


def get_windows_env_var(var_name: str) -> Optional[str]:
    """
    Convenience function to get a Windows environment variable.
    
    Args:
        var_name: Name of the environment variable
        
    Returns:
        Value of the environment variable or None if not found
    """
    return _windows_env_bridge.get_windows_env_var(var_name)


def load_windows_env_vars(pattern: str = "*") -> Dict[str, str]:
    """
    Convenience function to load Windows environment variables.
    
    Args:
        pattern: Wildcard pattern to match variable names
        
    Returns:
        Dictionary of environment variables
    """
    return _windows_env_bridge.load_windows_env_vars(pattern)


def apply_windows_env_vars(var_names: List[str]) -> Dict[str, bool]:
    """
    Convenience function to apply Windows environment variables to current environment.
    
    Args:
        var_names: List of environment variable names to apply
        
    Returns:
        Dictionary showing which variables were successfully applied
    """
    return _windows_env_bridge.apply_to_current_environment(var_names)


def setup_kraken_credentials() -> bool:
    """
    Setup Kraken API credentials from Windows environment variables.
    
    Returns:
        True if credentials were successfully loaded and applied
    """
    logger.info("Setting up Kraken credentials from Windows environment variables...")

    # Apply Kraken credentials
    results = apply_windows_env_vars(['KRAKEN_KEY', 'KRAKEN_SECRET'])

    # Check if both credentials were applied
    success = results.get('KRAKEN_KEY', False) and results.get('KRAKEN_SECRET', False)

    if success:
        logger.info("Successfully loaded Kraken credentials from Windows environment variables")
        # Verify they're available in current environment
        if os.getenv('KRAKEN_KEY') and os.getenv('KRAKEN_SECRET'):
            logger.info("Kraken credentials confirmed available in current environment")
            return True
        else:
            logger.error("Credentials were applied but not found in current environment")
            return False
    else:
        logger.error("Failed to load Kraken credentials from Windows environment variables")
        # SECURITY: Never log actual credential values
        key_present = bool(results.get('KRAKEN_KEY'))
        secret_present = bool(results.get('KRAKEN_SECRET'))
        logger.error(f"Results: KRAKEN_KEY={'[PRESENT]' if key_present else '[MISSING]'}, KRAKEN_SECRET={'[PRESENT]' if secret_present else '[MISSING]'}")

        if key_present:
            logger.error(f"KRAKEN_KEY length: {len(results.get('KRAKEN_KEY', ''))} characters")
        if secret_present:
            logger.error(f"KRAKEN_SECRET length: {len(results.get('KRAKEN_SECRET', ''))} characters")

        # Show diagnostic information
        status = _windows_env_bridge.get_credential_status()
        logger.error(f"Credential access status: {status}")

        return False


def get_windows_credential_status() -> Dict[str, Any]:
    """
    Get status of Windows credential access.
    
    Returns:
        Dictionary with credential access status
    """
    return _windows_env_bridge.get_credential_status()


__all__ = [
    'WindowsEnvBridge',
    'WSL_ENVIRONMENT',
    'WINDOWS_ENV_BRIDGE_AVAILABLE',
    'get_windows_env_var',
    'load_windows_env_vars',
    'apply_windows_env_vars',
    'setup_kraken_credentials',
    'get_windows_credential_status'
]
