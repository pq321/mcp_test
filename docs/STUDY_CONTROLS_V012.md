# PoliticsMemory v0.12 · 仅四项增量

基线：`f9b0d727abb2b59aabe4cf4e4ce6e7260f2d0cc7`。不修改现有561组正文/问题/ID、561条原录音、评分算法、滑动方向、字号、连续播放及手动同步原则。

## 使用

- 资料页增加可折叠的“苏一”，下面仍是原五科、章节、考点和知识组。其他来源只有实际发布资料后才出现，无空占位。来源名称来自数据索引。
- 点击播放器倍速：0.75×—4×之后为折叠的“声音”。展开后是全局单选，选择会保存在本机，所有后续播放使用同一声音。不提供逐组音色设置或手机制作录音功能。
- 冷启动默认隐藏答案。点击正文依次为“回忆 → 完整展示 → 挖空 → 回忆”。原揭晓按钮同样循环，滑动/评分/播放控件不触发显示切换。不同页面和翻卡延续当前显示状态；重开重新隐藏。
- 浅黄底+加粗：核心；红色加粗：易混区别；蓝色：条件/否定/逻辑限定；标题底部虚线：有做题错题标记历史。忘记/模糊评分不是做题错题。
- 切换声音时从当前组录音起点重播，保持暂停/播放状态、倍速和队列。某音色未覆盖当前组时，明确提示并使用正文匹配的默认声音；绝不把旧文字录音当新版答案播放。

本次没有制作新的生产音色：菜单起初只有原默认声音。测试使用的fixture音色不进入正式APK。Codex发布其他声音后，手机主动同步后才显示。

## 挖空与标注来源

561组使用独立`data/study-resources.json`旁注，不改`data/suyi-full.json`。锚点是原文精确片段，附正文SHA-256和UTF-16位置。修改目录/声音/旁注不增加知识正文revision，不将掌握状态变成待复核。正文变更时旧标记校验失效，不错位挖空。

本批为编辑选取的概念、对应关系、成套要点、易混区别词，结合用户Library腿姐课程逐课文字稿的相关上下文；可追溯的旁注记录课程ID和时间段。1012个标记有相关课程上下文，**不等于1012处均为老师明确划重点或已逐字人工校对**。课程原稿标识为RAW_ASR_UNVERIFIED，保留此边界。未把课程全文/用户学习记录上传公共仓库。苏一原先前75页尚未逐字终审的状态不因本次变动而升级。

## Codex 发布入口

`python scripts/publish_study_resources.py --help`

1. 保留原资料的稳定card ID。新资料包使用自己的稳定pack_id和全局唯一card ID。来源名称在`study-resources.json.sources`设置。
2. 发布资料时使用`--pack <完整资料包.json>`；一个包是该来源的完整有效集合。更高pack_revision中未列出的卡仅停用，原评分/事件保留。空的新版本停用该来源，不影响其他来源。不要把局部几条卡冒充完整资料包。
3. 声音是独立资源，选项名称、版本和录音索引在`voices`中；单独改声音不修改知识正文。现有默认音频仍内置，新增声音文件放入`audio/<voice_id>/<revision>/<card_id>.mp3`。不可复用同一版本路径覆盖不同字节。
4. 用`--voice-id`、`--voice-name`、`--voice-revision`、`--voice-dir`接入Codex已制作的MP3；用`--text-pack`提供对应正文（仅用于绑定，不更新手机知识正文）。索引只校验文件完整性/文本版本，不能替代人工试听确认实际朗读内容。
5. 旁注/来源/声音分别维护revision；更改相应条目必须递增。提供`--previous-resources`校验版本变化，`--save-resources`保存本次完整资源索引用于下次发布。
6. 输出仍命名为`content-update.zip`，通过已授权Google Drive连接**原位更新既有文件**。不得删除重建文件ID，也不要更改`progress.json`。手机仍用原“同步”按钮，无后台同步。

示例（路径均为Codex本地文件，不是手机设置）：

```bash
python scripts/publish_study_resources.py \
  --resources data/study-resources.json \
  --previous-resources private-cache/last-published-resources.json \
  --text-pack data/suyi-full.json \
  --voice-id clear_female --voice-name 清晰女声 --voice-revision 1 \
  --voice-dir private-cache/new-voice-mp3 \
  --audio-root private-cache --save-resources private-cache/current-resources.json \
  --out private-cache/content-update.zip
```

新文件须包含`update.json`、`study-resources.json`，以及可选的`packs/<pack_id>.json`与声音MP3。发布器保留**当前所有可选音色的完整文件集合**，确保手机跳过某次发布仍能同步。原内置561条不重复打包；接收端不重写已校验且未变化的文件。使用单个Drive ZIP意味着它不是按字节网络增量下载。

声音优先级：所选声音的当前文字匹配录音 → 默认声音当前文字匹配录音 → 明确不可播放。不制作假音色占位。删除声音用更高revision与retired=true；默认声音不可退役。

## 验收和范围边界

针对实际使用路径验证：目录折叠、三态点击、音色菜单、原手势/循环、评分与复习历史、资料包独立增删、真实MP3解析、暂停/倍速/自动下一条；旧版安装包原位升级不得丢评分。不新建广泛测试框架，不改其他版本工作流。

Android模拟器和本地Drive镜像不能代替实体OPPO K5和Google Drive提供器的真实服务器回写验证。新资源已内置到新版APK；本轮不触碰个人Drive进度。
