# AI Terminal Tools

## Quickstart

To get started quickly, run the following command in your terminal:

```bash
git clone https://github.com/WuKunhuan163/AITerminalTools.git
cd AITerminalTools
./setup.py
```

After setup, you can use the `TOOL` command to manage your AI tools.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/WuKunhuan163/AITerminalTools.git
   ```
2. **Run setup**:
   ```bash
   cd AITerminalTools
   ./setup.py
   ```
   This will create a `TOOL` command in your PATH.
3. **Install tools**:
   ```bash
   TOOL install USERINPUT
   TOOL install BACKGROUND
   ```

## Vision
赋能 AI Agents 更多实用工具，以此提高 AI 与用户共同开发的效率（用户自己也能拥有更好的工作流）。

## Mission
将这些工具制作成模块，并且拥有统一的管理机制。

## Architecture

项目采用模块化管理，核心机制由 `main.py` 和 `setup.py` 驱动。

### Core Mechanism
- **`setup.py`**: 项目部署脚本。执行后会在根目录建立一个 `TOOL` 的符号链接，指向 `main.py`。
- **`main.py`**: 工具管理入口。
  - `TOOL install <TOOL_NAME>`: 下载/安装指定工具，并创建相应的符号链接。
  - `TOOL test <TOOL_NAME>`: 测试指定工具。
- **`data/`**: 存放全局配置和 setup 过程中的相关数据。

### Tool Structure
每个工具集成在自己的文件夹中（例如 `USERINPUT/`）：
- `main.py`: 工具主入口。
- `proj/`: 工具源代码目录（原 `proj`）。
- `data/`: 工具专用数据目录（原 `_DATA`）。
- `tool.json`: 工具注册表信息（原 `AI_TOOL.json` 对应部分）。
- `README.md`: 工具详细文档。

