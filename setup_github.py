#!/usr/bin/env python3
"""Script to initialize git repo and push to GitHub."""

import subprocess
import os
import sys

def run_cmd(cmd, cwd=None):
    """Run command and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result

def main():
    repo_dir = "/mnt/c/Users/SebastianCabrera/OneDrive - Silicon Valley SAS/new_world/mcp-fred"
    
    print("Initializing git repository...")
    run_cmd("git init", cwd=repo_dir)
    
    print("Adding files...")
    run_cmd("git add .", cwd=repo_dir)
    
    print("Creating initial commit...")
    run_cmd('git commit -m "Initial commit: MCP server for FRED"', cwd=repo_dir)
    
    print("Creating GitHub repository with gh cli...")
    result = run_cmd(
        "gh repo create mcp-fred --public --source=. --remote=origin --push",
        cwd=repo_dir
    )
    
    if result.returncode == 0:
        print("\n✅ Repository created and pushed successfully!")
        print("You can now install it with:")
        print('  uvx --from git+https://github.com/YOUR_USERNAME/mcp-fred mcp-fred')
    else:
        print("\n❌ Failed to create repository. Make sure gh cli is authenticated.")
        print("Run: gh auth login")
        sys.exit(1)

if __name__ == "__main__":
    main()
