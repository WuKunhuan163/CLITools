"""
Command registry for managing GDS special commands.
"""

from typing import Dict, Optional
from .base_command import BaseCommand


class CommandRegistry:
    """Registry for managing special commands."""
    
    def __init__(self):
        self._commands: Dict[str, BaseCommand] = {}
    
    def register(self, command: BaseCommand) -> None:
        """
        Register a command handler.
        
        Args:
            command: Command handler instance
        """
        self._commands[command.command_name] = command
    
    def register_under_name(self, command: BaseCommand, name: str) -> None:
        """
        Register a command handler under a specific name.
        Useful for merged commands that handle multiple command names.
        
        Args:
            command: Command handler instance
            name: Command name to register under
        """
        self._commands[name] = command
    
    def get_command(self, name: str) -> Optional[BaseCommand]:
        """
        Get command handler by name.
        
        Args:
            name: Command name
            
        Returns:
            BaseCommand instance or None if not found
        """
        return self._commands.get(name)
    
    def is_special_command(self, name: str) -> bool:
        """
        Check if a command is a special command.
        
        Args:
            name: Command name
            
        Returns:
            bool: True if it's a special command, False otherwise
        """
        return name in self._commands
    