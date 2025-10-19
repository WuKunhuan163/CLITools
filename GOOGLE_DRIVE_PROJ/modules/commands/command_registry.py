"""
Command registry for managing GDS special commands.
"""

from typing import Dict, List, Optional
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
    
    def get_all_commands(self) -> List[str]:
        """
        Get list of all registered command names.
        
        Returns:
            List of command names
        """
        return list(self._commands.keys())
    
    def _fix_unquoted_json_strings(self, json_str: str) -> str:
        """
        Fix unquoted strings in JSON by adding quotes around them.
        This handles cases where shell parsing split quoted strings into words.
        
        Args:
            json_str: JSON string with potentially unquoted strings
            
        Returns:
            str: JSON string with properly quoted strings
        """
        import re
        
        # Strategy: Find word sequences between array delimiters and quote them as single strings
        # Pattern matches: [word1 word2 word3, word4 word5]
        # Should become: ["word1 word2 word3", "word4 word5"]
        
        def fix_array_elements(text):
            # Find content between [ and ] or between , and , or between , and ]
            # This pattern captures sequences of words that should be quoted strings
            
            # Split by array/object delimiters while preserving them
            parts = re.split(r'([\[\],])', text)
            result_parts = []
            
            for part in parts:
                if part in ['[', ']', ',']:
                    result_parts.append(part)
                else:
                    # This is content between delimiters - check if it needs quoting
                    stripped = part.strip()
                    if stripped and not stripped.startswith('"') and not stripped.endswith('"'):
                        # Check if it's a sequence of words that should be quoted
                        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_\s]*$', stripped):
                            result_parts.append(f' "{stripped}" ')
                        else:
                            result_parts.append(part)
                    else:
                        result_parts.append(part)
            
            return ''.join(result_parts)
        
        return fix_array_elements(json_str)
    
    def _process_json_arguments(self, name: str, args: List[str]) -> List[str]:
        """
        Process JSON arguments for commands that need them.
        
        Args:
            name: Command name
            args: Original arguments
            
        Returns:
            List[str]: Processed arguments
        """
        # Commands that expect JSON arguments
        json_argument_commands = ['edit']
        
        if name not in json_argument_commands:
            return args
        
        if name == 'edit' and len(args) >= 2:
            # Look for JSON pattern split across multiple arguments
            json_parts = []
            json_start_idx = -1
            
            for i, arg in enumerate(args):
                if arg.startswith('[') and json_start_idx == -1:
                    # Start of JSON
                    json_start_idx = i
                    json_parts = [arg]
                elif json_start_idx >= 0:
                    # Continuation of JSON
                    json_parts.append(arg)
                    if arg.endswith(']'):
                        # End of JSON found, reconstruct it
                        json_str = ' '.join(json_parts)
                        
                        # Fix unquoted strings in the JSON
                        fixed_json = self._fix_unquoted_json_strings(json_str)
                        
                        # Return args with JSON parts replaced by single reconstructed JSON
                        new_args = args[:json_start_idx] + [fixed_json]
                        # print(f"🔍 DEBUG: Reconstructed JSON: {json_parts} -> '{json_str}' -> '{fixed_json}'")
                        return new_args
            
            # If no split JSON found, check if it's already a single JSON argument
            for i, arg in enumerate(args):
                if arg.startswith('[') and arg.endswith(']'):
                    # Already a complete JSON argument
                    return args
        
        return args

    def execute_command(self, name: str, args: List[str], **kwargs) -> int:
        """
        Execute a command by name.
        
        Args:
            name: Command name
            args: Command arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        command = self.get_command(name)
        if command is None:
            print(f"Error: Unknown command '{name}'")
            return 1
        
        # Process JSON arguments if needed
        processed_args = self._process_json_arguments(name, args)
        # print(f"🔍 DEBUG: CommandRegistry.execute_command called with name='{name}', args={args}, processed_args={processed_args}")
        
        if not command.validate_args(processed_args):
            return 1
        
        return command.execute(name, processed_args, **kwargs)
