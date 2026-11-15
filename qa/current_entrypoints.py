#!/usr/bin/env python3
"""Check only the user's four approved controls at the delivered web entrypoints."""
import functools, http.server, json, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence' / 'current-delivery'

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    report = {'entrypoints': {}, 'user_data': 'Synthetic acceptance records only; no real progress accessed'}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width':350, 'height':790}, reduced_motion='reduce')
            page = context.new_page()
            errors, sync_calls = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: sync_calls.append(r.url) if '/api/' in r.url else None)
            before = None
            for label, path in [('source','preview/index.html'), ('repository','web-preview/index.html'), ('package','site/index.html')]:
                page.goto(f'http://127.0.0.1:{server.server_port}/{path}', wait_until='load')
                page.wait_for_function('Boolean(window.PoliticsMemory)')
                assert page.evaluate('PoliticsMemory.getCards().length') == 561
                assert page.evaluate('PoliticsMemory.getState().app.mode') == 0
                if before is not None:
                    assert page.evaluate('PoliticsMemory.getState().events.length') == before
                page.locator('[data-tab="books"]').click()
                parent = page.locator('details[data-open="P:politics-suyi-full"]')
                assert parent.count() == 1
                if parent.evaluate('(e)=>e.open'):
                    parent.locator(':scope > summary').click()
                assert parent.locator('[data-open^="S:"] > summary').count() == 5
                assert not parent.locator('[data-open="S:马原"] > summary').is_visible()
                page.screenshot(path=str(OUT / f'{label}-catalogue-collapsed.png'))
                parent.locator(':scope > summary').click()
                assert parent.locator('[data-open="S:马原"] > summary').is_visible()
                assert page.get_by_text('腿姐', exact=True).count() == 0
                page.screenshot(path=str(OUT / f'{label}-catalogue-expanded.png'))
                page.locator('[data-tab="review"]').click()
                assert page.locator('#recallPrompt').is_visible()
                page.locator('#recallPrompt').click()
                assert page.locator('#answer').get_attribute('data-mode') == 'complete'
                assert page.locator('#answer .study-core').count() > 0
                page.screenshot(path=str(OUT / f'{label}-complete.png'))
                page.locator('#reveal').click()
                assert page.locator('#answer').get_attribute('data-mode') == 'cloze'
                assert page.locator('.study-blank').count() > 0
                page.screenshot(path=str(OUT / f'{label}-cloze.png'))
                page.locator('#reveal').click()
                assert page.locator('#recallPrompt').is_visible()
                page.get_by_label('播放速度', exact=True).click()
                assert page.locator('#dialog [data-speed]').last.get_attribute('data-speed') == '4'
                assert not page.locator('#voiceOptions').evaluate('(e)=>e.open')
                page.locator('#voiceOptions summary').click()
                page.screenshot(path=str(OUT / f'{label}-voice.png'))
                page.locator('[data-voice="default"]').click()
                assert page.locator('#recallPrompt').is_visible()
                if before is None:
                    page.locator('#reveal').click()
                    page.locator('[data-rate="yes"]').click()
                    page.wait_for_timeout(200)
                    before = page.evaluate('PoliticsMemory.getState().events.length')
                    assert before == 1
                report['entrypoints'][path] = 'PASS: source parent, five subjects, three modes, emphasis, global voice, retained progress'
            assert not errors, errors
            assert not sync_calls, sync_calls
            report['no_automatic_sync'] = 'PASS'
            report['same_origin_existing_rating_retained'] = 'PASS'
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    (OUT / 'entrypoints.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    main()
