"""Verified installation, upgrade backup and rollback."""
import argparse
import hashlib
import json
import shutil
import uuid
from pathlib import Path

def files(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and not any(x in ('__pycache__','.git','data','models') for x in p.relative_to(root).parts) and p.name!='package-manifest.json' and p.suffix not in ('.pyc','.sqlite3') and not p.name.startswith('.env') and '.sqlite3-' not in p.name}

def install(destination,upgrade=False,check=False):
    source=Path(__file__).resolve().parent
    destination=Path(destination).resolve()
    if destination==source or source in destination.parents or destination in source.parents: raise ValueError('destination must be separate from source')
    hashes=files(source); manifest=source/'package-manifest.json'
    if manifest.exists() and json.loads(manifest.read_text(encoding='utf-8'))['files']!=hashes: raise ValueError('source manifest mismatch')
    exists=destination.exists()
    if exists:
        if not upgrade: raise FileExistsError('destination exists; use --upgrade')
        old=destination/'package-manifest.json'
        if not old.is_file(): raise ValueError('unmanaged installation; choose a new destination')
        previous=json.loads(old.read_text(encoding='utf-8'))
        if previous.get('name')!='decision-kit' or previous['files']!=files(destination): raise ValueError('installation has edits or unmanaged files')
        if any(p.is_file() and (p.name.startswith('.env') or '.sqlite3' in p.name) for p in destination.iterdir()):
            raise ValueError('move root credentials/databases to an external directory before upgrading')
    if check: return {'status':'ready','files':len(hashes)}
    destination.parent.mkdir(parents=True,exist_ok=True)
    suffix=uuid.uuid4().hex[:10]; stage=destination.parent/('.decision-stage-'+suffix); backup=destination.parent/(destination.name+'.backup-'+suffix)
    try:
        stage.mkdir()
        for name in hashes:
            target=stage/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source/name,target)
        (stage/'package-manifest.json').write_text(json.dumps({'name':'decision-kit','version':'0.2.3','files':hashes},indent=2),encoding='utf-8')
        if files(stage)!=hashes: raise ValueError('staging verification failed')
        if exists:
            for name in ('data','models'):
                if (destination/name).exists(): shutil.copytree(destination/name,stage/name)
            destination.rename(backup)
        try: stage.rename(destination)
        except Exception:
            if exists: backup.rename(destination)
            raise
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return {'status':'installed','destination':str(destination),'backup':str(backup) if exists else None}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('destination',nargs='?',default=str(Path.home()/'.codex/skills/decision-kit'))
    parser.add_argument('--upgrade',action='store_true'); parser.add_argument('--check',action='store_true')
    args=parser.parse_args(); print(json.dumps(install(args.destination,args.upgrade,args.check),ensure_ascii=False,indent=2))
