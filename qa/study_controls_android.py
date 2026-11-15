#!/usr/bin/env python3
"""Small installed-APK acceptance. Run seed with v0.11, verify after install -r v0.12."""
import subprocess as sp,time,re,json,xml.etree.ElementTree as ET,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'evidence';out.mkdir(exist_ok=True);pkg='org.vector.politicsmemory'
def adb(*args):return sp.check_output(['adb',*args],timeout=40).decode(errors='replace')
def shell(*args):return adb('shell',*args)
def nodes():
    shell('uiautomator','dump','/sdcard/politics-ui.xml');return list(ET.fromstring(adb('exec-out','cat','/sdcard/politics-ui.xml')).iter('node'))
def find(text):return [n for n in nodes() if n.get('text')==text or n.get('content-desc')==text]
def match(text):
    found=find(text);assert found,'UI not found: '+text;return found[0]
def bounds(text):return list(map(int,re.findall(r'\d+',match(text).get('bounds'))))
def tap(text):
    a,b,c,d=bounds(text);assert d>b and c>a,('not visible',text);shell('input','tap',str((a+c)//2),str((b+d)//2));time.sleep(.4)
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
    # Menu intentionally scrolls on compact devices; voice remains after the final speed.
    for _ in range(4):
        if find('声音'):return
        shell('input','swipe','850','1750','850','800','250');time.sleep(.2)
    match('声音')
def run(phase):
    shell('wm','size','1080x2340');shell('wm','density','440');shell('am','force-stop',pkg);shell('am','start','-n',pkg+'/.MainActivity');time.sleep(4)
    if phase=='seed':
        tap('复习');tap('揭晓');tap('记住');match('2 / 561');print('PASS: v0.11 first rating seeded before in-place upgrade');return
    report={};screenshot('v012-android-catalogue');tap('▸  苏一');match('▸  马原');screenshot('v012-android-suyi')
    tap('复习');match('2 / 561');match('先回忆，再点击揭晓');tap('先回忆，再点击揭晓');match('完整展示');screenshot('v012-android-complete')
    tap('完整展示');match('挖空版');screenshot('v012-android-cloze');tap('挖空版');match('先回忆，再点击揭晓')
    report['three_modes_cold_hidden']='PASS'
    shell('input','swipe','850','1100','200','1100','280');time.sleep(.6);match('3 / 561');match('先回忆，再点击揭晓')
    shell('input','swipe','200','1100','850','1100','280');time.sleep(.6);match('2 / 561');match('先回忆，再点击揭晓')
    report['unchanged_finger_direction_and_no_toggle']='PASS'
    menu();assert not find('默认声音');tap('声音');match('默认声音');screenshot('v012-android-voice');tap('默认声音');match('先回忆，再点击揭晓')
    report['global_voice_folded_after_4x']='PASS'
    tap('播放速度')
    for _ in range(4):
        if find('4.0×'):break
        shell('input','swipe','850','1750','850','800','250');time.sleep(.2)
    tap('4.0×');tap('播放或暂停');wait_media(lambda x:x['active']=='true' and x['speed']=='4.0' and int(x['position_ms'])>0)
    tap('播放或暂停');before=wait_media(lambda x:x['paused']=='true');menu();tap('声音');tap('默认声音');wait_media(lambda x:x['paused']=='true' and x['card_id']==before['card_id'] and x['speed']=='4.0')
    report['real_media_decode_4x_voice_switch_keeps_pause_and_card']='PASS'
    tap('播放或暂停');a,b,c,d=bounds('播放进度');shell('input','tap',str(c-20),str((b+d)//2));ids=[x['id'] for x in json.loads((root/'data/suyi-full.json').read_text())['cards']]
    wait_media(lambda x:x['card_id']==ids[2] and x['paused']=='false');match('3 / 561');tap('播放或暂停')
    report['real_auto_next_follows_review_without_scoring']='PASS'
    tap('资料');match('播放或暂停');report['player_survives_tab_change']='PASS'
    logs=adb('logcat','-d','-v','brief');assert not re.search(r'FATAL EXCEPTION[\s\S]{0,300}Process: '+re.escape(pkg),logs)
    report['device']='Android 29 emulator 1080x2340 / 440dpi; not physical OPPO K5'
    (out/'v012-android.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['seed','verify'],required=True);run(p.parse_args().phase)
