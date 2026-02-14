# iCloudPD Subtool

iCloud Photo Downloader for automatically downloading and organizing photos.

## Usage
```bash
iCloudPD --since 2023-01-01 --before 2023-12-31 --output ./my_photos
```

## Features
- **Date filtering**: `--since` and `--before` parameters.
- **Metadata caching**: Generates a local JSON cache for fast rescheduling.
- **Organization**: Automatically groups photos by date (`yyyy-mm-dd/` folders).
- **Subtool design**: Uses the parent `iCloud` tool for secure authentication.

