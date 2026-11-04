"""Run with DECISIONKIT_MODEL set to an existing trained JSON model."""
import json
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from decisionkit import Engine
from functools import lru_cache
from runtime import Runtime

server=FastMCP('DecisionKit')

@lru_cache(maxsize=1)
def configured_runtime():
    return Runtime(os.environ['DECISIONKIT_CONFIG'])

@server.tool()
def decide(request: dict) -> dict:
    """Run classify/check/score/extract with configured cache, policy and budget."""
    return configured_runtime().decide(request)

@server.tool()
def report(project: str) -> dict:
    """Read estimated usage and outstanding cost reservations for a project."""
    return configured_runtime().report(project)

@server.tool()
def classify(text: str, project: str) -> dict:
    """Classify text with a configured local model; needs_review is unresolved."""
    path=Path(os.environ['DECISIONKIT_MODEL'])
    database=os.environ.get('DECISIONKIT_DB','decisionkit.sqlite3')
    engine=Engine(json.loads(path.read_text(encoding='utf-8-sig')),database)
    try: return engine.decide(text,project=project)
    finally: engine.close()

if __name__=='__main__': server.run(transport='stdio')
