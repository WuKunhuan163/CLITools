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
    
    def _smart_fix_json(self, json_str: str) -> str:
        """
        Intelligently fix JSON by adding missing quotes and using eval.
        
        Args:
            json_str: JSON string that may have missing quotes
            
        Returns:
            str: Fixed JSON string
        """
        import re
        import ast
        import json
        
        # Strategy: Use regex to identify and fix different JSON patterns
        fixed_str = json_str
        
        # Pattern 1: Fix string replacement [[text1, text2]] -> [["text1", "text2"]]
        string_pattern = r'\[\[([^"]+?),\s*([^"]+?)\]\]'
        def fix_string_replacement(match):
            text1 = match.group(1).strip()
            text2 = match.group(2).strip()
            return f'[["{text1}", "{text2}"]]'
        
        if re.search(string_pattern, fixed_str):
            fixed_str = re.sub(string_pattern, fix_string_replacement, fixed_str)
        
        # Pattern 2: Fix line replacement [[[numbers], text]] -> [[[numbers], "text"]]
        line_pattern = r'(\[\[\[[0-9, ]+\],\s*)([^"]+?)(\]\])'
        def fix_line_replacement(match):
            prefix = match.group(1)
            text = match.group(2).strip()
            suffix = match.group(3)
            return f'{prefix}"{text}"{suffix}'
        
        if re.search(line_pattern, fixed_str):
            fixed_str = re.sub(line_pattern, fix_line_replacement, fixed_str)
        
        # Now try to parse with ast.literal_eval
        try:
            parsed = ast.literal_eval(fixed_str)
            # Convert back to JSON string
            result = json.dumps(parsed)
            return result
        except Exception as e:
            # Fallback to original method
            return self._fix_unquoted_json_strings(json_str)
    
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
                        
                        # Try to intelligently fix the JSON by adding missing quotes
                        fixed_json = self._smart_fix_json(json_str)
                        
                        # Return args with JSON parts replaced by single reconstructed JSON
                        new_args = args[:json_start_idx] + [fixed_json]
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
