"""Temporary bridge into connected GitHub API, one small JSONL chunk per line."""
import base64,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
paths=sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='source_bridge.jsonl' and '.git' not in p.parts and 'build' not in p.parts and p.suffix!='.pyc')
# Don't upload build script used to generate this bridge. Keep all actual project source in GitHub.
out=Path('/mnt/data/source_bridge.jsonl')
with out.open('w',encoding='utf8') as f:
  for path in paths:
    text=(ROOT/path).read_text(encoding='utf-8')
    b64=base64.b64encode(text.encode('utf-8')).decode('ascii')
    n=1800
    chunks=[b64[i:i+n] for i in range(0,len(b64),n)]
    for i,part in enumerate(chunks):
      f.write(json.dumps({'p':path,'i':i,'n':len(chunks),'b':part},ensure_ascii=False,separators=(',',':'))+'\n')
print('BRIDGE',out, 'files',len(paths),'lines',sum(1 for _ in out.open()),'bytes',out.stat().st_size)
