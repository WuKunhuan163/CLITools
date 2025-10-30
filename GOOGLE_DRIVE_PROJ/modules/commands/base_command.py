"""
Base command class for GDS special commands.
"""

from abc import ABC, abstractmethod
from typing import List

class BaseCommand(ABC):
    """Base class for all GDS special commands."""
    
    def __init__(self, shell_instance):
        """
        Initialize the command with a reference to the shell instance.
        
        Args:
            shell_instance: The GoogleDriveShell instance
        """
        self.shell = shell_instance
        self.main_instance = shell_instance  # For backward compatibility
        self.drive_service = shell_instance.drive_service if hasattr(shell_instance, 'drive_service') else None
    
    @property
    @abstractmethod
    def command_name(self) -> str:
        """Return the command name this handler processes."""
        pass
    
    @abstractmethod
    def execute(self, cmd: str, args: List[str], **kwargs) -> int:
        """
        Execute the command with given arguments.
        
        Args:
            cmd: The command name
            args: List of command arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        pass
    
    def validate_args(self, args: List[str]) -> bool:
        """
        Validate command arguments. Override in subclasses if needed.
        
        Args:
            args: List of command arguments
            
        Returns:
            bool: True if arguments are valid, False otherwise
        """
        return True
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        print(f"Error in BaseCommand: {message}")