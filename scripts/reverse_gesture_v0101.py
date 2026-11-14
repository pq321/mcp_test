"""Invert the shipped v0.10 finger gestures; leave all study/media/sync logic intact."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
def change(path, replacements):
    p = root / path
    text = p.read_text(encoding='utf-8')
    for old, new in replacements:
        if old not in text:
            raise RuntimeError(f'Unexpected source at {path}: {old[:70]}')
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

change('preview/app.js', [
    ('PoliticsMemory v0.10 —', 'PoliticsMemory v0.10.1 —'),
    ('step(g.dx>0?1:-1,g.dx); // Right swipe -> next; left swipe -> previous.',
     'step(g.dx>0?-1:1,g.dx); // Finger x decreases -> next; finger x increases -> previous.'),
    ('const sign=dir<0?-1:1,dist=', 'const sign=dir>0?-1:1,dist='),
])
change('app/src/main/java/org/vector/politicsmemory/SwipePagerLayout.java', [
    ('swipe LEFT -> previous; swipe RIGHT -> next.', 'finger moves LEFT -> next; finger moves RIGHT -> previous.'),
    ('// +1 right gesture -> next; -1 left gesture -> previous', '// Physical movement sign, kept independent from the page index'),
    ('int target=(index+dir+count)%count;', 'int target=(index-dir+count)%count;'),
    ('ensureNeighbor(next,1,Math.max(1,getWidth()));\n        completeSwipe(1);',
     'ensureNeighbor(next,-1,Math.max(1,getWidth()));\n        completeSwipe(-1);'),
])
change('app/build.gradle', [('versionCode 6', 'versionCode 7'), ("versionName '0.10.0'", "versionName '0.10.1'")])
change('scripts/build_preview.py', [('PoliticsMemory v0.10 desktop preview', 'PoliticsMemory v0.10.1 desktop preview')])

# Reuse existing real-device/browser checks with the inverse physical gesture.
for name, first, second, old_key, new_key in [
    ('web_smoke.py', 'swipe(page,75,285)', 'swipe(page,285,75)',
     'right_next_left_previous_first_last_and_rating_wrap', 'finger_left_next_right_previous_first_last_and_rating_wrap'),
    ('android_smoke.py', "shell('input','swipe','200','1100','850','1100','280')", "shell('input','swipe','850','1100','200','1100','280')",
     'right_next_left_previous_first_last_loop', 'finger_left_next_right_previous_first_last_loop'),
]:
    p = root / 'qa' / name
    s = p.read_text(encoding='utf-8')
    assert s.count(first) == 2 and s.count(second) == 2, name
    s = s.replace(first, '__INVERSE_GESTURE__').replace(second, first).replace('__INVERSE_GESTURE__', second)
    s = s.replace(old_key, new_key)
    p.write_text(s, encoding='utf-8')
print('Applied gesture-only hotfix; content, font sizes, audio and sync unchanged.')
