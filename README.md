# PoliticsMemory 0.11：手动同步与 Codex 知识包更新

目前保留一个「同步」入口，严格只在点击时同步。首次选择两个 Google Drive 文档（进度 JSON + 内容 ZIP），更新包由 Codex 在 Drive 原位发布。电脑同步目录使用 Google Drive Desktop。当前不具备后台自动同步，Google Drive 真实端到端上传仍需在用户设备验证。详情：docs/DRIVE_MANUAL_V011.md。

---

# 当前版本 0.10.1 · 滑动方向已对调

本次只反转0.10.0的手指滑动行为。最新说明：`docs/GESTURE_V0101.md`；验收：`docs/V0101_ACCEPTANCE.json`；完整网页：`web-preview/index.html`；安装包：Release `v0.10.1-gesture`。以下旧版方向说明不再适用。

---

# PoliticsMemory 0.10 · 一键同步、精简朗读

当前版本：0.10.0。完整网页与561条标题+正文录音已提交 `web-preview/`；APK与含Windows同步接收器的网页完整包在 Release `v0.10.0-sync`。操作说明见 `docs/SYNC_V010.md`，真实验收见 `docs/V010_ACCEPTANCE.json`。

同步为同一可信局域网内的手机→电脑传输，首次连接一次，随后点同步直接发送；不是自动云同步。右滑下一条、左滑上一条。正文14、标题17，保留4×与首尾循环。

---

以下为历史版本记录：

# PoliticsMemory 0.9 · 极简成组背诵

完整网页：`web-preview/index.html`（包含561条录音）。Android APK 和网页完整ZIP在 Releases 的 `v0.9.0-minimal`。本次要求与验收见 `docs/MINIMAL_V09.md` 和 `docs/V09_ACCEPTANCE.json`。

# 政治背诵 · PoliticsMemory v0.8

苏一全科成组背诵工具。**复习单位是一组完整知识点，不是孤立短句。** 本版同时提供桌面网页预览和原生 Android APK。

## 当前内容

- 五科：马原、毛中特、新思想、史纲、思修。
- 依据苏一正文印刷第1—135页（PDF第6—140页）整理，共 **561 组**。
- 每组包含三层位置、知识点名称、回忆问题、完整答案、来源和可选备注。
- 页面顺序：位置 → 名称 → 问题 → 分隔线 → 答案 → 组末小备注。
- 复习方法沿用“忘记／模糊／记住”，左滑上一组、右滑下一组，保留跟手滑动与回弹动画。
- 资料目录紧凑显示五科，另有“错题”和“时政”入口。做题错题由用户单独标记；背诵忘记／模糊不会自动冒充做题错误。时政内容等待用户提供。
- 底部只保留复习、资料、统计；素材导入、备份、每日目标和倍速设置放在工具菜单。
- 离线录音覆盖全部知识组，播放前校验位置、名称、问题、答案和备注的 SHA-256；倍速支持 **0.75×—2.0×**。

## 内容质量边界

全科覆盖与逐字终审是两件事：印刷第1—75页按既有结构化底稿的节点分组，并已检查全部结构叶节点均被纳入；印刷第76—135页按原图重新整理。**这不等于全书逐字终审，也不代表所有 OCR 文字已经人工逐字核对。** 页面来源状态会明确区分，不把自动整理说成终审。

## 网页预览

**完整离线网页成品已提交到仓库的 `web-preview/` 目录**，不是只有源码：

- [打开完整网页成品目录](web-preview/)
- [网页入口 HTML](web-preview/index.html)
- [561组音频索引](web-preview/audio-index.json)
- `web-preview/audio/`：561条逐组 MP3 录音
- `web-preview/README.md`：离线运行说明

下载或克隆整个 `web-preview/` 目录后，保持 `index.html`、`audio-index.json` 和 `audio/` 的相对位置不变，使用浏览器打开 `index.html` 即可离线使用。Codex 可以直接检查该目录中的完整网页成品、数据和录音索引。

GitHub Pages 在线地址（启用并部署成功后）：[PoliticsMemory 网页预览](https://pq321.github.io/mcp_test/)。若 Pages 尚未启用，需要仓库管理员在 Repository → Settings → Pages → Build and deployment 中选择 **GitHub Actions**，再运行 `Build and deploy PoliticsMemory v0.8`。

学习记录保存在当前浏览器 `localStorage`，不会上传；更换浏览器或清理网站数据前请先导出 JSON 备份。源码开发入口位于 `preview/`，完整网页由 `scripts/build_preview.py` 生成。

## Android APK

推送到 `main` 后，GitHub Actions 工作流 **Build and deploy PoliticsMemory v0.8** 会：

1. 按五科并行生成整组普通话录音；
2. 合并并校验全部561条音频及文本哈希；
3. 将完整资料和录音打包进原生 APK；
4. 构建桌面网页预览并部署 GitHub Pages。

在仓库 Actions 页面下载 artifact `politics-memory-debug-apk`，文件名为 `app-debug.apk`。这是可安装的 debug APK，不是已签名的商店发布包。

## 本地构建

要求 Java 17、Android SDK 35、Gradle 8.9、Python 3.11、ffmpeg：

```bash
python scripts/validate_pack.py data/suyi-full.json
python -m pip install 'piper-tts[zh]==1.8.0'
python scripts/generate_audio.py --pack data/suyi-full.json --model .voice-cache/zh_CN-chaowen-medium.onnx --out app/src/main/assets
python scripts/validate_audio.py data/suyi-full.json app/src/main/assets
cp data/suyi-full.json app/src/main/assets/suyi-full.json
gradle --no-daemon :app:assembleDebug
```

Piper 模型只在构建机器上使用；APK 只包含生成后的 MP3，不包含语音模型。App 不请求 INTERNET 权限、不登录、不联网。

## 学习记录与隐私

- Android 学习记录保存在本机 SQLite；网页学习记录保存在当前浏览器。
- Android 与网页进度互不自动同步。需要迁移时，主动导出／导入 JSON 备份。
- 备份包含资料、评分、错题标记、复习日志与倍速偏好；导入较旧备份不会覆盖较新的本地评分。
- 旧版93条短卡记录保留在备份中，但不与561组新卡混排，也不会自动换算成新卡掌握状态。
- 不提交用户学习记录、原书扫描件、密钥或签名文件。

## License / voice

语音模型来自 [Piper zh_CN-chaowen-medium](https://huggingface.co/rhasspy/piper-voices/tree/main/zh/zh_CN/chaowen/medium)，模型卡标注 CC0 数据来源。生成音频仅用于本项目离线学习。每条录音由本项目的知识组文本合成，不使用课程录音或原书音频。
