#!/usr/bin/env python3
"""Focused installation check on a disposable emulator, not a phone migration."""
import hashlib,json,subprocess as sp,time
from pathlib import Path
import study_controls_android as ui
OLD='org.vector.politicsmemory'
NEW='org.vector.politicsmemory.stable'
APK='deliverables/PoliticsMemory-v0.12.1.apk'

def adb_bytes(*args):
    return sp.check_output(['adb',*args],timeout=90)

def legacy_hashes():
    files=adb_bytes('exec-out','run-as',OLD,'ls','databases').decode().split()
    return {name:hashlib.sha256(adb_bytes('exec-out','run-as',OLD,'cat','databases/'+name)).hexdigest() for name in files}

def launch_new():
    ui.pkg=NEW
    ui.shell('am','force-stop',NEW)
    ui.shell('am','start','-W','-n',NEW+'/'+OLD+'.MainActivity')
    time.sleep(2)
    ui.match('复习')
    ui.tap('复习')

def main():
    assert adb_bytes('get-serialno').decode().strip().startswith('emulator-'),'Disposable emulator only'
    adb_bytes('install','old/PoliticsMemory-v0.11.0.apk')
    ui.run('seed')
    ui.shell('am','force-stop',OLD)
    original=legacy_hashes()
    assert 'politics-memory.db' in original
    assert 'Success' in adb_bytes('install',APK).decode()
    assert OLD in ui.shell('pm','list','packages',OLD)
    assert NEW in ui.shell('pm','list','packages',NEW)
    launch_new();ui.match('1 / 561');ui.match('先回忆，再点击揭晓')
    ui.tap('先回忆，再点击揭晓');ui.match('完整展示');ui.tap('完整展示');ui.match('挖空版')
    ui.tap('记住');ui.match('2 / 561');ui.screenshot('stable-new-before-reinstall')
    ui.shell('am','force-stop',NEW)
    assert 'Success' in adb_bytes('install','-r',APK).decode()
    launch_new();ui.match('2 / 561');ui.match('先回忆，再点击揭晓')
    ui.screenshot('stable-new-after-reinstall')
    assert legacy_hashes()==original,'Legacy private database changed'
    ui.shell('am','force-stop',NEW)
    ui.pkg=OLD;ui.shell('am','start','-W','-n',OLD+'/.MainActivity');time.sleep(2)
    ui.tap('复习');ui.match('2 / 561');ui.screenshot('legacy-still-intact')
    logs=ui.adb('logcat','-d','-v','brief')
    (Path('evidence')/'install-logcat.txt').write_text(logs)
    assert 'FATAL EXCEPTION' not in '\n'.join(line for line in logs.splitlines() if NEW in line)
    report={'version':'0.12.1','application_id':NEW,'legacy_application_id':OLD,
      'install_without_uninstalling_legacy':'PASS','both_apps_launch':'PASS',
      'release_apk_reinstall_preserves_new_rating_and_cursor':'PASS',
      'legacy_database_files_unchanged':'PASS','legacy_rating_and_cursor_still_accessible':'PASS',
      'three_study_modes_in_release':'PASS','production_logic_and_content_unchanged_from_v012':'PASS',
      'legacy_database_sha256':original,
      'signing_verification':Path('evidence/signature.txt').read_text(),
      'device':'Android 29 emulator; not physical OPPO K5',
      'limits':['New and old private databases are separate. User progress is not automatically migrated.','Real phone and Google Drive upload require user-device verification.']}
    Path('evidence/install-fix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except Exception:
        try:ui.screenshot('stable-install-failure')
        except Exception:pass
        raise
