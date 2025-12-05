# Extract Command Test Files

## Test Archive Location

**Location:** `~/tmp/big_project.tar.gz` (on remote/Google Drive)

**Structure:**
```
big_project/
├── module1/ (10 files: file1.txt - file10.txt)
├── module2/ (10 files: file1.txt - file10.txt)
├── module3/ (10 files: file1.txt - file10.txt)
├── module4/ (10 files: file1.txt - file10.txt)
└── module5/ (10 files: file1.txt - file10.txt)
Total: 50 files
```

##使用方式

### 首次运行
```bash
./GOOGLE_DRIVE --shell extract ~/tmp/big_project.tar.gz --transfer-batch 2
```
生成的 task_id 格式：`big_project_XXXXXXXX`

### 恢复进度
```bash
./GOOGLE_DRIVE --shell extract --progress-id big_project_XXXXXXXX --transfer-batch 2
```

### 或者指定归档路径恢复
```bash
./GOOGLE_DRIVE --shell extract ~/tmp/big_project.tar.gz --progress-id big_project_XXXXXXXX --transfer-batch 2
```

## Extract 流程

1. **首次运行**：
   - 从 `~/tmp/big_project.tar.gz` 复制到 `/tmp/` 并解压到 `/tmp/gds_extract_<task_id>/`
   - 创建指纹文件 `~/tmp/extract_progress_<task_id>.json`
   - 开始传输

2. **恢复进度**：
   - 加载指纹文件 `~/tmp/extract_progress_<task_id>.json`
   - 检查 `/tmp/gds_extract_<task_id>/` 是否存在且非空
   - 如果不存在或为空，从原归档路径重新复制并解压
   - 只传输剩余文件

3. **Remount后**：
   - `/tmp` 目录会被清空
   - 归档文件需要从 `~/tmp/` 重新复制到 `/tmp/`
   - 解压目录需要重新创建

## 重新创建测试文件

```bash
./GOOGLE_DRIVE --shell --raw-command "
mkdir -p ~/tmp && \
cd ~/tmp && \
rm -rf big_project big_project.tar.gz && \
mkdir -p big_project/module1 big_project/module2 big_project/module3 big_project/module4 big_project/module5 && \
for i in {1..10}; do echo \"file\$i\" > big_project/module1/file\$i.txt; done && \
for i in {1..10}; do echo \"file\$i\" > big_project/module2/file\$i.txt; done && \
for i in {1..10}; do echo \"file\$i\" > big_project/module3/file\$i.txt; done && \
for i in {1..10}; do echo \"file\$i\" > big_project/module4/file\$i.txt; done && \
for i in {1..10}; do echo \"file\$i\" > big_project/module5/file\$i.txt; done && \
tar -czf big_project.tar.gz big_project && \
echo '✅ Created test archive in ~/tmp' && \
ls -lh ~/tmp/big_project.tar.gz
"
```

