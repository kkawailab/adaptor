# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the e-Stat API Adaptor, a Python library that wraps Japan's government statistics portal (e-Stat) API. The project has been recently modernized from Python 2 to Python 3.7+, with significant security improvements including removal of command injection vulnerabilities and addition of input validation.

## Environment Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

Required: Python 3.7+. Python 2 is **not** supported.

### Initial Setup for Development
After installing dependencies, you need an e-Stat API key (appId) from https://www.e-stat.go.jp/

The library requires certain directories which are auto-created on first run:
- `data-cache/` - CSV cache storage
- `dictionary/` - Index files for search
- `dictionary/detail/` - N-gram search indices
- `tmp/` - Temporary JSON downloads

## Running the Application

### Flask Web Server
```bash
# Edit www/run.py to set your appId and directory path
python www/run.py
```

The server provides REST endpoints at `/<appId>/<command>/<id>.<format>`:
- GET data: `/<appId>/get/0000030001.csv`
- Search: `/<appId>/search/法人.json`
- Merge: `/<appId>/merge/0000030001,0000030002/area.csv?aggregate=mean`

### Command-line Usage
```python
import sys
sys.path.append('./python')
import e_Stat_API_Adaptor

eStatAPI = e_Stat_API_Adaptor.e_Stat_API_Adaptor({
    'appId': 'your_app_id',
    'limit': '10000',
    'next_key': True,
    'directory': './',
    'ver': '2.0'
})

# First-time index creation
eStatAPI.load_all_ids()
eStatAPI.build_statid_index()
```

## Code Architecture

### Core Data Flow

The library follows a multi-stage data pipeline:

1. **API Fetch** (`get_all_data`) → Downloads raw JSON from e-Stat API
   - Handles pagination via `next_key` mechanism
   - Caches JSON in `tmp/` as `{appId}.{statsId}.{position}.json`
   - Automatically retries on failure and cleans up failed downloads

2. **JSON→CSV Conversion** (`convert_raw_json_to_csv`) → Transforms API response
   - Merges multiple paginated JSON files
   - Extracts class mappings from `CLASS_INF` for human-readable column names
   - Writes 3-row CSV: [1] human names, [2] API keys, [3+] data rows
   - Cleans up temp JSON files after successful conversion

3. **CSV Caching** → All processed data stored in `data-cache/{statsId}.csv`
   - Cache is persistent across sessions
   - **Important**: Cache doesn't auto-expire; manually delete CSVs if e-Stat updates data

4. **Output Formatting** (`get_output`) → Converts to requested format
   - `csv` - Raw CSV with row 2 (keys) stripped
   - `rjson` - Row-oriented JSON (array of objects)
   - `cjson` - Column-oriented JSON (object with arrays)

### Search Index System

Two-tier search system for finding statistical tables:

1. **Basic Index** (`build_statid_index`)
   - Format: `{id}-{name}-{date}-{org}-{category}.dic`
   - Searchable via `search_id()` with grep-like functionality
   - Returns CSV with statsDataId and metadata

2. **Detailed N-gram Index** (`build_detailed_index`)
   - Creates per-table files in `dictionary/detail/`
   - 2-gram tokenization of STATISTICS_NAME and TITLE fields
   - Used for fuzzy/partial matching via `search_detailed_index()`
   - Can promote results to user index with `create_user_index_from_detailed_index()`

### Data Aggregation

The `merge_data()` method:
- Accepts comma-separated stats IDs: `'0000030001,0000030002'`
- Downloads missing data automatically
- Uses pandas for joining and aggregation (sum, min, max, median, count, var, std, mean)
- Column renaming: `$` becomes `${statsId}` to distinguish sources

### Security Architecture

**Critical security improvements** in Python 3 version:

1. **Input Validation** - All user inputs validated before use:
   - `_validate_stats_id()` - Ensures stats IDs are numeric only (prevents path traversal)
   - `_validate_query()` - Blocks shell metacharacters `[;&|`$\n\r]` in search queries

2. **No Shell Execution** - Eliminated `subprocess.check_output(cmd, shell=True)`
   - File operations use native Python `open()`, `Path.glob()`, etc.
   - Where shell commands remain, inputs are validated first

3. **Safe Temp Files** - Uses `tempfile.NamedTemporaryFile()` in www/run.py
   - Prevents race conditions and predictable filenames
   - Automatic cleanup on exceptions

## File Roles

### python/e_Stat_API_Adaptor.py
Main library class. Single class `e_Stat_API_Adaptor` with all functionality.

**Key internal methods** (not documented in README):
- `_ensure_directories()` - Auto-creates required dirs on init
- `_validate_stats_id()`, `_validate_query()` - Security validation
- `_cleanup_temp_files()` - Removes orphaned JSON files from failed downloads
- `build_uri()` - Constructs e-Stat API URLs with query params

**Important**: Uses `logging` module - logs show API calls, file operations, errors. Set `logging.basicConfig(level=logging.DEBUG)` for troubleshooting.

### www/run.py
Flask web service with three routes:
- `/<appId>/search/<q>.<ext>` - Search index
- `/<appId>/<cmd>/<id>.<ext>` - Get/head/tail data (cmd ∈ {get, head, tail})
- `/<appId>/merge/<ids>/<group_by>.<ext>` - Merge multiple stats

**Note**: `appId` is dynamic per-request (not fixed at init), allowing multi-tenant usage.

### python/examples.py
Template file with commented-out examples. Users should copy and uncomment for testing.

### python/get_csv.py and install.py
**WARNING**: These files still use Python 2 syntax (`print` statements without parentheses). They were not part of the Python 3 migration. If users attempt to run them, they will fail with syntax errors. Consider migrating these files if they're actively used.

## Common Patterns

### Adding New Aggregation Methods
Modify `merge_data()` in e_Stat_API_Adaptor.py:
```python
elif aggregate == 'new_method':
    data = data.groupby(group_cols).new_method()
```
Also update README.md aggregation table and www/run.py docstring.

### Changing CSV Format
The 3-row CSV format is fundamental:
- Row 1: Human-readable column names (from CLASS_INF)
- Row 2: API keys (e.g., "area", "cat01")
- Row 3+: Data values

If modifying, update:
- `convert_raw_json_to_csv()` - CSV writing
- `get_csv()` - Row 2 stripping logic
- `get_output()` - CSV→JSON parsing (assumes row 1 = headers)

### Error Handling Philosophy
- Use `logger.error()` for all errors, not silent `pass`
- Raise exceptions up to caller (let Flask or user code handle)
- Clean up temp files in `except` blocks before raising
- Log successful operations at `INFO` level for audit trail

## Testing Notes

**No test suite exists.** Manual testing workflow:

1. Set valid appId in examples.py or run.py
2. Test index creation:
   ```python
   eStatAPI.load_all_ids()
   eStatAPI.build_statid_index()
   ```
3. Test data download with known stats ID (e.g., '0000030001' for census data)
4. Verify cache: `ls data-cache/` should show CSV files
5. For web API, use curl:
   ```bash
   curl http://localhost:5000/{appId}/get/0000030001.csv
   ```

## Known Limitations

1. **Cache Staleness**: No automatic cache invalidation. Users must manually delete `data-cache/*.csv` if e-Stat updates data.

2. **Large Datasets**: `next_key=True` downloads entire datasets into memory during JSON→CSV conversion. Very large stats (100k+ rows) may cause memory issues.

3. **Character Encoding**: Assumes all e-Stat data is UTF-8. Encoding errors unlikely but not handled gracefully.

4. **API Rate Limiting**: No built-in rate limiting or retry logic for 429 responses from e-Stat.

5. **Concurrent Requests**: Flask default server is single-threaded. For production, use WSGI server (gunicorn/uWSGI).

## Migration from Python 2

See MIGRATION.md for full details. Key points:

- `urllib2` → `requests` for HTTP
- `StringIO` → `io.StringIO`
- All `print` statements → `print()` functions
- Files opened with explicit `encoding='utf-8'`
- `.bak` files contain original Python 2 code

If working on code that interfaces with old Python 2 scripts, note incompatibilities in subprocess calls and file I/O.
