"""Local, trainable text decision core. Python standard library only."""
import argparse
import hashlib
import json
import math
import re
import unicodedata
import sqlite3
from collections import Counter
from pathlib import Path

VERSION = '0.2.3'

def tokens(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    words = re.findall(r'[^\W_]+', text, re.UNICODE)
    words += ['char:' + text[i:i+2] for i in range(len(text)-1) if not any(c.isspace() for c in text[i:i+2])]
    chinese = re.findall(r'[\u4e00-\u9fff]+', text)
    return words + [s[i:i+2] for s in chinese for i in range(len(s)-1)]

def train(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('training data must be a nonempty list')
    counts, docs = {}, Counter()
    for row in rows:
        text, label = row['text'], row['label']
        if not isinstance(text, str) or not text.strip() or not isinstance(label, str) or not label.strip():
            raise ValueError('text and label must be nonempty strings')
        docs[label] += 1
        counts.setdefault(label, Counter()).update(tokens(text))
    if len(docs) < 2:
        raise ValueError('at least two labels required')
    return dict(version=VERSION, algorithm='multinomial-naive-bayes', docs=dict(docs), counts={k:dict(v) for k,v in counts.items()})

def predict(model, text):
    features = Counter(tokens(text))
    vocabulary = set().union(*(set(c) for c in model['counts'].values()))
    known = sum(v for k,v in features.items() if k in vocabulary)
    scores = {}
    for label, counts in model['counts'].items():
        score = math.log(model['docs'][label] / sum(model['docs'].values()))
        total = sum(counts.values()) + len(vocabulary)
        for token, number in features.items():
            if token in vocabulary:
                score += number * math.log((counts.get(token, 0)+1)/total)
        scores[label] = score
    peak = max(scores.values())
    weights = {k: math.exp(v-peak) for k,v in scores.items()}
    norm = sum(weights.values())
    probabilities = {k:v/norm for k,v in weights.items()}
    ordered = sorted(probabilities, key=probabilities.get, reverse=True)
    return dict(label=ordered[0], scores=probabilities, margin=probabilities[ordered[0]]-probabilities[ordered[1]], coverage=known/max(1,sum(features.values())), calibrated=False)

class Engine:
    def __init__(self, model, database):
        self.model = model
        self.fingerprint = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
        self.db = sqlite3.connect(database)
        self.db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, route TEXT, status TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')

    def close(self):
        self.db.close()

    def decide(self, text, project='default', min_margin=.5, min_coverage=.25):
        if not isinstance(text, str) or not text.strip() or len(text)>100000:
            raise ValueError('text must contain 1..100000 characters')
        if not isinstance(project, str) or not project.strip():
            raise ValueError('project required')
        for value in (min_margin, min_coverage):
            if not isinstance(value, (float,int)) or not math.isfinite(value) or not 0<=value<=1:
                raise ValueError('thresholds must be finite values between 0 and 1')
        key = hashlib.sha256(json.dumps([VERSION,self.fingerprint,project,text,min_margin,min_coverage], ensure_ascii=False).encode()).hexdigest()
        with self.db:
            cached = self.db.execute('SELECT value FROM cache WHERE key=?',(key,)).fetchone()
            if cached:
                result = json.loads(cached[0]); result['route']='exact_cache'
            else:
                prediction = predict(self.model,text)
                accepted = prediction['margin']>=min_margin and prediction['coverage']>=min_coverage
                result = dict(status='completed' if accepted else 'needs_review', route='local_classifier', result=prediction, model_fingerprint=self.fingerprint, validation='heuristic_gate_not_accuracy_guarantee', cost=dict(remote_calls=0, api_cost_usd=0, local_compute_cost='unmeasured'))
                self.db.execute('INSERT OR REPLACE INTO cache VALUES (?,?)',(key,json.dumps(result)))
            self.db.execute('INSERT INTO events(route,status) VALUES (?,?)',(result['route'],result['status']))
        return result

def evaluate(model, rows):
    engine = Engine(model, ':memory:')
    try:
        results = [(r,engine.decide(r['text'])) for r in rows]
        accepted = [(r,p) for r,p in results if p['status']=='completed']
        return dict(samples=len(results), accepted=len(accepted), review=len(results)-len(accepted), accepted_accuracy=sum(r['label']==p['result']['label'] for r,p in accepted)/len(accepted) if accepted else None, total_accuracy=sum(r['label']==p['result']['label'] for r,p in results)/len(results) if results else None, note='Evaluate on independent representative data; scores are uncalibrated.')
    finally:
        engine.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('train'); p.add_argument('data'); p.add_argument('output')
    p=commands.add_parser('classify'); p.add_argument('model'); p.add_argument('text'); p.add_argument('--db',default='decisionkit.sqlite3'); p.add_argument('--project',default='default')
    p=commands.add_parser('evaluate'); p.add_argument('model'); p.add_argument('data')
    args=parser.parse_args()
    read=lambda path: json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if args.command=='train':
        model=train(read(args.data)); Path(args.output).write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8'); result={'status':'trained','labels':list(model['docs'])}
    elif args.command=='evaluate': result=evaluate(read(args.model),read(args.data))
    else:
        engine=Engine(read(args.model),args.db)
        try: result=engine.decide(args.text,project=args.project)
        finally: engine.close()
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
