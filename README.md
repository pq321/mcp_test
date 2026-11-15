# 闪背 · 当前版本 v0.12.2

`main` 已合入四项背诵改动和固定签名安装修复，不再停留在 v0.11。当前代码、开发预览与完整网页必须使用同一份资料和学习资源索引。

## 唯一当前入口

- Android：v0.12.2「闪背」正式签名 APK 已在当前 ChatGPT 交付会话提供下载，GitHub Release 中的 [v0.12.1](https://github.com/pq321/mcp_test/releases/tag/v0.12.1-stable-install) 是旧安装包。v0.12.2 应用 ID 仍为 `org.vector.politicsmemory.stable`，版本号递增并沿用 v0.12.1 的正式签名，可覆盖安装 v0.12.1；不能覆盖不同应用 ID 的 v0.11。
- 完整网页：[`web-preview/index.html`](web-preview/index.html)，保留旁边 `audio/`。可直接离线打开，或运行同目录 `start-sync.cmd`。
- 电脑完整包：Release [`v0.12.1-stable-install`](https://github.com/pq321/mcp_test/releases/tag/v0.12.1-stable-install) 中的 `PoliticsMemory-v0.12.1-web.zip`。包含原561条录音及 Windows 同步接收器。
- 开发预览：[`preview/index.html`](preview/index.html)，使用同一版四项功能；不要复制旧 Release 中的 HTML 覆盖当前页面。
- 在线预览只有在 GitHub Pages 实际部署成功后才有效；部署状态见 `Current study delivery` 工作流，不把仓库上传当成在线部署。

已有离线网页版应先备份原目录，解压新版到原来的使用位置；使用原浏览器、原网址/文件入口，**不要清除网站数据或 localStorage**。更新代码本身不会自动把不同网址的浏览器存储搬到一起。

## 本轮限定的四项功能

1. 资料：可折叠的「苏一 → 马原／毛中特／新思想／史纲／思修 → 原目录」。「错题」「时政」保留原入口。其他老师仅在真正发布其资料包后出现，没有空占位。
2. 声音：倍速菜单4×下面是默认折叠的「声音」，展开后全局单选并记住。录音由 Codex 制作发布，手机只手动同步、选择、播放。没有逐知识点设置，当前内置只有原默认声音。
3. 背诵：冷启动默认回忆，点击正文循环「回忆 → 完整展示 → 挖空 → 回忆」。翻卡、评分、播放器不误触显示切换。
4. 标注：浅黄底加粗为核心必背，红色加粗为易混区别，蓝色为条件/否定/逻辑限定，标题虚线表示做题错题标记历史。挖空与标注单独维护，不改知识原文。

原561组ID、正文、问题、录音、评分算法、字号、手势方向、连续播放和手动同步原则保持不变。手指左滑下一条，右滑上一条，首尾循环；只点击同步才交换文件。

## 资料、声音与进度

Codex 发布规范见 [`docs/STUDY_CONTROLS_V012.md`](docs/STUDY_CONTROLS_V012.md)，入口为 `scripts/publish_study_resources.py`。按原文件ID更新私有 Drive 的 `content-update.zip`，不要覆盖 `progress.json`。新来源使用独立稳定pack_id和全局唯一card_id。

561组已有原文锚定的首版挖空和颜色标记；课程上下文来自用户提供的课程文字稿。相关上下文不等于老师逐条明确划重点，原稿的 `RAW_ASR_UNVERIFIED` 标识不升级为逐字终审。原文内容质量边界仍见 [`docs/CONTENT_AUDIT_V08.md`](docs/CONTENT_AUDIT_V08.md)。

新旧 Android APP 不自动共享私有数据库。旧进度迁移：旧版手动同步并确认云端文件真实上传，新版关联同一进度文件与内容包后手动同步，核对评分、错题和位置后再决定是否删除旧版。不要先卸载旧版。

## 发布与签名

正式版本必须保持 `org.vector.politicsmemory.stable` 和原正式签名私钥，递增 versionCode。密钥只存私有位置，不能提交到源码、公开 Release 或普通缓存；缺少密钥必须停止签名，不能临时生成替代。公开 `docs/STABLE_SIGNING_CERT.pem` 仅为证书。

四项功能验收见 [`docs/V012_ACCEPTANCE.json`](docs/V012_ACCEPTANCE.json)，并存安装验收见 [`docs/INSTALL_FIX_V0121_ACCEPTANCE.json`](docs/INSTALL_FIX_V0121_ACCEPTANCE.json)。这些模拟器检查不代替实体 OPPO K5 和真实 Google Drive 上传验收。

历史说明：[v0.11 手动同步](docs/DRIVE_MANUAL_V011.md)、[手势约定](docs/GESTURE_V0101.md)、[原极简界面](docs/MINIMAL_V09.md)。历史文档中的「当前版本」和旧下载入口不代表本版。
