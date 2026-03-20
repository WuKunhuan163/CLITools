# CHARTCUBE — Agent Reference

## Status: CDMCP ACCEPTABLE (ToS silent)

DOM automation disabled. Only session/auth state checking via CDMCP remains.
Use AntV Libraries (code generation alternative) for all operations.

## ToS Compliance

**Risk Level: LOW RISK**

ChartCube (AntV) ToS is silent on automation. No official API exists.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS restricts automation | **Silent** |
| Official API exists | **Yes** (AntV Libraries (code generation alternative)) |
| Decision | **Use official API** |

## Migration: AntV Libraries (code generation alternative)

**Documentation**: https://antv.antgroup.com/

### Features

- G2 (statistical charts)
- G6 (graph visualization)
- S2 (pivot tables)
- L7 (geospatial)
- Direct code generation instead of UI automation

### Setup

1. npm install @antv/g2 (or g6, s2, l7)
1. Generate chart code directly instead of using ChartCube UI
