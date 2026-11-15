# PoliticsMemory v0.11 | 手动 Google Drive 同步与 Codex 知识包发布

## 不变的原则

- 手机学习、评分、音频、错题全部支持离线。
- **只有主动点击「同步」才读取或写入云端文件**；不设后台工作、定时同步、打开时自动同步。
- 只显示原来的一个「同步」入口。长按这个入口可以重新关联文件。
- 不改变之前 v0.10.1 的手指滑动方向、三档评分、字体或极简排版。
- 程序更新仍通过 GitHub Releases；**知识数据更新不用安装 APK**。

## 零成本实现与首次连接

不需要 Google Cloud OAuth Client ID、API Key 或服务器。Android 使用 Android 官方 **Storage Access Framework (SAF)**；仅当 Google Drive 的 Android 文件提供器在系统选择器里可见且提供文件读写功能时，才能实现下面的远程同步。请先在手机安装并登录 Google Drive，使用与你的 Drive 同步目录相同的账号。

Google Drive 已预置私有文件夹 `PoliticsMemory_手动同步与资料更新`。其中有 `progress.json` 和 `content-update.zip`。文件夹和两份文件的实际 Drive ID 不应硬编码进公开 GitHub 仓库；Codex 应通过已连接的 Google Drive 检索它们，**读取当前文件 ID 后原位更新**，不能删除重建。
首次在手机点击「同步」，依次通过系统文件选择器从上述 Google Drive 文件夹选择 `progress.json`（需读写权限）和 `content-update.zip`（读取权限）。APP 保存的是用户授予的两个文件权限，不保存 Google 密码、OAuth Token 或云端管理员权限。以后只点一次「同步」，才会把本机与所选进度文件进行合并，再按需导入知识更新。

如果 Android 的系统文件选择器没有出现 Google Drive，说明当前手机/Google Drive 版本未提供所需文件访问途径；**不能将本地选中的文件冒充云端同步成功**。这时可保留旧版局域网接收器，或在手机提供 Google Drive 文件提供器之后重新关联。尚未在实体 OPPO K5 完成云盘文件提供器兼容性测试。

Google Drive 的文件提供器可能在后台上传写入的文件。APP 验证的是本机所选文档可回读，**不等于已收到 Google 云端的服务器回执**。界面据此只提示“文件已更新，云盘上传由 Google Drive 完成”。断网或云盘尚未上传完成时，以 Drive 自己的同步状态为准。

## 电脑同步

推荐安装 Google Drive for desktop（免费额度内），在电脑端镜像/挂载同一文件夹。首次运行网页包里的 `start-sync.cmd`，选择这个电脑上的 Google Drive 同步文件夹。接收器的 API 凭据只在本机 `local-data/` 中，**不会放进 Google Drive**；网页点击「同步」时，接收器才读写 Drive 同步文件夹中的 `progress.json`，同时检查 `content-update.zip`。两台设备可不在同一 Wi-Fi，云端文件由 Google Drive 客户端各自上传/下载。

如果还未安装 Google Drive for desktop，原局域网版本可继续使用，但无法声称已经具备异地 Drive 同步。

## Codex 增删改背诵知识点

Canonical source：`data/suyi-full.json`。

1. Codex 更改该 JSON 的 `cards`，新增知识组分配全局唯一且稳定的 `id`；修改一组要增加该组的 `revision`；删除时从新版全文包中移除该组，但不要复用它的 ID。`pack_revision` 必须递增。
2. 使用 `scripts/publish_content_update.py` 比较旧版与新版（`--before`、`--after`），提供新增/改写“标题+正文”的新录音 `--audio-dir`，输出 `content-update.zip`。只包含**新增或更改的MP3**，不重复打包原有561条。
3. 校验完成后通过已连接的 Google Drive 连接器 **原位替换** 上述 `content-update.zip`（同一个文件 ID，不要删除重建）。可以通过 Google Drive update_file 或原位覆盖的文件工具更新。
4. 手机下一次主动点击「同步」，APP 对知识包的结构、音频内容哈希和文件哈希先做校验；新版 `pack_revision` 更高才使**整包所列知识组**成为有效集合。新增入列、修改保留历史并标记待复核、删除仅从复习队列隐藏并保留事件历史。旧内置素材包不会覆盖更高版本。
5. 电脑网页版点击「同步」时同样可以更新本地浏览器的知识组；修改后的音频可由桌面接收器从同步包中按需读取。

### 小心：不要把整个学习进度上传到公共 GitHub

Drive `progress.json` 和云端连接信息都属于个人隐私数据，保持 Drive 私有权限。只有原有项目代码、审核后的知识包发行说明可以进入 GitHub。源仓库当前可见性可能是 public，请先确认苏一资料的授权情况；不要将个人学习记录或 Google 账号凭据提交。

## 数据安全边界

- 更新新资料时，稳定 card ID 与评分事件 ID 永不重复利用。删除知识点只软停用；原评分历史不删除。
- 改动答案会标记待复核。新增知识点初始为未学。
- 云端进度用事件唯一 ID 合并，按时间选择较新每组评分，保留错题标记/取消标记的最近操作。
- 手机在覆盖远端文件前另存上一次读取的状态，本次写入后校验回读。发生错误不把同步描述为成功。
- **跨设备恰好同时写入 Drive 文档**仍可能导致冲突副本；这是普通云盘同步文件的限制，不是强一致事务数据库。个人使用建议两端分时点击同步。需要严格事务的多端并发需另做服务器或使用 Drive API 条件写入。

## 非应用更新范围

这轮不增加用户中心、云账号登录界面、不改变复习交互、不增加后台定时任务。同步功能的真实 Drive provider 行为需要在 OPPO K5 上首次选择文件后验证；模拟器只能验证 SAF 文件读写逻辑，不能代替实际 Google Drive 上传完成。
