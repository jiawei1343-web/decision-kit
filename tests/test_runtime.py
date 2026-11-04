import concurrent.futures
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from budget import Budget
from runtime import Runtime, validate_request, validate_answer, ChatProvider

REQUEST={'text':'please refund','project':'demo','criteria':{'billing':'money','technical':'software'}}

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.config={'database':'data.sqlite3','project_budget_usd':1,'cache_ttl_seconds':60,
            'providers':[{'url':'http://127.0.0.1:9999/v1/chat/completions','model':'test','call_ceiling_usd':.1,'input_per_million':1,'output_per_million':1}]}
    def tearDown(self): self.temp.cleanup()
    def runtime(self):
        path=self.root/'config.json'; path.write_text(json.dumps(self.config)); return Runtime(path)
    def test_cache_and_policy_isolation(self):
        runtime=self.runtime()
        try:
            with patch.object(ChatProvider,'call',return_value=({'status':'completed','value':'billing'},.01)) as call:
                request={**REQUEST,'max_cost_usd':.2}
                self.assertEqual(runtime.decide(request)['route'],'chat:test')
                self.assertEqual(runtime.decide(request)['route'],'exact_cache')
                runtime.decide({**request,'project':'other'})
                runtime.decide({**request,'data_version':'2'})
                self.assertEqual(call.call_count,3)
                self.assertEqual(runtime.report('demo')['budget']['settled'],.02)
                runtime.clear_cache('demo')
                self.assertEqual(runtime.decide(request)['route'],'chat:test')
        finally: runtime.close()
    def test_expired_cache(self):
        self.config['cache_ttl_seconds']=.01; runtime=self.runtime()
        try:
            with patch.object(ChatProvider,'call',return_value=({'status':'completed','value':'billing'},0)) as call:
                runtime.decide({**REQUEST,'max_cost_usd':.2}); time.sleep(.02)
                runtime.decide({**REQUEST,'max_cost_usd':.2}); self.assertEqual(call.call_count,2)
        finally: runtime.close()
    def test_remote_denied(self):
        self.config['providers'][0]['url']='https://example.com/v1/chat/completions'; runtime=self.runtime()
        try:
            with patch.object(ChatProvider,'call') as call:
                runtime.decide({**REQUEST,'max_cost_usd':1,'allow_remote':True}); call.assert_not_called()
        finally: runtime.close()
    def test_remote_permission_string_rejected(self):
        self.config['allow_remote']='false'
        with self.assertRaisesRegex(ValueError,'allow_remote must be boolean'):
            self.runtime()
    def test_budget_no_call(self):
        runtime=self.runtime()
        try:
            with patch.object(ChatProvider,'call') as call:
                self.assertEqual(runtime.decide(REQUEST)['status'],'budget_exceeded'); call.assert_not_called()
        finally: runtime.close()
    def test_unknown_cost_no_fallback(self):
        self.config['providers']*=2; runtime=self.runtime()
        try:
            with patch.object(ChatProvider,'call',side_effect=TimeoutError) as call:
                result=runtime.decide({**REQUEST,'max_cost_usd':1})
                self.assertTrue(result['cost']['unknown_charge']); self.assertEqual(call.call_count,1)
                self.assertEqual(runtime.report('demo')['budget']['reserved'],.1)
        finally: runtime.close()
    def test_escalation_bounded(self):
        self.config['providers']*=2; runtime=self.runtime()
        try:
            with patch.object(ChatProvider,'call',side_effect=[({'status':'needs_review'},.01),({'status':'completed','value':'billing'},.02)]) as call:
                result=runtime.decide({**REQUEST,'max_cost_usd':1}); self.assertEqual(result['status'],'completed'); self.assertEqual(call.call_count,2)
        finally: runtime.close()
    def test_zero_cost_fallback(self):
        self.config['providers'][0]['call_ceiling_usd']=0
        self.config['providers']*=2
        runtime=self.runtime()
        try:
            with patch.object(ChatProvider,'call',side_effect=[({'status':'needs_review'},0),({'status':'completed','value':'billing'},0)]):
                self.assertEqual(runtime.decide(REQUEST)['value'],'billing')
        finally: runtime.close()
    def test_extraction_and_types(self):
        request=validate_request({**REQUEST,'task':'extract','text':'Name: Alice','criteria':{'name':'person name'}})
        self.assertEqual(validate_answer({'status':'completed','value':{'name':'Alice'}},request)['status'],'completed')
        with self.assertRaises(ValueError): validate_answer({'status':'completed','value':{'name':'Bob'}},request)
        with self.assertRaises(ValueError): validate_request({**REQUEST,'allow_remote':'true'})
        with self.assertRaises(ValueError): validate_request({**REQUEST,'max_cost_usd':float('nan')})
    def test_atomic_budget_across_connections(self):
        path=self.root/'ledger.sqlite3'
        initial=Budget(path); initial.close()
        def reserve(_):
            b=Budget(path)
            try: return b.reserve('p',.6,1)
            finally: b.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(reserve,range(4)))
        self.assertEqual(sum(x is not None for x in results),1)
    def test_check_and_score(self):
        request=validate_request({**REQUEST,'task':'check','criteria':{'condition':'asks for money'}})
        self.assertTrue(validate_answer({'status':'completed','value':True},request)['value'])
        with self.assertRaises(ValueError): validate_answer({'status':'completed','value':1},request)
        request=validate_request({**REQUEST,'task':'score','criteria':{'low':'minor','high':'major'}})
        self.assertEqual(validate_answer({'status':'completed','value':'high'},request)['value'],'high')
    def test_exact_rule(self):
        self.config['exact_rules']=[{'task':'classify','text':REQUEST['text'],'criteria':REQUEST['criteria'],'value':'billing'}]
        runtime=self.runtime()
        try:
            result=runtime.decide(REQUEST)
            self.assertEqual(result['route'],'exact_rule'); self.assertEqual(result['value'],'billing')
        finally: runtime.close()
    def test_quality_without_backend_explains(self):
        self.config['providers']=[]; runtime=self.runtime()
        try:
            result=runtime.decide({**REQUEST,'mode':'quality'})
            self.assertEqual(result['reason'],'quality_mode_requires_chat_provider')
        finally: runtime.close()

if __name__=='__main__': unittest.main()
