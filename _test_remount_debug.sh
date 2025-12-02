#!/bin/bash
# 临时测试脚本：连续调用5个GDS echo，观察remount flag的行为

echo "=========================================="
echo "开始测试remount flag行为"
echo "=========================================="

for i in {1..5}; do
    echo ""
    echo "---------- GDS echo 调用 #$i ----------"
    GDS echo "Test message $i"
    echo "---------- 完成 #$i ----------"
    sleep 1
done

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="

