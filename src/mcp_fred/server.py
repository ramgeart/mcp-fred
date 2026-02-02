#!/usr/bin/env python3
"""
MCP Server for FRED (Federal Reserve Economic Data)
Technical interface for macroeconomic data retrieval.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# MCP imports only - keep startup fast
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Global client storage (initialized lazily)
_client = None
_api_key = None


def get_client():
    """Lazy initialization of FRED client."""
    global _client, _api_key
    if _client is None:
        _api_key = os.environ.get("FRED_API_KEY", "")
        if _api_key:
            _client = FredClient(_api_key)
    return _client


class FredClient:
    """
    Cliente técnico para la obtención de series temporales de FRED.
    API: https://fred.stlouisfed.org/docs/api/fred/
    """

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_series(self, series_id: str, params: Optional[Dict] = None) -> list:
        """
        Obtiene observaciones de una serie específica.
        Lazy import of requests and pandas.
        """
        import requests

        query_params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json"
        }

        if params:
            query_params.update(params)

        try:
            response = requests.get(self.BASE_URL, params=query_params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'observations' not in data:
                return []

            # Return raw observations without pandas
            observations = []
            for obs in data['observations']:
                try:
                    value = float(obs['value'])
                    observations.append({
                        'date': obs['date'],
                        'value': value
                    })
                except (ValueError, TypeError):
                    continue

            return observations

        except Exception as e:
            return [{"error": str(e)}]


# MCP Server
app = Server("mcp-fred")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available FRED tools."""
    return [
        Tool(
            name="get_series",
            description="Retrieve observations from a FRED series. "
                        "Returns time series data with date and value columns. "
                        "Common series IDs: FEDFUNDS (Fed Funds Rate), "
                        "GDP (Gross Domestic Product), CPIAUCSL (CPI Inflation), "
                        "UNRATE (Unemployment Rate), WALCL (Fed Balance Sheet)",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "string",
                        "description": "FRED series identifier (e.g., FEDFUNDS, GDP, CPIAUCSL)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of observations to return",
                        "default": 100
                    }
                },
                "required": ["series_id"]
            }
        ),
        Tool(
            name="get_series_info",
            description="Get information about a FRED series including title, "
                        "frequency, units, and notes",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "string",
                        "description": "FRED series identifier"
                    }
                },
                "required": ["series_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute FRED tools."""
    client = get_client()

    if not client or not _api_key:
        return [TextContent(
            type="text",
            text="ERROR: FRED_API_KEY environment variable not set"
        )]

    if name == "get_series":
        series_id = arguments.get("series_id")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        limit = arguments.get("limit", 100)

        params = {}
        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date

        observations = client.get_series(series_id, params)

        if not observations:
            return [TextContent(
                type="text",
                text=f"No data retrieved for series '{series_id}'. "
                     "Verify series ID validity or connectivity."
            )]

        if len(observations) > 0 and "error" in observations[0]:
            return [TextContent(
                type="text",
                text=f"Error: {observations[0]['error']}"
            )]

        # Get last N observations
        observations = observations[-limit:] if len(observations) > limit else observations

        # Format output without pandas
        output = f"Series: {series_id}\n"
        output += f"Observations: {len(observations)}\n"
        if observations:
            dates = [obs['date'] for obs in observations]
            output += f"Period: {min(dates)} to {max(dates)}\n\n"
            output += "date       | value\n"
            output += "-----------+-------\n"
            for obs in observations:
                output += f"{obs['date']} | {obs['value']}\n"

        return [TextContent(type="text", text=output)]

    elif name == "get_series_info":
        import requests

        series_id = arguments.get("series_id")

        url = "https://api.stlouisfed.org/fred/series"
        params = {
            "series_id": series_id,
            "api_key": _api_key,
            "file_type": "json"
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'seriess' not in data or not data['seriess']:
                return [TextContent(
                    type="text",
                    text=f"Series '{series_id}' not found"
                )]

            series = data['seriess'][0]
            output = f"Series Information: {series_id}\n"
            output += f"Title: {series.get('title', 'N/A')}\n"
            output += f"Frequency: {series.get('frequency', 'N/A')}\n"
            output += f"Units: {series.get('units', 'N/A')}\n"
            output += f"Seasonal Adjustment: {series.get('seasonal_adjustment', 'N/A')}\n"
            output += f"Last Updated: {series.get('last_updated', 'N/A')}\n"
            notes = series.get('notes', 'N/A')
            output += f"Notes: {notes[:200]}{'...' if len(notes) > 200 else ''}"

            return [TextContent(type="text", text=output)]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error retrieving series info: {e}"
            )]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run MCP server."""
    # Use stderr for logging to avoid interfering with stdio protocol
    print("Starting MCP FRED server...", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        print("Server initialized, running...", file=sys.stderr)
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
