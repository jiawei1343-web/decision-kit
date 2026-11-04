"""Optional multilingual E5 classifier. Downloads require explicit --download."""
import argparse
import json
import math
from pathlib import Path

class SemanticClassifier:
    def __init__(self, model_path, download=False):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_path, local_files_only=not download, trust_remote_code=False)

    def classify(self, text, labels, minimum_margin=.03):
        if isinstance(minimum_margin,bool) or not isinstance(minimum_margin,(int,float)) or not math.isfinite(minimum_margin) or not 0<=minimum_margin<=2:
            raise ValueError('minimum_margin must be between 0 and 2')
        if not isinstance(text,str) or not text.strip():
            raise ValueError('nonempty text required')
        if not isinstance(labels,dict) or len(labels)<2 or not all(isinstance(v,str) and v.strip() for v in labels.values()):
            raise ValueError('provide at least two label descriptions')
        values=['query: '+text]+['query: '+v for v in labels.values()]
        lengths=[len(self.model.tokenizer.encode(v)) for v in values]
        if max(lengths)>self.model.max_seq_length:
            return {'status':'needs_review','reason':'input_exceeds_model_context'}
        vectors=self.model.encode(values,normalize_embeddings=True)
        scores={key:float(vectors[0] @ vector) for key,vector in zip(labels,vectors[1:])}
        order=sorted(scores,key=scores.get,reverse=True)
        margin=scores[order[0]]-scores[order[1]]
        return {'status':'completed' if margin>=minimum_margin else 'needs_review','label':order[0], 'similarities':scores,'margin':margin,'calibrated':False,'validation':'similarity_gate_not_accuracy_guarantee'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('text'); p.add_argument('labels'); p.add_argument('--model',default='intfloat/multilingual-e5-small'); p.add_argument('--download',action='store_true')
    args=p.parse_args()
    classifier=SemanticClassifier(args.model,args.download)
    print(json.dumps(classifier.classify(args.text,json.loads(Path(args.labels).read_text(encoding='utf-8-sig'))),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
