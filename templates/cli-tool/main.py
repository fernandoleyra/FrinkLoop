"""
CLI Tool project — starter scaffold (using Typer).
Agents will implement commands and logic based on the BRIEF.
"""

import typer
from cli.commands import register_commands

app = typer.Typer(help="CLI tool — built by Agent OS")
register_commands(app)

if __name__ == "__main__":
    app()
