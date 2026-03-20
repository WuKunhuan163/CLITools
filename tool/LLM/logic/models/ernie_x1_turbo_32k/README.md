# ERNIE X1 Turbo 32K

**Vendor:** Baidu  
**Model Key:** `ernie-x1-turbo-32k`  
**Directory:** `ernie_x1_turbo_32k`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | False |
| Streaming | True |
| Reasoning | True |
| System Prompt | True |
| Max Context Tokens | 32768 |
| Max Output Tokens | 4096 |

## Cost

- **Free tier:** No
- **Input:** 1.0 CNY/1M tokens
- **Output:** 4.0 CNY/1M tokens

## Rate Limits

### paid
- **rpm:** 300
- **tpm:** 500000
- Pay-per-use. Deep reasoning model, budget-friendly.

## Logo

- **Source:** [Wenxin (文心) color icon](https://lobehub.com/icons/wenxin)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `ernie-x1-turbo-32k` (canonical identifier)
- **Directory:** `ernie_x1_turbo_32k` = `model_key_to_dir("ernie-x1-turbo-32k")`
