# GCS Raw Command Mode for Remote Debugging

> Use this skill when GCS commands fail, produce unexpected results, or when you need to inspect the remote Colab environment directly.

## When to Use

- A GCS command fails with unclear errors (e.g., result file timeout, unexpected output)
- You need to inspect the remote filesystem, processes, or environment variables
- You want to run an interactive or long-running command with real-time terminal output
- Standard GCS output capture is interfering with the command (e.g., commands that use stdout for progress)

## How to Use

```bash
GCS --raw '<command>'
```

Raw mode generates a minimal script that runs the command directly in the Colab terminal without stdout/stderr capture. Output appears in the Colab terminal in real time. No result file is created on Drive.

## Debugging Workflow

1. **Verify Drive mount**: `GCS --raw 'ls /content/drive/MyDrive && echo "Drive OK"'`
2. **Check remote filesystem**: `GCS --raw 'ls -la /content/drive/MyDrive/REMOTE_ROOT/tmp/'`
3. **Inspect environment**: `GCS --raw 'env | grep -i python'`
4. **Check disk space**: `GCS --raw 'df -h /content/drive'`
5. **View process list**: `GCS --raw 'ps aux | head -20'`
6. **Test network**: `GCS --raw 'curl -I https://pypi.org'`
7. **Review bg task files**: `GCS --raw 'cat /content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_bg_*.status 2>/dev/null || echo "No bg tasks"'`

## Comparison with Normal Mode

| Feature | Normal Mode | Raw Mode (`--raw`) |
|---------|-------------|-------------------|
| Output | Captured to Drive, returned locally | Shown in Colab terminal |
| Result file | Created on Drive | Not created |
| Timeout risk | Yes (Drive API polling) | No |
| Interactive | No | Yes |
| Use case | Automated workflows | Debugging, inspection |
