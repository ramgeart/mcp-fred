#!/bin/bash
set -e

# Configurar git
git init
git add .
git commit -m "Initial commit: MCP server for FRED"

# Crear repo en GitHub con gh cli
gh repo create mcp-fred --public --source=. --remote=origin --push

echo "Repositorio creado y código pusheado exitosamente"
