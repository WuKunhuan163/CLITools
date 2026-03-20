# ERNIE Speed 8K (Legacy)

**Vendor:** baidu  
**Model Key:** `ernie-speed-8k`  
**Directory:** `ernie_speed_8k`  
**Status:** Inactive — Legacy model. Replaced by ERNIE 4.5 Turbo 128K. qianfan SDK no longer supported.  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | False |
| Streaming | True |
| System Prompt | True |
| Max Context Tokens | 131072 |
| Max Output Tokens | 4096 |
| Reasoning | False |

## Cost

- **Free tier:** Yes

## Rate Limits

### free
- **rpm:** 10000
- **tpm:** 800000

## Logo

- **Source:** [Wenxin (文心) color icon](https://lobehub.com/icons/wenxin)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `ernie-speed-8k` (canonical identifier)
- **Directory:** `ernie_speed_8k` = `model_key_to_dir("ernie-speed-8k")`
