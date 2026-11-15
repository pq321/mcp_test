#!/usr/bin/env python3
"""One installed-APK scenario; legacy certificate and restored-data checks are separate."""
import subprocess as sp,time,re,json,xml.etree.ElementTree as ET,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'evidence';out.mkdir(exist_ok=True);pkg='org.vector.politicsmemory'
def adb(*args):return sp.check_output(['adb',*args],stderr=sp.STDOUT,timeout=40).decode(errors='replace')
def shell(*args):return adb('shell',*args)
def nodes():
    deadline=time.monotonic()+25;last='no hierarchy'
    while time.monotonic()<deadline:
        try:
            shell('rm','-f','/sdcard/politics-ui.xml')
            status=shell('uiautomator','dump','/sdcard/politics-ui.xml')
            if 'dumped to:' not in status:
                last=status;time.sleep(.5);continue
            raw=adb('exec-out','cat','/sdcard/politics-ui.xml');tree=ET.fromstring(raw);found=list(tree.iter('node'))
            if found:return found
            last='empty hierarchy'
        except (sp.CalledProcessError,ET.ParseError) as error:last=str(error)
        time.sleep(.5)
    raise AssertionError('Android did not return a live UI hierarchy: '+last)
def find(text):return [n for n in nodes() if n.get('text')==text or n.get('content-desc')==text]
def match(text):
    deadline=time.monotonic()+15
    while True:
        found=find(text)
        if found:return found[0]
        if time.monotonic()>=deadline:raise AssertionError('UI not found: '+text)
        time.sleep(.3)
def bounds(text):return list(map(int,re.findall(r'\d+',match(text).get('bounds'))))
def tap_box(box):
    a,b,c,d=box;assert d>b and c>a,('not visible',box);shell('input','tap',str((a+c)//2),str((b+d)//2));time.sleep(.4)
def tap(text):tap_box(bounds(text))
def screenshot(name):(out/(name+'.png')).write_bytes(sp.check_output(['adb','exec-out','screencap','-p'],timeout=25))
def media():
    txt=shell('dumpsys','activity','service',pkg+'/.SpeechService')
    def value(k):
        m=re.search(r'\b'+k+r'=(\S+)',txt);return m.group(1) if m else None
    return {k:value(k) for k in ['active','paused','speed','position_ms','duration_ms','playlist_size','card_id']}
def wait_media(check):
    for _ in range(35):
        state=media()
        if check(state):return state
        time.sleep(.25)
    raise AssertionError(state)
def menu():
    tap('播放速度')
    for _ in range(4):
        if find('声音'):return
        shell('input','swipe','850','1750','850','800','250');time.sleep(.2)
    match('声音')
def run(phase):
    shell('wm','size','1080x2340');shell('wm','density','440')
    shell('input','keyevent','224');shell('wm','dismiss-keyguard')
    shell('am','force-stop',pkg);shell('am','start','-W','-n',pkg+'/.MainActivity');match('复习')
    if phase=='seed':
        tap('复习');tap('揭晓');tap('记住');match('2 / 561');print('PASS: v0.11 first rating seeded before compatibility probe');return
    report={};screenshot('v012-android-catalogue');tap('▸  苏一');match('▸  马原');screenshot('v012-android-suyi')
    tap('复习');match('2 / 561');match('先回忆，再点击揭晓');tap('先回忆，再点击揭晓');match('完整展示');screenshot('v012-android-complete')
    tap('完整展示');match('挖空版');screenshot('v012-android-cloze');tap('挖空版');match('先回忆，再点击揭晓');report['three_modes_cold_hidden']='PASS'
    shell('input','swipe','850','1100','200','1100','280');time.sleep(.6);match('3 / 561');match('先回忆，再点击揭晓')
    shell('input','swipe','200','1100','850','1100','280');time.sleep(.6);match('2 / 561');match('先回忆，再点击揭晓');report['unchanged_finger_direction_and_no_toggle']='PASS'
    menu();assert not find('默认声音');tap('声音');match('默认声音');screenshot('v012-android-voice');tap('默认声音');match('先回忆，再点击揭晓');report['global_voice_folded_after_4x']='PASS'
    tap('播放速度')
    for _ in range(4):
        if find('4.0×'):break
        shell('input','swipe','850','1750','850','800','250');time.sleep(.2)
    tap('4.0×')
    # Observe the actual button while stationary. A progressing SeekBar is never idle,
    # so do not require an idle UI dump before tapping that same live play/pause button.
    play_box=bounds('播放或暂停');tap_box(play_box)
    wait_media(lambda x:x['active']=='true' and x['speed']=='4.0' and int(x['position_ms'] or 0)>0)
    tap_box(play_box);before=wait_media(lambda x:x['paused']=='true');menu();tap('声音');tap('默认声音')
    wait_media(lambda x:x['paused']=='true' and x['card_id']==before['card_id'] and x['speed']=='4.0')
    report['real_media_decode_4x_voice_switch_keeps_pause_and_card']='PASS'
    ids=[x['id'] for x in json.loads((root/'data/suyi-full.json').read_text())['cards']];before=media();next_index=(ids.index(before['card_id'])+1)%len(ids)
    a,b,c,d=bounds('播放进度');play_box=bounds('播放或暂停')
    shell('input','tap',str(c-20),str((b+d)//2));tap_box(play_box)
    wait_media(lambda x:x['card_id']==ids[next_index] and x['paused']=='false')
    tap_box(play_box);wait_media(lambda x:x['paused']=='true');match(str(next_index+1)+' / 561')
    report['real_auto_next_follows_review_without_scoring']='PASS'
    tap('资料');match('播放或暂停');report['player_survives_tab_change']='PASS'
    logs=adb('logcat','-d','-v','brief');assert not re.search(r'FATAL EXCEPTION[\s\S]{0,300}Process: '+re.escape(pkg),logs)
    report['device']='Android 29 emulator 1080x2340 / 440dpi; not physical OPPO K5'
    (out/'v012-android.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['seed','verify'],required=True);phase=p.parse_args().phase
    try:run(phase)
    except Exception:
        screenshot('v012-'+phase+'-failure');(out/('v012-'+phase+'-failure-logcat.txt')).write_text(adb('logcat','-d','-v','brief'));raise
