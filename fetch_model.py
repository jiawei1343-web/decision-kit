"""Explicit download of the MIT-licensed E5 model, with resolved revision record."""
import argparse
import json
from pathlib import Path

def main():
    from huggingface_hub import HfApi,snapshot_download
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('destination'); p.add_argument('--revision',default='main'); args=p.parse_args()
    model='intfloat/multilingual-e5-small'
    revision=HfApi().model_info(model,revision=args.revision).sha
    target=snapshot_download(model,revision=revision,local_dir=args.destination,allow_patterns=['*.json','*.txt','*.safetensors','*.model','1_Pooling/*'])
    (Path(target)/'decisionkit-source.json').write_text(json.dumps({'model':model,'revision':revision},indent=2),encoding='utf-8')
    print(target)

if __name__=='__main__': main()
