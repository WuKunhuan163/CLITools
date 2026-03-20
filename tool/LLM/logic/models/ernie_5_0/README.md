# ERNIE 5.0

**Vendor:** Baidu  
**Model Key:** `ernie-5.0`  
**Directory:** `ernie_5_0`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | True |
| Streaming | True |
| Reasoning | True |
| System Prompt | True |
| Max Context Tokens | 131072 |
| Max Output Tokens | 4096 |

## Cost

- **Free tier:** No
- **Input:** 6.0 CNY/1M tokens
- **Output:** 24.0 CNY/1M tokens

## Rate Limits

### paid
- **rpm:** 100
- **tpm:** 300000
- Pay-per-use. Top-tier model.

## Logo

- **Source:** [Wenxin (文心) color icon](https://lobehub.com/icons/wenxin)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `ernie-5.0` (canonical identifier)
- **Directory:** `ernie_5_0` = `model_key_to_dir("ernie-5.0")`
