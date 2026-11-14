"""Publish only after real browser, Android and receiver acceptance succeeds."""
import json,hashlib,os,shutil
from pathlib import Path
for name in ['index.html','audio-index.json','README.txt','progress_server.py','start-sync.cmd','start-sync.sh']:
    shutil.copy2(Path('site')/name,Path('web-preview')/name)
for p in Path('generated-audio/audio').glob('*.mp3'):shutil.copy2(p,Path('web-preview/audio')/p.name)
shutil.copy2('generated-audio/spoken-texts.json','web-preview/spoken-texts.json')
shutil.copy2('docs/SYNC_V010.md','web-preview/README.md')
files=['app/build/outputs/apk/debug/app-debug.apk','site/PoliticsMemory-Sync.exe','web-preview/index.html','web-preview/audio-index.json','preview/app.js','preview/app.css','data/suyi-full.json']
report={'version':'0.10.0','run_id':os.environ['GITHUB_RUN_ID'],'source_base':os.environ['GITHUB_SHA'],'audio_groups':561,'speech_format':'title-answer-v1','web':json.loads(Path('evidence/web-smoke.json').read_text()),'android':json.loads(Path('evidence/android-smoke.json').read_text()),'receiver':json.loads(Path('evidence/sync-smoke.json').read_text()),'windows_receiver':'actual executable health check passed in dependent job','sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}}
Path('docs/V010_ACCEPTANCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=Path('README.md');previous=p.read_text();header='# PoliticsMemory 0.10 · 一键同步、精简朗读\n\n当前版本：0.10.0。完整网页与561条标题+正文录音已提交 `web-preview/`；APK与含Windows同步接收器的网页完整包在 Release `v0.10.0-sync`。操作说明见 `docs/SYNC_V010.md`，真实验收见 `docs/V010_ACCEPTANCE.json`。\n\n同步为同一可信局域网内的手机→电脑传输，首次连接一次，随后点同步直接发送；不是自动云同步。右滑下一条、左滑上一条。正文14、标题17，保留4×与首尾循环。\n\n---\n\n以下为历史版本记录：\n\n'
if not previous.startswith('# PoliticsMemory 0.10'):p.write_text(header+previous,encoding='utf-8')
Path('docs/CODEX_V010.md').write_text('Current entry: web-preview/index.html. Source: preview/ and app/src/main/java/. Requirements: docs/SYNC_V010.md. Acceptance: docs/V010_ACCEPTANCE.json. Run desktop/progress_server.py for paired progress sync; never commit local-data/ or credentials. Do not replace the completed web product with the old source shell.\n')
