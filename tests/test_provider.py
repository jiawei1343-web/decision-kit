import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from runtime import ChatProvider,validate_request

class ProviderTests(unittest.TestCase):
    def test_wire_usage_and_validation(self):
        responses=[{'status':'completed','value':'billing'}, {'status':'completed','value':'not-a-label'}]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if request['model']!='test': raise ValueError('wrong model')
                body=json.dumps({'choices':[{'message':{'content':json.dumps(responses.pop(0))},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':10}}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            provider=ChatProvider({'url':f'http://127.0.0.1:{server.server_port}/v1/chat/completions','model':'test','call_ceiling_usd':1,'input_per_million':1,'output_per_million':2})
            r=validate_request({'text':'refund','project':'test','criteria':{'billing':'money','technical':'software'}})
            answer,cost=provider.call(r)
            self.assertEqual(answer['value'],'billing'); self.assertAlmostEqual(cost,.00012)
            answer,cost=provider.call(r)
            self.assertEqual(answer['status'],'needs_review'); self.assertAlmostEqual(cost,.00012)
        finally: server.shutdown(); server.server_close(); thread.join(5)
    def test_insecure_remote_rejected(self):
        with self.assertRaises(ValueError): ChatProvider({'url':'http://example.com/v1/chat/completions'})

if __name__=='__main__': unittest.main()
