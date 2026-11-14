"""Small release correction, applied to the verified candidate before building."""
from pathlib import Path
p=Path('desktop/progress_server.py')
s=p.read_text(encoding='utf-8')
old='def main():\n    here='
new='''def main():
    # Frozen Windows programs may inherit cp1252 even when PYTHONIOENCODING is set.
    # Explicit UTF-8 keeps the Chinese connection instructions from crashing startup.
    for stream in (sys.stdout,sys.stderr):
        if stream is not None and hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8',errors='backslashreplace')
    here='''
if old in s:s=s.replace(old,new,1)
elif 'Explicit UTF-8' not in s:raise RuntimeError('Receiver main insertion point changed')
p.write_text(s,encoding='utf-8')
