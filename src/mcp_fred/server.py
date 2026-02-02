#!/usr/bin/env python3
"""
MCP Server for FRED (Federal Reserve Economic Data)
Technical interface for macroeconomic data retrieval.
"""

import argparse
import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


class FredClient:
    """
    Cliente técnico para la obtención de series temporales de FRED.
    API: https://fred.stlouisfed.org/docs/api/fred/
    """

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_series(self, series_id: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Obtiene observaciones de una serie específica.

        Identidad: Datos_Observados = f(Series_ID, API_Key)
        Restricción: Requiere conexión HTTP 200 y JSON válido.
        """
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

            # Validación de estructura de datos
            if 'observations' not in data:
                return pd.DataFrame()

            df = pd.DataFrame(data['observations'])
            # Conversión de tipos para asegurar integridad matemática
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')

            # Eliminación de valores nulos para mantener consistencia en el cálculo
            return df.dropna(subset=['value'])

        except requests.exceptions.RequestException as e:
            # Reporte explícito de falla en acceso a datos
            print(f"Error de acceso a datos: {e}")
            return pd.DataFrame()


# Initialize FRED client
api_key = os.environ.get("FRED_API_KEY", "")
client = FredClient(api_key) if api_key else None

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
    if not client or not client.api_key:
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

        df = client.get_series(series_id, params)

        if df.empty:
            return [TextContent(
                type="text",
                text=f"No data retrieved for series '{series_id}'. "
                     "Verify series ID validity or connectivity."
            )]

        # Get last N observations
        df = df.tail(limit)

        # Format output
        output = f"Series: {series_id}\n"
        output += f"Observations: {len(df)}\n"
        output += f"Period: {df['date'].min().strftime('%Y-%m-%d')} to "
        output += f"{df['date'].max().strftime('%Y-%m-%d')}\n\n"
        output += df.to_string(index=False)

        return [TextContent(type="text", text=output)]

    elif name == "get_series_info":
        series_id = arguments.get("series_id")

        url = "https://api.stlouisfed.org/fred/series"
        params = {
            "series_id": series_id,
            "api_key": client.api_key,
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
            output += f"Notes: {series.get('notes', 'N/A')[:200]}..."

            return [TextContent(type="text", text=output)]

        except requests.exceptions.RequestException as e:
            return [TextContent(
                type="text",
                text=f"Error retrieving series info: {e}"
            )]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
