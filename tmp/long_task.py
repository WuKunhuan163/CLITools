#!/usr/bin/env python3
import time
from datetime import datetime

log_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/long_task.log"

with open(log_file, "w") as f:
    start_msg = f"TASK_START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n"
    f.write(start_msg)
    f.flush()
    
    print(start_msg.strip())
    
    for i in range(1, 3601):  # 3600秒
        t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{i:04d}/3600] {t}\n"
        f.write(line)
        f.flush()
        time.sleep(1)
    
    end_msg = f"TASK_END: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n"
    f.write(end_msg)
    f.flush()
    
    print(end_msg.strip())

