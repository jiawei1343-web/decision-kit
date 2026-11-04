"""Analyze empirical correctness by margin bin with Wilson intervals. No model probabilities are manufactured."""
import argparse
import json
import math
from pathlib import Path

def analyze(rows):
    groups={}
    for row in rows:
        if type(row.get('correct')) is not bool: raise ValueError('correct must be an independently verified boolean')
        margin=row.get('margin')
        if isinstance(margin,bool) or not isinstance(margin,(int,float)) or not math.isfinite(margin) or not 0<=margin<=2:
            raise ValueError('finite margin between 0 and 2 required')
        key=(row.get('language','und'),min(19,int(margin*10)))
        groups.setdefault(key,[]).append(row['correct'])
    result=[]
    for (language,bin_id),values in sorted(groups.items()):
        n=len(values); rate=sum(values)/n; z=1.96; denominator=1+z*z/n
        center=(rate+z*z/(2*n))/denominator
        radius=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/denominator
        result.append({'language':language,'margin_range':[bin_id/10,(bin_id+1)/10],'samples':n,'accuracy':rate,'wilson_95':[max(0,center-radius),min(1,center+radius)],'sufficient_for_initial_analysis':n>=30})
    return {'bins':result,'notice':'Empirical diagnostic only. Use independent labeled calibration data, separate final test data and enough examples per language/domain. Does not modify runtime gates or prove future correctness.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input'); p.add_argument('output'); args=p.parse_args()
    data=json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    rows=data['results'] if isinstance(data,dict) else data
    Path(args.output).write_text(json.dumps(analyze(rows),ensure_ascii=False,indent=2),encoding='utf-8')
