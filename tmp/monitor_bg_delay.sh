#!/bin/bash

TASK_ID="1763975884_2566"
START_TIME=$(date +%H:%M:%S.%N | cut -c1-12)

echo "="
echo "🔍 监测--bg任务访问延迟"
echo "任务ID: $TASK_ID"
echo "本地启动监测: $START_TIME"
echo "="
echo ""
echo "每2秒查询一次，共查询8次"
echo ""
printf "%-8s %-15s %-10s %-50s %-20s\n" "查询次数" "本地时间" "日志大小" "最新行" "延迟分析"
echo "----------------------------------------------------------------------------------------------------"

for i in {1..8}; do
    sleep 2
    ACCESS_TIME=$(date +%H:%M:%S.%N | cut -c1-12)
    
    # 通过GDS查询日志
    LOG_OUTPUT=$(cd /Users/wukunhuan/.local/bin && python3 GOOGLE_DRIVE.py --shell "--bg --log $TASK_ID" 2>&1 | tail -1)
    
    # 提取最后一行内容（如果有的话）
    if echo "$LOG_OUTPUT" | grep -q "Line"; then
        LAST_LINE=$(echo "$LOG_OUTPUT" | tail -1)
        LOG_SIZE="有内容"
        
        # 尝试解析时间戳
        REMOTE_TIME=$(echo "$LAST_LINE" | grep -oE "[0-9]{2}:[0-9]{2}:[0-9]{2}")
        
        if [ -n "$REMOTE_TIME" ]; then
            DELAY="可见(远端: $REMOTE_TIME)"
        else
            DELAY="无法解析时间"
        fi
    else
        LAST_LINE="(空或错误)"
        LOG_SIZE="0"
        DELAY="还未同步"
    fi
    
    printf "%-8s %-15s %-10s %-50s %-20s\n" "第${i}次" "$ACCESS_TIME" "$LOG_SIZE" "${LAST_LINE:0:48}" "$DELAY"
done

echo ""
echo "="
echo "📊 结论"
echo "="
echo "观察第1-2次查询："
echo "  • 如果立即可见：说明访问延迟小，不是问题"
echo "  • 如果多次才可见：说明存在访问/同步延迟"

