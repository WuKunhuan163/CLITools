# ERNIE 4.5 8K

**Vendor:** Baidu  
**Model Key:** `ernie-4.5-8k`  
**API Model ID:** `ernie-4.5-8k-preview`  
**Directory:** `ernie_4_5_8k`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | True |
| Streaming | True |
| Reasoning | False |
| System Prompt | True |
| Max Context Tokens | 8192 |
| Max Output Tokens | 4096 |

## Cost

- **Free tier:** No
- **Input:** 4.0 CNY/1M tokens
- **Output:** 16.0 CNY/1M tokens

## Rate Limits

### paid
- **rpm:** 300
- **tpm:** 500000
- Pay-per-use. Also supports search enhancement.

## Logo

- **Source:** [Wenxin (文心) color icon](https://lobehub.com/icons/wenxin)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `ernie-4.5-8k` (canonical identifier)
- **Directory:** `ernie_4_5_8k` = `model_key_to_dir("ernie-4.5-8k")`
- **API ID:** `ernie-4.5-8k-preview` (what the vendor API expects)
