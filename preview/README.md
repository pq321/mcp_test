# 政治背诵 App：离线网页预览

实际入口：`preview/index.html`。

本预览包含93条思修重点K及93段预生成MP3，音频拆为 `preview/audio/chunk-01.js` 至 `chunk-09.js`。把整个 `preview/` 文件夹保存在一起即可离线使用。网页的熟悉度记录存在浏览器本地存储，和Android APK分开。

## 在Codex中打开

从仓库根目录执行：

```bash
python3 -m http.server 8765 --directory preview
```

然后使用Codex可用的浏览器预览工具访问 `http://127.0.0.1:8765/`。

只验收浏览器实际页面：复习、资料三级展开、统计、播放、左滑上一条、右滑下一条、答案跨卡保留。不要未经授权改动工程或运行Android编译。

提醒：GitHub网页中的HTML代码预览并非可运行页面，应在本地HTTP服务器中打开。