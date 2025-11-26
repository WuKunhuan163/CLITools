#!/bin/bash

LOG_FILE="/tmp/gds_check_result.txt"
REMOTE_LOG="/content/drive/MyDrive/REMOTE_ROOT/tmp/fast_task.log"

echo "======================================================================"
echo "🔍 监测远端任务访问延迟（每5秒检查一次）"
echo "======================================================================"
echo "远端日志: $REMOTE_LOG"
echo "检查开始: $(date +%H:%M:%S)"
echo ""
echo "格式: 本地时间 | 远端最新时间"
echo "----------------------------------------------------------------------"

for i in {1..20}; do
    # 本地时间
    LOCAL_TIME=$(date +%H:%M:%S)
    
    # 通过GDS读取远端最后一行，重定向到本地
    cd /Users/wukunhuan/.local/bin && python3 GOOGLE_DRIVE.py --shell "tail -1 $REMOTE_LOG" > $LOG_FILE 2>&1
    
    # 提取远端时间（最后一行）
    REMOTE_TIME=$(cat $LOG_FILE | tail -1 | tr -d '\n\r' | head -c 15)
    
    # 输出对比
    echo "$LOCAL_TIME | $REMOTE_TIME"
    
    # 等待5秒
    sleep 5
done

echo ""
echo "======================================================================"
echo "✅ 监测完成"
echo "======================================================================"
echo ""
echo "分析："
echo "  • 如果本地时间和远端时间相近（差值<5秒）：访问实时"
echo "  • 如果差值>10秒：存在同步延迟"

