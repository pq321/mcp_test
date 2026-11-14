# PoliticsMemory v0.8 — Web source directory

This directory contains the editable web source, not the final offline package.

**Use `../web-preview/` to run or inspect the complete built preview.** The `web-preview/` directory is committed with all 561 MP3 files, the complete audio index, and a ready-to-open `index.html`.

Source files here:
- `index.html`: development HTML shell
- `app.js` / `app.css`: study UI and interaction logic
- `full-data.js`: generated knowledge pack source
- `audio-index.js`: development placeholder; it is not the complete release audio manifest

To rebuild the complete preview from source and verified audio assets, run from the repository root:

```bash
python scripts/build_preview.py \
  --pack data/suyi-full.json \
  --audio-index app/src/main/assets/audio-index.json \
  --audio-dir app/src/main/assets/audio \
  --out site
```

The generated `site/` directory contains `index.html`, `audio-index.json`, and `audio/` with all MP3 files. Keep the audio folder beside the HTML file.
