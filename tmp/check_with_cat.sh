#!/bin/bash

REMOTE_LOG="/content/drive/MyDrive/REMOTE_ROOT/tmp/fast_task.log"
LOCAL_TEMP="/tmp/gds_cat_result.txt"

echo "======================================================================"
echo "🔍 用cat监测访问延迟（每5秒检查）"
echo "======================================================================"
echo ""

for i in {1..20}; do
    LOCAL_TIME=$(date +%H:%M:%S)
    
    # 用cat读取并重定向到本地文件
    cd /Users/wukunhuan/.local/bin && python3 GOOGLE_DRIVE.py --shell "cat $REMOTE_LOG" > $LOCAL_TEMP 2>&1
    
    # 提取最后一行（远端时间戳）
    REMOTE_TIME=$(tail -1 $LOCAL_TEMP | head -c 15)
    
    # 输出：本地时间 | 远端时间
    echo "$LOCAL_TIME | $REMOTE_TIME"
    
    sleep 5
done

echo ""
echo "✅ 完成"

