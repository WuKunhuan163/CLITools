# GLM-4-Flash

**Vendor:** Zhipu AI  
**Model Key:** `glm-4-flash`  
**Directory:** `glm_4_flash`  

## Capabilities

| Feature | Value |
|---------|-------|
| Tool Calling | True |
| Vision | False |
| Streaming | True |
| Reasoning | False |
| Max Context Tokens | 128000 |
| Max Output Tokens | 4096 |

## Cost

- **Free tier:** Yes

## Rate Limits

### free
- **rpm:** 30
- **tpm:** 500000
- **max_concurrency:** 1
- **context_threshold_tokens:** 8000
- **over_threshold_concurrency_pct:** 1
- Free tier: concurrency=1, >8K context => 1% standard rate

### paid
- **rpm:** 300
- **tpm:** 10000000
- **max_concurrency:** 100
- **context_threshold_tokens:** None
- **over_threshold_concurrency_pct:** None
- Paid tier standard

## Logo

- **Source:** [Zhipu AI / ChatGLM icon](https://lobehub.com/icons/zhipu)
- **Repository:** [https://github.com/lobehub/lobe-icons](https://github.com/lobehub/lobe-icons)
- **License:** MIT

## Naming Convention

This directory follows the LLM naming convention (see `tool/LLM/logic/naming.py`):
- **Model key:** `glm-4-flash` (canonical identifier)
- **Directory:** `glm_4_flash` = `model_key_to_dir("glm-4-flash")`
