"""Authenticated loopback-only HTTP adapter for the local classification core."""
import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from decisionkit import Engine

def create_server(model, database, token, port=8765, runtime=None):
    if not token or len(token)<24: raise ValueError('DECISIONKIT_HTTP_TOKEN must have at least 24 characters')
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup(); self.connection.settimeout(15)
        def log_message(self,*args): pass
        def reply(self,status,data):
            body=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_POST(self):
            if not hmac.compare_digest(self.headers.get('Authorization','').encode(),'Bearer '.encode()+token.encode()):
                return self.reply(401,{'error':'unauthorized'})
            if self.path not in ('/classify','/decide','/report'): return self.reply(404,{'error':'not_found'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=500000: return self.reply(413,{'error':'invalid_body_size'})
                data=json.loads(self.rfile.read(size))
                if self.path in ('/decide','/report'):
                    if runtime is None: return self.reply(503,{'error':'pipeline_not_configured'})
                    if self.path=='/report':
                        if not isinstance(data,dict) or set(data)!={'project'} or not isinstance(data['project'],str): raise ValueError('project required')
                        return self.reply(200,runtime.report(data['project']))
                    return self.reply(200,runtime.decide(data))
                if not isinstance(data,dict) or set(data)-{'text','project'}: raise ValueError('invalid fields')
                if model is None: return self.reply(503,{'error':'legacy_model_not_configured'})
                engine=Engine(model,database)
                try: result=engine.decide(data['text'],project=data['project'])
                finally: engine.close()
                self.reply(200,result)
            except (ValueError,KeyError,TypeError): self.reply(400,{'error':'invalid_request'})
            except Exception: self.reply(500,{'error':'internal_error'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('model',nargs='?'); p.add_argument('--config'); p.add_argument('--db',default='decisionkit.sqlite3'); p.add_argument('--port',type=int,default=8765)
    args=p.parse_args()
    from runtime import Runtime
    runtime=Runtime(args.config) if args.config else None
    model=json.loads(Path(args.model).read_text(encoding='utf-8-sig')) if args.model else None
    if model is None and runtime is None: p.error('provide model or --config')
    server=create_server(model,args.db,os.environ.get('DECISIONKIT_HTTP_TOKEN',''),args.port,runtime)
    try: server.serve_forever()
    finally:
        server.server_close()
        if runtime: runtime.close()

if __name__=='__main__': main()
