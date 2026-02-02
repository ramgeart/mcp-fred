# MCP Server for FRED

MCP server for accessing Federal Reserve Economic Data (FRED).

## Installation

### Using uvx (recommended)

```bash
uvx --from git+https://github.com/YOUR_USERNAME/mcp-fred mcp-fred
```

### Environment Variables

- `FRED_API_KEY`: Required. Get your API key at https://fred.stlouisfed.org/docs/api/api_key.html

## Usage

### With Claude Desktop

Add to your `claude_desktop_config.json` or `mcp_config.json`:

```json
{
  "fred": {
    "command": "/home/zkadmin/.local/bin/uvx",
    "args": [
      "--from",
      "git+https://github.com/YOUR_USERNAME/mcp-fred",
      "mcp-fred"
    ],
    "env": {
      "FRED_API_KEY": "your_api_key_here"
    },
    "disabled": false
  }
}
```

## Available Tools

- `get_series`: Retrieve observations from a FRED series
  - Parameters: `series_id`, `start_date`, `end_date`, `limit`
  - Common series IDs: FEDFUNDS, GDP, CPIAUCSL, UNRATE, WALCL

- `get_series_info`: Get metadata about a FRED series
  - Parameters: `series_id`

## Examples

```python
# Get Federal Funds Rate
get_series(series_id="FEDFUNDS", limit=10)

# Get CPI data for specific period
get_series(series_id="CPIAUCSL", start_date="2023-01-01", end_date="2024-01-01")
```

## License

MIT
