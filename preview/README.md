# 政治背诵 · 苏一全科预览

本目录是网页端源文件。正式离线预览由 `scripts/build_preview.py` 生成，内嵌完整 561 组数据和音频索引，并在 `audio/` 目录提供逐组 MP3。

- `index.html`：本地开发入口
- `app.js` / `app.css`：背诵与资料界面
- `full-data.js`：完整苏一知识组数据（由全科数据构建）
- `audio-index.js`：音频索引；CI 构建时由已校验的音频清单替换

本地开发：在仓库根目录执行 `python scripts/build_preview.py --pack data/suyi-full.json --audio-index app/src/main/assets/audio-index.json --audio-dir app/src/main/assets/audio --out site`，然后打开 `site/index.html`。音频目录必须与 `index.html` 同级。
