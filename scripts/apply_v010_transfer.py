"""Apply the checksummed v0.10 source delta without overwriting unrelated work."""
import base64,hashlib,lzma,subprocess
from pathlib import Path
parts=sorted(Path('source').glob('v010-*.b64'))
if parts:
    patch=lzma.decompress(base64.b64decode(''.join(p.read_text().strip() for p in parts),validate=True))
    assert hashlib.sha256(patch).hexdigest()=='ae3382c8c42f5f17278397d0ac197e8b3a0d87e500b2c11aa724fd3d196b3a75','Source checksum mismatch'
    subprocess.run(['git','apply','--unidiff-zero','--check','-'],input=patch,check=True)
    subprocess.run(['git','apply','--unidiff-zero','-'],input=patch,check=True)
    follow=Path('scripts/v010_followup.py')
    if follow.exists():subprocess.run(['python',str(follow)],check=True)
