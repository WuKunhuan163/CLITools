# Dead Code & Duplicate Detection: Tool Research

**Date:** 2026-03-18

## Problem

The ecosystem accumulates dead code, duplicate implementations, and near-identical functions over time. Manual auditing doesn't scale. We need automated tools to detect these patterns.

## Findings

### Dead Code Detection

| Tool | Type | Notes |
|------|------|-------|
| **vulture** | Static (AST) | Most mature. Confidence levels (60-100%). Whitelist support. `pip install vulture` |
| **deadcode** | Static (AST) | Auto-fix capability. Pre-commit hooks. `pip install deadcode` |
| **dead** | Static (AST) | Lightweight. By asottile. Limited with metaclasses. |
| **Sentry Reaper** | Runtime | Instruments running code to find unused paths. Requires production traffic. |

**Recommendation:** `vulture` for static analysis (immediate), Sentry Reaper for runtime analysis (future).

### Duplicate/Clone Detection

| Tool | Approach | Notes |
|------|----------|-------|
| **duplifinder** | AST + token | Python-specific. Parallel processing. Requires Python 3.12+. |
| **CloneHunter** | Semantic (CodeBERT) | Transformer embeddings. Cross-language. Finds non-trivial clones. New (2026-02). |
| **recator** | Token + fuzzy | Multi-language. Auto-refactoring suggestions. |
| **SonarQube** | Multi-technique | Enterprise. Full CI/CD integration. Free community edition for basic duplication. |
| **jscpd** | Token-based | Multi-language. Used in many CI pipelines. npm package. |

**Recommendation:** `duplifinder` or `CloneHunter` for Python-specific analysis. SonarQube for enterprise-grade CI integration.

### Enterprise Solutions

| Platform | Duplicate Detection | Dead Code | Cost |
|----------|-------------------|-----------|------|
| **SonarQube** (Community) | Yes | Partial | Free |
| **SonarQube** (Enterprise) | Yes | Yes | Paid |
| **Sentry** | Via Reaper SDK | Yes (runtime) | Free tier + paid |
| **Codacy** | Yes | Yes | Free for OSS |
| **CodeClimate** | Yes | Partial | Free tier |

## Found Duplicates in Our Codebase

| Function | Location 1 | Location 2 | Resolution |
|----------|-----------|-----------|------------|
| `find_project_root` | `logic/_/utils/system.py` | `logic/_/utils/resolve.py` | Consolidated to `resolve.py` |
| `get_tool_module_path` | `logic/_/utils/system.py` | `logic/_/utils/resolve.py` | Consolidated to `resolve.py` |

## Next Steps

1. Add `vulture` to `TOOL --audit code` pipeline
2. Run `duplifinder` or `CloneHunter` on full codebase for comprehensive duplicate scan
3. Evaluate SonarQube Community Edition for CI integration
4. Consider adding Sentry Reaper for runtime dead code detection
