"""Run separately using a Python environment with requirements-mcp installed."""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from decisionkit import train
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory); model=root/'model.json'
        model.write_text(json.dumps(train([{'text':'refund payment','label':'billing'},{'text':'crash broken','label':'technical'}])))
        config=root/'config.json'; config.write_text(json.dumps({'database':'pipeline.sqlite3','local_model':'model.json','local_criteria':{'billing':'money','technical':'software'}}))
        params=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).resolve().parents[1]/'mcp_server.py')],env={**os.environ,'DECISIONKIT_CONFIG':str(config),'DECISIONKIT_MODEL':str(model),'DECISIONKIT_DB':str(root/'db.sqlite3')})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                tools=await session.list_tools()
                assert any(t.name=='classify' for t in tools.tools)
                result=await session.call_tool('classify',{'text':'refund payment','project':'test'})
                assert not result.isError
                data=json.loads(result.content[0].text)
                assert data['result']['label']=='billing'
                result=await session.call_tool('decide',{'request':{'text':'refund payment','project':'test','criteria':{'billing':'money','technical':'software'}}})
                assert not result.isError
                assert json.loads(result.content[0].text)['value']=='billing'
                result=await session.call_tool('report',{'project':'test'})
                assert not result.isError
                print('MCP initialization, discovery, legacy classify, pipeline decide and report passed')

if __name__=='__main__': asyncio.run(asyncio.wait_for(main(),30))
