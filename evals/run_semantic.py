"""Small synthetic language smoke set, not a production benchmark."""
import argparse
import json
import platform
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic import SemanticClassifier

def main():
    p=argparse.ArgumentParser(); p.add_argument('model'); p.add_argument('output'); args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    rows=json.loads((root/'evals/multilingual.json').read_text(encoding='utf-8'))
    labels=json.loads((root/'examples/labels.json').read_text(encoding='utf-8'))
    start=time.perf_counter(); classifier=SemanticClassifier(args.model); load=time.perf_counter()-start
    results=[]
    for row in rows:
        start=time.perf_counter(); result=classifier.classify(row['text'],labels)
        results.append({**row,**result,'correct':result.get('label')==row['label'],'expected':row['label'],'seconds':time.perf_counter()-start})
    accepted=[r for r in results if r['status']=='completed']
    report={'model':'intfloat/multilingual-e5-small','python':platform.python_version(),'platform':platform.platform(),'load_seconds':load,'samples':len(rows),'languages':len({r['language'] for r in rows}),'correct':sum(r['correct'] for r in results),'accepted':len(accepted),'accepted_correct':sum(r['correct'] for r in accepted),'notice':'Synthetic one-example-per-language smoke test. Not independent human evaluation, not Jev comparison, not evidence of 100-language accuracy. No threshold tuning on these results.','results':results}
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False))

if __name__=='__main__': main()
