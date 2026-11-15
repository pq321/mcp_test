#!/usr/bin/env python3
"""Export a readable per-card editorial audit. No source or user-state mutations."""
import argparse,collections,hashlib,html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def render(answer,marks,cloze=False):
    source=answer.encode('utf-16-le');at=0;out=[]
    for m in marks:
        start,end=m['start']*2,m['end']*2
        out.append(html.escape(source[at:start].decode('utf-16-le')))
        text='［　　］' if cloze and m['cloze'] else m['text']
        out.append('<span class="'+('blank' if cloze and m['cloze'] else m['kind'])+'">'+html.escape(text)+'</span>');at=end
    out.append(html.escape(source[at:].decode('utf-16-le')))
    return ''.join(out)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='deliverables');args=parser.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    pack=json.loads((ROOT/'data/suyi-full.json').read_text());resources=json.loads((ROOT/'data/study-resources.json').read_text());cards=pack['cards'];sections=[]
    for n,c in enumerate(cards,1):
        a=resources['annotations'][c['id']];assert a['revision']==3
        marks=a['marks'];assert a['recall_goal'] and a['retained_cues']
        assert hashlib.sha256(c['answer'].encode()).hexdigest()==a['answer_sha256']
        last=0
        for m in marks:
            assert m['start']>=last and c['answer'].encode('utf-16-le')[m['start']*2:m['end']*2].decode('utf-16-le')==m['text'];last=m['end']
        assert any(m['cloze'] for m in marks)
        sections.append('<details class="card"><summary>'+str(n)+'. '+html.escape(c['path'][0]+'｜'+c['title'])+'</summary><p><b>背诵目标：</b>'+html.escape(a['recall_goal'])+'</p><p><b>保留提示：</b>'+html.escape(a['retained_cues'])+'</p><p class="muted">'+html.escape(c['question'])+'</p><div class="columns"><section><h3>挖空版</h3><div class="answer">'+render(c['answer'],marks,True)+'</div></section><section><h3>完整原文与标注</h3><div class="answer">'+render(c['answer'],marks)+'</div></section></div><small>'+html.escape(c['id'])+'</small></details>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>政治背诵·561卡逐卡挖空 R2</title><style>
body{max-width:1180px;margin:28px auto;padding:0 20px;font:16px/1.8 system-ui,sans-serif;color:#27332e;background:#f6f7f5}h1{line-height:1.4}header{margin-bottom:24px}.card{background:white;border:1px solid #d9dfda;border-radius:6px;margin:10px 0;padding:14px 18px}summary{font-weight:700;cursor:pointer}.columns{display:grid;grid-template-columns:1fr 1fr;gap:28px}.answer{white-space:pre-wrap;overflow-wrap:anywhere}.core{background:#fff0b3;font-weight:700}.confusion{color:#b23b3b;font-weight:700}.condition{color:#286a9a}.blank,.muted,small{color:#65716b}input{box-sizing:border-box;width:100%;padding:12px;font:inherit;border:1px solid #b5c2b8;border-radius:5px}button{margin:8px 8px 0 0;padding:7px 14px;cursor:pointer}@media(max-width:760px){.columns{grid-template-columns:1fr}body{padding:0 12px}}[hidden]{display:none!important}</style><header><h1>561张卡：逐卡挖空与标注 R2</h1><p>每张卡分别确定背诵目标和保留线索。黄底加粗＝核心必背；红色加粗＝易混区别；蓝色＝保留的条件与限定。此页是对照稿，不是新的APP界面，也不修改学习进度。</p><p>全部原文保持不变。本轮为原卡内容的背诵编辑，不等于新增课程重点认证或原文事实校订。</p><input id="q" placeholder="搜索卡片标题、原文、背诵目标"><button onclick="fold(true)">展开筛选结果</button><button onclick="fold(false)">全部收起</button><span id="count">561张</span></header>'''+''.join(sections)+'''<script>const cards=[...document.querySelectorAll('.card')];document.getElementById('q').oninput=e=>{const q=e.target.value.trim().toLowerCase();let count=0;for(const c of cards){c.hidden=!c.textContent.toLowerCase().includes(q);if(!c.hidden)count++}document.getElementById('count').textContent=count+'张'};function fold(open){for(const c of cards)if(!c.hidden)c.open=open}</script></html>'''
    (out/'PoliticsMemory-cloze-R2-review.html').write_text(page,encoding='utf-8')
    report={'edition':'cloze-r2-20261115','annotation_revision':3,'cards':len(cards),'subjects':dict(collections.Counter(c['path'][0] for c in cards)),
            'cloze_spans':sum(bool(m['cloze']) for a in resources['annotations'].values() for m in a['marks']),
            'marks_by_kind':dict(collections.Counter(m['kind'] for a in resources['annotations'].values() for m in a['marks'])),
            'per_card_goal_and_cues':'561/561','all_exact_spans_nonoverlapping':'PASS','original_pack_sha256':hashlib.sha256((ROOT/'data/suyi-full.json').read_bytes()).hexdigest(),
            'resources_sha256':hashlib.sha256((ROOT/'data/study-resources.json').read_bytes()).hexdigest(),
            'scope':'Only explicit cloze/highlight metadata; no original text, runtime, audio, progress, source or voice changes',
            'limits':['Original wording preserved, not a factual correction','Not a fresh teacher-emphasis certification','Physical phone sync not inspected']}
    (out/'CLOZE_R2_ACCEPTANCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
