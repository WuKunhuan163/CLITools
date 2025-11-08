#!/usr/bin/env python3
"""
Heredoc Translator Module
将heredoc语法翻译为等效的echo命令
"""

import re
import shlex

def translate_heredoc(command):
    """
    将包含heredoc语法的命令翻译为等效的echo命令
    
    Args:
        command (str): 可能包含heredoc语法的命令
        
    Returns:
        tuple: (translated_commands, is_heredoc)
            - translated_commands: 翻译后的命令列表
            - is_heredoc: 是否检测到heredoc语法
    """
    # 检测heredoc模式: cmd << "EOF" 或 cmd << EOF
    heredoc_pattern = r'^(.+?)\s*<<\s*["\']?(\w+)["\']?\s*$'
    
    lines = command.strip().split('\n')
    if len(lines) < 2:  # 至少需要2行：命令行和结束标记（空heredoc）
        return [command], False
    
    first_line = lines[0].strip()
    match = re.match(heredoc_pattern, first_line)
    
    if not match:
        return [command], False
    
    base_command = match.group(1).strip()
    end_marker = match.group(2)
    
    # 查找结束标记
    content_lines = []
    end_marker_found = False
    
    for i in range(1, len(lines)):
        line = lines[i]
        # 检查是否为结束标记（去除空格后比较）
        if line.strip() == end_marker:
            end_marker_found = True
            break
        # 保留所有空格，包括尾随空格
        content_lines.append(line)
    
    if not end_marker_found:
        # 没有找到结束标记，不是有效的heredoc
        return [command], False
    
    # 分析base_command，确定是重定向还是管道
    if '>' in base_command:
        # 重定向模式：cat > file.txt
        return _translate_heredoc_redirect(base_command, content_lines)
    elif '|' in base_command:
        # 管道模式：cat | command
        return _translate_heredoc_pipe(base_command, content_lines)
    else:
        # 简单输入模式：cat
        return _translate_heredoc_simple(base_command, content_lines)

def _translate_heredoc_redirect(base_command, content_lines):
    """
    翻译重定向类型的heredoc
    例如：cat > file.txt << EOF
    """
    # 解析重定向命令
    if '>>' in base_command:
        # 追加重定向
        parts = base_command.split('>>')
        if len(parts) != 2:
            return [base_command], False
        
        target_file = parts[1].strip()
        redirect_op = '>>'
        
    elif '>' in base_command:
        # 普通重定向
        parts = base_command.split('>')
        if len(parts) != 2:
            return [base_command], False
        
        target_file = parts[1].strip()
        redirect_op = '>'
        
    else:
        return [base_command], False
    
    # 生成单个echo命令，使用实际换行符连接多行
    if not content_lines:
        # 空内容
        commands = [f'echo "" {redirect_op} {target_file}']
    else:
        # 将所有行用实际换行符连接（而不是\n转义序列）
        combined_content = '\n'.join(content_lines)
        # 使用单引号包围，单引号内的内容完全按字面处理
        # 唯一需要特殊处理的是单引号本身：将 ' 替换为 '\''
        escaped_content = combined_content.replace("'", "'\\''")
        # 使用echo和单引号，内容完全按字面保存
        commands = [f"echo '{escaped_content}' {redirect_op} {target_file}"]
    
    return commands, True

def _translate_heredoc_pipe(base_command, content_lines):
    """
    翻译管道类型的heredoc
    例如：cat | grep pattern << EOF
    """
    # 管道模式比较复杂，暂时不实现
    # 可以考虑创建临时文件
    return [base_command], False

def _translate_heredoc_simple(base_command, content_lines):
    """
    翻译简单输入类型的heredoc
    例如：cat << EOF
    """
    # 简单模式：直接输出内容
    commands = []
    for line in content_lines:
        escaped_line = shlex.quote(line)
        commands.append(f'echo {escaped_line}')
    
    return commands, True

def preprocess_command(command):
    """
    预处理命令，检测并翻译heredoc语法
    
    Args:
        command (str): 原始命令
        
    Returns:
        tuple: (processed_commands, needs_sequential_execution)
            - processed_commands: 处理后的命令列表
            - needs_sequential_execution: 是否需要顺序执行
    """
    translated_commands, is_heredoc = translate_heredoc(command)
    
    if is_heredoc:
        return translated_commands, True  # heredoc翻译的命令需要顺序执行
    else:
        return [command], False  # 原始命令，不需要特殊处理

# 测试函数
def test_heredoc_translator():
    """测试heredoc翻译器"""
    
    # 测试用例1：基本重定向
    test1 = '''cat > test.txt << "EOF"
line 1
line 2
line 3
EOF'''
    
    result1, is_heredoc1 = translate_heredoc(test1)
    print("测试1 - 基本重定向:")
    print(f"输入: {repr(test1)}")
    print(f"输出: {result1}")
    print(f"是否heredoc: {is_heredoc1}")
    print()
    
    # 测试用例2：追加重定向
    test2 = '''cat >> append.txt << EOF
append line 1
append line 2
EOF'''
    
    result2, is_heredoc2 = translate_heredoc(test2)
    print("测试2 - 追加重定向:")
    print(f"输入: {repr(test2)}")
    print(f"输出: {result2}")
    print(f"是否heredoc: {is_heredoc2}")
    print()
    
    # 测试用例3：非heredoc命令
    test3 = 'echo "hello world"'
    
    result3, is_heredoc3 = translate_heredoc(test3)
    print("测试3 - 非heredoc命令:")
    print(f"输入: {repr(test3)}")
    print(f"输出: {result3}")
    print(f"是否heredoc: {is_heredoc3}")
    print()

if __name__ == "__main__":
    test_heredoc_translator()
