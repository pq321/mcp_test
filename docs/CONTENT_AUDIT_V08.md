# 苏一全科成组内容审计 · v0.8

审计对象：`data/suyi-full.json`；来源覆盖记录：`data/coverage.json`。

## 结构检查结果

- 全书正文：印刷第1—135页，PDF第6—140页；封面、目录、封底排除。
- 总知识组：561，稳定ID 561个，无重复ID。
- 马原127组、毛中特57组、新思想177组、史纲128组、思修72组。
- 每组均有三层目录、title、question、answer；当前全为 `type=group`。
- 每组有来源页码和处理状态；135个印刷页均有来源映射。
- 处理状态：276组 `STRUCTURED_TEXT_REORGANIZED`，285组 `VISUALLY_REORGANIZED`。
- 印刷第1—75页：按既有结构化底稿整理，核对2,596个结构叶节点，全部映射到知识组（2,596/2,596，未映射0）。
- 印刷第76—135页：逐页按原图重新组织，285组。
- 已知修订项及原图旁注保留在来源记录；老师技巧只有在有出处时才作为备注显示。

## 重要质量边界

这次审计证明的是**结构覆盖与数据完整性**，不是所有文字已经逐字人工终审。特别是第1—75页依赖既有结构化底稿；OCR、原图文字和最终答案仍可能存在细微转写问题。来源详情会区分两种处理状态，不将“覆盖100%”等同于“逐字正确100%”。

## v0.8 音频验收标准

- 每组单独生成一条普通话离线录音。
- 朗读顺序：知识点位置、知识点名称、回忆问题、完整答案、可选备注。
- `text_sha256` 覆盖上述完整朗读文本；`audio_sha256` 校验MP3字节。
- Android和网页端播放前都校验正文哈希；任何过期或错配音频必须阻止播放。
- 倍速范围0.75×—2.0×，不改变复习评分。

## 运行验证

```bash
python scripts/validate_pack.py data/suyi-full.json
python scripts/merge_audio_shards.py --pack data/suyi-full.json --shards audio-shards --out app/src/main/assets
python scripts/validate_audio.py data/suyi-full.json app/src/main/assets
python scripts/build_preview.py --pack data/suyi-full.json --audio-index app/src/main/assets/audio-index.json --audio-dir app/src/main/assets/audio --out site
```
