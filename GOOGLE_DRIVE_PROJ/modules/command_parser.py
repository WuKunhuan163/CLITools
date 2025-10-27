#!/usr/bin/env python3
"""
统一的命令解析和分割模块

提供能够正确处理引号上下文的命令分割功能，
避免将引号内的操作符误认为命令分隔符。
"""

import re
from typing import List, Dict, Any, Optional, Tuple


class CommandSplitter:
    """统一的命令分割器"""
    
    # 支持的命令组合操作符
    COMBINATORS = ['&&', '||', ';']
    
    def __init__(self):
        pass
    
    def has_real_combinators(self, text: str) -> bool:
        """
        检测是否有真正的命令组合符（不在引号内的）
        
        Args:
            text: 要检测的命令字符串
            
        Returns:
            bool: True如果有真正的组合符，False否则
        """
        in_single_quote = False
        in_double_quote = False
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # 处理转义字符
            if char == '\\' and i + 1 < len(text):
                i += 2
                continue
            
            # 处理引号
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            
            # 检测组合符（只有在引号外才算）
            elif not in_single_quote and not in_double_quote:
                for combinator in self.COMBINATORS:
                    if text[i:i+len(combinator)] == combinator:
                        # 确保这不是更长操作符的一部分
                        if combinator == ';':
                            return True
                        elif combinator == '&&':
                            # 检查不是 &&&
                            if i + 2 >= len(text) or text[i+2] != '&':
                                return True
                        elif combinator == '||':
                            # 检查不是 |||
                            if i + 2 >= len(text) or text[i+2] != '|':
                                return True
            
            i += 1
        
        return False
    
    def split_command(self, command_str: str) -> List[Dict[str, Any]]:
        """
        分割命令字符串，正确处理引号上下文
        
        Args:
            command_str: 要分割的命令字符串
            
        Returns:
            List[Dict]: 分割后的命令列表，每个元素包含：
                - command: 命令字符串
                - operator: 前置操作符 (None, '&&', '||', ';')
                - position: 在原字符串中的位置信息
        """
        if not self.has_real_combinators(command_str):
            # 单个命令
            return [{
                'command': command_str.strip(),
                'operator': None,
                'position': {'start': 0, 'end': len(command_str)}
            }]
        
        # 解析命令和操作符
        commands = []
        current_command = ""
        current_operator = None
        in_single_quote = False
        in_double_quote = False
        i = 0
        command_start = 0
        
        while i < len(command_str):
            char = command_str[i]
            
            # 处理转义字符
            if char == '\\' and i + 1 < len(command_str):
                current_command += command_str[i:i+2]
                i += 2
                continue
            
            # 处理引号
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current_command += char
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current_command += char
            
            # 检测组合符（只有在引号外才算）
            elif not in_single_quote and not in_double_quote:
                found_combinator = None
                combinator_length = 0
                
                # 检查每个组合符
                for combinator in sorted(self.COMBINATORS, key=len, reverse=True):
                    if command_str[i:i+len(combinator)] == combinator:
                        # 确保这不是更长操作符的一部分
                        if combinator == ';':
                            found_combinator = combinator
                            combinator_length = len(combinator)
                            break
                        elif combinator == '&&':
                            if i + 2 >= len(command_str) or command_str[i+2] != '&':
                                found_combinator = combinator
                                combinator_length = len(combinator)
                                break
                        elif combinator == '||':
                            if i + 2 >= len(command_str) or command_str[i+2] != '|':
                                found_combinator = combinator
                                combinator_length = len(combinator)
                                break
                
                if found_combinator:
                    # 找到组合符，保存当前命令
                    if current_command.strip():
                        commands.append({
                            'command': current_command.strip(),
                            'operator': current_operator,
                            'position': {'start': command_start, 'end': i}
                        })
                    
                    # 准备下一个命令
                    current_operator = found_combinator
                    current_command = ""
                    i += combinator_length
                    
                    # 跳过组合符后的空白
                    while i < len(command_str) and command_str[i].isspace():
                        i += 1
                    command_start = i
                    continue
                else:
                    current_command += char
            else:
                current_command += char
            
            i += 1
        
        # 添加最后一个命令
        if current_command.strip():
            commands.append({
                'command': current_command.strip(),
                'operator': current_operator,
                'position': {'start': command_start, 'end': len(command_str)}
            })
        
        return commands
    
    def parse_command(self, command_str: str) -> Dict[str, Any]:
        """
        解析命令字符串，返回完整的解析信息
        
        Args:
            command_str: 要解析的命令字符串
            
        Returns:
            Dict: 解析结果，包含：
                - original: 原始命令字符串
                - is_compound: 是否为复合命令
                - commands: 分割后的命令列表
                - execution_plan: 执行计划
        """
        commands = self.split_command(command_str)
        
        return {
            'original': command_str,
            'is_compound': len(commands) > 1,
            'commands': commands,
            'execution_plan': self._create_execution_plan(commands)
        }
    
    def _create_execution_plan(self, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        创建执行计划
        
        Args:
            commands: 分割后的命令列表
            
        Returns:
            Dict: 执行计划
        """
        if len(commands) == 1:
            return {
                'type': 'single',
                'command': commands[0]['command']
            }
        
        # 分析执行逻辑
        has_and = any(cmd['operator'] == '&&' for cmd in commands)
        has_or = any(cmd['operator'] == '||' for cmd in commands)
        has_semicolon = any(cmd['operator'] == ';' for cmd in commands)
        
        plan_type = 'sequential'  # 默认顺序执行
        if has_and and not has_or:
            plan_type = 'conditional_and'  # 条件与执行
        elif has_or and not has_and:
            plan_type = 'conditional_or'   # 条件或执行
        elif has_and and has_or:
            plan_type = 'mixed_conditional'  # 混合条件执行
        elif has_semicolon:
            plan_type = 'sequential'  # 顺序执行
        
        return {
            'type': plan_type,
            'commands': commands,
            'total_commands': len(commands)
        }


# 全局实例
command_splitter = CommandSplitter()


def parse_command(command_str: str) -> Dict[str, Any]:
    """
    便捷函数：解析命令字符串
    
    Args:
        command_str: 要解析的命令字符串
        
    Returns:
        Dict: 解析结果
    """
    return command_splitter.parse_command(command_str)


def has_real_combinators(command_str: str) -> bool:
    """
    便捷函数：检测是否有真正的命令组合符
    
    Args:
        command_str: 要检测的命令字符串
        
    Returns:
        bool: True如果有真正的组合符，False否则
    """
    return command_splitter.has_real_combinators(command_str)


def split_command(command_str: str) -> List[Dict[str, Any]]:
    """
    便捷函数：分割命令字符串
    
    Args:
        command_str: 要分割的命令字符串
        
    Returns:
        List[Dict]: 分割后的命令列表
    """
    return command_splitter.split_command(command_str)


if __name__ == '__main__':
    # 测试用例
    test_cases = [
        "echo 'hello world'",
        "echo 'hello; world' && ls",
        "echo '测试中文：你好世界 Special chars: @#$%^&*()_+-=[]{}|;:,.<>?' > file.txt",
        "ls && echo 'success' || echo 'failed'",
        "cmd1; cmd2; cmd3",
        "echo 'test' | grep 'test'",
        "echo \"json: {'key': 'value; with semicolon'}\" && echo 'done'"
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case}")
        result = parse_command(test_case)
        print(f"是否复合命令: {result['is_compound']}")
        print(f"执行计划类型: {result['execution_plan']['type']}")
        for i, cmd in enumerate(result['commands']):
            operator_str = f" (操作符: {cmd['operator']})" if cmd['operator'] else ""
            print(f"  命令 {i+1}: {cmd['command']}{operator_str}")
