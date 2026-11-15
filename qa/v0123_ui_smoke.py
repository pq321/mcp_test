#!/usr/bin/env python3
"""Disposable emulator: only the four requested UI changes."""
import sys,json,re,time,subprocess as sp
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import study_controls_android as ui
ui.pkg='org.vector.politicsmemory.stable'
pkg=ui.pkg
def main():
    ui.shell('wm','size','1080x2340');ui.shell('wm','density','440')
    sp.run(['adb','install','-r','app/build/outputs/apk/debug/app-debug.apk'],check=True)
    ui.shell('am','force-stop',pkg)
    ui.shell('am','start','-W','-n',pkg+'/org.vector.politicsmemory.MainActivity')
    ui.match('▸  苏一')
    old_left=ui.bounds('▸  苏一')[0]
    ui.tap('▸  苏一')
    ui.match('▸  马原')
    new_left=ui.bounds('▸  马原')[0]
    assert new_left-old_left >= 25,('subject not visibly indented',old_left,new_left)
    ui.screenshot('v0123-subject-indented')
    ui.tap('复习')
    ui.match('1 / 561')
    ui.tap('揭晓')
    order=[(t,ui.bounds(t)[0]) for t in ('记住','模糊','忘记')]
    assert order[0][1]<order[1][1]<order[2][1],order
    ui.screenshot('v0123-buttons')
    ui.tap('记住')
    ui.match('2 / 561')
    ui.tap('资料')
    ui.match('▾  苏一')
    ui.screenshot('v0123-after-rating')
    log=ui.adb('logcat','-d','-v','brief')
    assert not re.search(r'FATAL EXCEPTION[\s\S]{0,300}Process: '+re.escape(pkg),log)
    report={'rating_left_to_right':['记住','模糊','忘记'],'subject_indent_px':new_left-old_left,
      'same_pack_561':'PASS','rating_press_advances':'PASS','launcher_label':'闪背',
      'manual_sync_animation':'compile/source inspected; provider is not emulated',
      'platform':'Android 29 emulator, not user phone'}
    Path('evidence').mkdir(exist_ok=True)
    Path('evidence/v0123-emulator.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except Exception:
        try:ui.screenshot('v0123-failure')
        except Exception:pass
        raise
