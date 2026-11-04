"""Compare two configured pipelines on the same labeled requests. May incur configured API costs."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime import Runtime

def summarize(results):
    completed=[r for r in results if r['status']=='completed']
    correct=sum(r['correct'] for r in completed)
    cost=sum(r['cost']['estimated_usd'] for r in results)
    return {'samples':len(results),'completed':len(completed),'correct':correct,'completion_rate':len(completed)/len(results) if results else None,'accepted_accuracy':correct/len(completed) if completed else None,'estimated_usd':cost,'estimated_cost_per_correct':cost/correct if correct else None,'unknown_cost':any(r['cost']['unknown_charge'] for r in results)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline'); p.add_argument('candidate'); p.add_argument('dataset'); p.add_argument('output'); args=p.parse_args()
    rows=json.loads(Path(args.dataset).read_text(encoding='utf-8-sig'))
    reports={}
    for name,config in [('baseline',args.baseline),('candidate',args.candidate)]:
        runtime=Runtime(config); results=[]
        try:
            for row in rows:
                request=row['request']; result=runtime.decide(request)
                results.append({'status':result['status'],'correct':result.get('value')==row['expected'],'cost':result['cost'],'seconds':result['elapsed_seconds'],'route':result['route'],'language':request.get('language','und')})
        finally: runtime.close()
        reports[name]={**summarize(results),'by_language':{lang:summarize([r for r in results if r['language']==lang]) for lang in sorted({r['language'] for r in results})},'results':results}
    baseline,candidate=reports['baseline'],reports['candidate']
    reports['estimated_savings_usd']=None if baseline['unknown_cost'] or candidate['unknown_cost'] else baseline['estimated_usd']-candidate['estimated_usd']
    reports['notice']='Compare correctness and completion alongside cost. Uses configured token prices, excludes local electricity/hardware and evaluation labor. Cache state affects results. No automatic quality equivalence claim.'
    Path(args.output).write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
