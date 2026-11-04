"""Versioned DecisionKit pipeline CLI."""
import argparse
import json
from pathlib import Path
from runtime import Runtime

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('decide'); p.add_argument('request')
    p=commands.add_parser('batch'); p.add_argument('requests')
    p=commands.add_parser('report'); p.add_argument('project')
    p=commands.add_parser('clear-cache'); p.add_argument('project')
    p=commands.add_parser('settle'); p.add_argument('reservation'); p.add_argument('actual_usd',type=float)
    args=parser.parse_args(); runtime=Runtime(args.config)
    try:
        if args.command=='decide': result=runtime.decide(json.loads(Path(args.request).read_text(encoding='utf-8-sig')))
        elif args.command=='batch':
            rows=json.loads(Path(args.requests).read_text(encoding='utf-8-sig'))
            if not isinstance(rows,list) or len(rows)>1000: raise ValueError('batch must have at most 1000 requests')
            result=[runtime.decide(row) for row in rows]
        elif args.command=='report': result=runtime.report(args.project)
        elif args.command=='clear-cache': result=runtime.clear_cache(args.project)
        else:
            from budget import Budget
            budget=Budget(runtime.database)
            try: budget.settle(args.reservation,args.actual_usd); result={'status':'settled','basis':'operator_supplied_actual_cost'}
            finally: budget.close()
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally: runtime.close()

if __name__=='__main__': main()
