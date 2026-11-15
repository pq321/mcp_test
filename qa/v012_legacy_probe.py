#!/usr/bin/env python3
"""CI-only legacy compatibility probe; never operates on a physical phone.
A signing mismatch stays BLOCKED. Synthetic database restore is a separate check.
"""
import hashlib,io,json,os,re,sqlite3,subprocess as sp,tarfile,tempfile,zipfile
from pathlib import Path
PKG='org.vector.politicsmemory'
def command(*args,**kw):
    result=sp.run(['adb',*args],stdout=sp.PIPE,stderr=sp.PIPE,timeout=90,**kw)
    if result.returncode:
        raise RuntimeError('adb '+repr(args)+'\n'+result.stderr.decode(errors='replace')+'\n'+result.stdout.decode(errors='replace'))
    return result.stdout

def source_snapshot(out):
    with zipfile.ZipFile(out/'v012-source-review.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ['app/src/main/java','app/src/androidTest','data','preview','scripts','qa','docs','desktop','.github/workflows']:
            for p in Path(folder).rglob('*'):
                if p.is_file() and p.suffix in {'.java','.json','.js','.css','.html','.py','.md','.txt','.yml','.sh','.cmd'}:z.write(p,p.as_posix())
        for name in ['build.gradle','app/build.gradle','settings.gradle','gradle.properties','app/src/main/AndroidManifest.xml']:
            p=Path(name)
            if p.is_file():z.write(p,name)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','CI only'
    assert command('get-serialno').decode().strip().startswith('emulator-'),'Refuse a physical phone'
    out=Path('evidence');out.mkdir(exist_ok=True);source_snapshot(out)
    new='app/build/outputs/apk/debug/app-debug.apk'
    command('shell','am','force-stop',PKG)
    backup=command('exec-out','run-as',PKG,'tar','-cf','-','databases');files={}
    with tarfile.open(fileobj=io.BytesIO(backup)) as archive:
        for item in archive.getmembers():
            if item.isdir():
                assert item.name.rstrip('/')=='databases';continue
            assert item.isfile() and re.fullmatch(r'databases/[A-Za-z0-9._-]+',item.name),item.name
            assert item.name not in files,item.name
            files[item.name]=archive.extractfile(item).read()
    with tempfile.TemporaryDirectory() as tmp:
        for name,data in files.items():
            p=Path(tmp)/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        dbs=list((Path(tmp)/'databases').glob('*.db'));assert len(dbs)==1,list(files)
        db=sqlite3.connect(dbs[0]);assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
        assert db.execute('select count(*) from events').fetchone()[0]>=1;db.close()
    install=sp.run(['adb','install','-r',new],stdout=sp.PIPE,stderr=sp.STDOUT,timeout=90)
    message=install.stdout.decode(errors='replace')
    report={'released_v011_in_place_upgrade':'PASS','disposable_emulator_database_restore':'NOT_NEEDED'}
    if install.returncode:
        assert 'INSTALL_FAILED_UPDATE_INCOMPATIBLE' in message,message
        report={'released_v011_in_place_upgrade':'BLOCKED_SIGNATURE_MISMATCH','disposable_emulator_database_restore':'PENDING','error':message.strip(),
                'scope':'Only synthetic records on a disposable emulator; NOT a user-phone migration.'}
        (out/'v012-upgrade.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        command('uninstall',PKG);command('install',new);command('shell','run-as',PKG,'mkdir','-p','databases')
        # push waits for transfer completion. The shell reads its own staging file;
        # run-as writes a fresh app-owned file. No tar ownership or streaming EOF race.
        with tempfile.TemporaryDirectory() as tmp:
            local=Path(tmp)/'synthetic-db.bin';remote='/data/local/tmp/politics-v012-synthetic-db.bin'
            try:
                for name,data in files.items():
                    local.write_bytes(data);command('push',str(local),remote)
                    command('shell',f'cat {remote} | run-as {PKG} sh -c "cat > {name}"')
                    actual=command('exec-out','run-as',PKG,'cat',name)
                    assert actual==data, f'Restored bytes differ: {name}; expected {len(data)}, got {len(actual)}'
            finally:command('shell','rm','-f',remote)
        report['disposable_emulator_database_restore']='PASS'
        report['restored_files_sha256']={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    (out/'v012-upgrade.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
