#!/bin/bash

# 测试bash如何展开路径

test_command='echo "~" > ~/Desktop/test.txt'

echo "原始命令："
echo "$test_command"
echo

# 使用set -x来查看bash如何展开命令
echo "Bash展开结果（使用set -x）："
bash -x -c "$test_command" 2>&1 | grep '^+'

echo

# 使用eval echo来展开命令字符串（但不执行）
echo "展开后的命令（使用eval）："
eval "echo $test_command"

