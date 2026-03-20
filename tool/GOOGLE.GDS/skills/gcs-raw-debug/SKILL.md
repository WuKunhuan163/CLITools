# GDS Raw Command Mode for Remote Debugging

> Use this skill when GDS commands fail, produce unexpected results, or when you need to inspect the remote Colab environment directly.

## When to Use

- A GDS command fails with unclear errors (e.g., result file timeout, unexpected output)
- You need to inspect the remote filesystem, processes, or environment variables
- You want to run an interactive or long-running command with real-time terminal output
- Standard GDS output capture is interfering with the command (e.g., commands that use stdout for progress)

## How to Use

```bash
GDS --raw '<command>'
```

Raw mode generates a minimal script that runs the command directly in the Colab terminal without stdout/stderr capture. Output appears in the Colab terminal in real time. No result file is created on Drive.

## Debugging Workflow

1. **Verify Drive mount**: `GDS --raw 'ls /content/drive/MyDrive && echo "Drive OK"'`
2. **Check remote filesystem**: `GDS --raw 'ls -la /content/drive/MyDrive/REMOTE_ROOT/tmp/'`
3. **Inspect environment**: `GDS --raw 'env | grep -i python'`
4. **Check disk space**: `GDS --raw 'df -h /content/drive'`
5. **View process list**: `GDS --raw 'ps aux | head -20'`
6. **Test network**: `GDS --raw 'curl -I https://pypi.org'`
7. **Review bg task files**: `GDS --raw 'cat /content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_bg_*.status 2>/dev/null || echo "No bg tasks"'`

## Comparison with Normal Mode

| Feature | Normal Mode | Raw Mode (`--raw`) |
|---------|-------------|-------------------|
| Output | Captured to Drive, returned locally | Shown in Colab terminal |
| Result file | Created on Drive | Not created |
| Timeout risk | Yes (Drive API polling) | No |
| Interactive | No | Yes |
| Use case | Automated workflows | Debugging, inspection |
