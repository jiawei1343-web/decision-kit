import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from decisionkit import train
from http_server import create_server
from install import install
from runtime import Runtime

class InterfaceTests(unittest.TestCase):
    def test_pipeline_http(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config.json'
            path.write_text(json.dumps({'database':'db.sqlite3','exact_rules':[{'task':'check','text':'yes','criteria':{'condition':'affirmative'},'value':True}]}))
            runtime=Runtime(path); token='pipeline-test-token-123456789'
            server=create_server(None,None,token,0,runtime)
            thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
            try:
                request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/decide',data=json.dumps({'task':'check','text':'yes','criteria':{'condition':'affirmative'},'project':'demo'}).encode(),headers={'Authorization':'Bearer '+token})
                with urllib.request.urlopen(request,timeout=5) as response: result=json.load(response)
                self.assertTrue(result['value'])
            finally: server.shutdown(); server.server_close(); thread.join(5); runtime.close()
    def test_http_auth_and_classification(self):
        with tempfile.TemporaryDirectory() as folder:
            model=train([{'text':'refund payment','label':'billing'},{'text':'crash broken','label':'technical'}])
            token='test-token-'*4
            server=create_server(model,str(Path(folder)/'db.sqlite3'),token,0)
            thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
            url='http://127.0.0.1:'+str(server.server_port)+'/classify'
            try:
                request=urllib.request.Request(url,data=b'{}')
                with self.assertRaises(urllib.error.HTTPError) as ctx: urllib.request.urlopen(request,timeout=5)
                self.assertEqual(ctx.exception.code,401)
                request=urllib.request.Request(url,data=json.dumps({'text':'refund payment','project':'test'}).encode(),headers={'Authorization':'Bearer '+token})
                with urllib.request.urlopen(request,timeout=5) as response: result=json.load(response)
                self.assertEqual(result['result']['label'],'billing')
            finally: server.shutdown(); server.server_close(); thread.join(5)
    def test_installer_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            destination=Path(folder)/'skill'
            install(destination)
            self.assertTrue((destination/'SKILL.md').is_file())
            with self.assertRaises(FileExistsError): install(destination)
    def test_upgrade_retains_backup_and_rejects_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            destination=Path(folder)/'skill'; install(destination)
            data=destination/'data'; data.mkdir(); (data/'keep.txt').write_text('user-data')
            result=install(destination,upgrade=True)
            self.assertTrue(Path(result['backup']).exists())
            self.assertEqual((data/'keep.txt').read_text(),'user-data')
            (destination/'SKILL.md').write_text('user edits')
            with self.assertRaises(ValueError): install(destination,upgrade=True)
