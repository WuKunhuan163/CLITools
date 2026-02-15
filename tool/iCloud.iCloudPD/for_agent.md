# Developer Guidelines: iCloudPD

## 1. Architecture Overview
`iCloudPD` is a high-performance downloader built on top of `pyicloud`. It uses a 4-stage pipeline:
1. **Auth**: Session-aware authentication (GUI or CLI).
2. **Scan**: Incremental metadata harvesting into `photos_cache.json`.
3. **Filter**: Local ID selection based on user criteria.
4. **Gather**: Object reconstruction using CloudKit `lookup`.
5. **Download**: Parallel streaming downloads with internal retries.

## 2. Key Optimizations

### CloudKit Lookup
Never use the library iterator (`album.all`) to find specific photo objects if you already have their IDs. Instead, use the `/lookup` POST endpoint:
```python
# batches of 100
query = {"records": [{"recordName": rid} for rid in batch], "zoneID": zone_id}
resp = session.post(f"{base_url}/lookup", json=query)
```
This is **60x faster** than scanning for 100k+ assets.

### Direction Enum
In the current `pyicloud` environment:
- `DirectionEnum.ASCENDING`: Returns **NEWEST** assets first (chronologically descending).
- `DirectionEnum.DESCENDING`: Returns **OLDEST** assets first (chronologically ascending).
Ensure `ASCENDING` is used for "incremental from latest" scanning.

### Path Resolution
The tool automatically handles filename collisions by checking the `used_paths` set during task generation. If a collision is detected, a numeric suffix is appended.

## 3. Data Structure
- **Cache**: `data/scan/<apple_id>/photos_cache.json` uses a nested structure: `{"Year": {"Month": {"Day": [assets]}}}`.
- **Session**: `data/session/<apple_id>/session.pkl` stores the raw requests cookie jar.

## 4. UI Conventions
- **Progress**: Always use `ProgressTuringMachine` for sequential stages and `ParallelWorkerPool` for the download phase.
- **Silent Success**: Use `success_status="\r\033[K", success_name=" "` for stages that should be erased on completion (e.g., Gathering).
- **Styling**: `Reused session` and `Found` should be **BOLD DEFAULT**. `iCloud` during auth should be **BOLD GREEN**.

## 5. Testing
Temporary scripts should be placed in the project-root `tmp/`. Unit tests go in `test/` or `tool/iCloud/tool/iCloudPD/test/` following the `test_xx_name.py` pattern.

