"""Create an offline-first working profile without overwriting user files."""
import argparse
import json
import platform
import shutil
from pathlib import Path

def create_profile(destination):
    destination=Path(destination).expanduser().resolve()
    if destination.exists(): raise FileExistsError('choose a new profile directory')
    destination.mkdir(parents=True)
    source=Path(__file__).resolve().parent/'examples'
    for name in ('model.json','request.json'):
        shutil.copy2(source/name,destination/name)
    config=json.loads((source/'config.json').read_text(encoding='utf-8'))
    config['database']='data/decisionkit.sqlite3'
    (destination/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'profile':str(destination),'offline':True,'python':platform.python_version(),'next_command':f'python cli.py --config "{destination / "config.json"}" decide "{destination / "request.json"}"'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('destination',nargs='?'); args=p.parse_args()
    destination=args.destination or input('New profile directory (existing files will not be overwritten): ').strip()
    if not destination: p.error('destination required')
    print(json.dumps(create_profile(destination),ensure_ascii=False,indent=2))
