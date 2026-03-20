# ERNIE 4.5 Turbo 128K

**Vendor:** Baidu  
**Model Key:** `ernie-4.5-turbo-128k`  
**Directory:** `ernie_4_5_turbo_128k`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | False |
| Streaming | True |
| Reasoning | False |
| System Prompt | True |
| Max Context Tokens | 131072 |
| Max Output Tokens | 4096 |

## Cost

- **Free tier:** No
- **Input:** 0.8 CNY/1M tokens
- **Output:** 3.2 CNY/1M tokens

## Rate Limits

### paid
- **rpm:** 300
- **tpm:** 500000
- Pay-per-use. Cache hit: 0.2 CNY/M input.

## Logo

- **Source:** [Wenxin (文心) color icon](https://lobehub.com/icons/wenxin)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `ernie-4.5-turbo-128k` (canonical identifier)
- **Directory:** `ernie_4_5_turbo_128k` = `model_key_to_dir("ernie-4.5-turbo-128k")`
