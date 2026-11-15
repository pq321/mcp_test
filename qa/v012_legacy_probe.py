#!/usr/bin/env python3
"""CI-only legacy database compatibility probe. NEVER runs against a physical device.

A certificate mismatch is recorded as BLOCKED, not relabeled an in-place upgrade.
The disposable emulator may then restore its synthetic database to check the new app.
"""
import io,json,os,sqlite3,subprocess as sp,tarfile,tempfile
from pathlib import Path
PKG='org.vector.politicsmemory'
def command(*args,**kw):
    return sp.run(['adb',*args],check=True,stdout=sp.PIPE,stderr=sp.PIPE,timeout=60,**kw).stdout

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','CI only'
    serial=command('get-serialno').decode().strip()
    assert serial.startswith('emulator-'),'Refuse to change a physical phone'
    new='app/build/outputs/apk/debug/app-debug.apk'
    command('shell','am','force-stop',PKG)
    backup=command('exec-out','run-as',PKG,'tar','-cf','-','databases')
    with tarfile.open(fileobj=io.BytesIO(backup)) as archive:
        names=archive.getnames()
        assert names and all(n=='databases' or n.startswith('databases/') for n in names)
        with tempfile.TemporaryDirectory() as tmp:
            for item in archive.getmembers():
                if item.isfile():
                    assert '..' not in Path(item.name).parts
                    dest=Path(tmp)/item.name;dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(archive.extractfile(item).read())
            dbs=list((Path(tmp)/'databases').glob('*.db'))
            assert len(dbs)==1, names
            db=sqlite3.connect(dbs[0]);assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
            assert db.execute('select count(*) from events').fetchone()[0]>=1
            db.close()
    install=sp.run(['adb','install','-r',new],stdout=sp.PIPE,stderr=sp.STDOUT,timeout=90)
    message=install.stdout.decode(errors='replace')
    report={'released_v011_in_place_upgrade':'PASS','disposable_emulator_database_restore':'NOT_NEEDED'}
    if install.returncode:
        assert 'INSTALL_FAILED_UPDATE_INCOMPATIBLE' in message,message
        report={'released_v011_in_place_upgrade':'BLOCKED_SIGNATURE_MISMATCH','disposable_emulator_database_restore':'PASS','error':message.strip(),
                'scope':'Only synthetic test data on a disposable emulator; NOT a tested user-phone migration.'}
        command('uninstall',PKG)
        command('install',new)
        command('shell','run-as',PKG,'tar','-xf','-',input=backup)
        assert command('exec-out','run-as',PKG,'ls','databases')
    out=Path('evidence');out.mkdir(exist_ok=True)
    (out/'v012-upgrade.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
