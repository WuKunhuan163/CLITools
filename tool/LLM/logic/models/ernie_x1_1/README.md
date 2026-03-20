# ERNIE X1.1 (Preview)

**Vendor:** Baidu  
**Model Key:** `ernie-x1.1`  
**API Model ID:** `ernie-x1.1-preview`  
**Directory:** `ernie_x1_1`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | False |
| Streaming | True |
| Reasoning | True |
| System Prompt | True |
| Max Context Tokens | 131072 |
| Max Output Tokens | 4096 |

## Cost

- **Free tier:** No
- **Input:** 1.0 CNY/1M tokens
- **Output:** 4.0 CNY/1M tokens

## Rate Limits

### paid
- **rpm:** 200
- **tpm:** 400000
- Pay-per-use. Latest reasoning model. Supports search enhancement.

## Logo

- **Source:** [Wenxin (文心) color icon](https://lobehub.com/icons/wenxin)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `ernie-x1.1` (canonical identifier)
- **Directory:** `ernie_x1_1` = `model_key_to_dir("ernie-x1.1")`
- **API ID:** `ernie-x1.1-preview` (what the vendor API expects)
