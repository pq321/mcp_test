# PoliticsMemory v0.12.1 安装修复

新版应用标识为 org.vector.politicsmemory.stable，桌面名称为「政治背诵·新版」。可与旧版并存，不必卸载旧版，不修改旧版数据。它不是对旧包的原位覆盖。

保留已验收v0.12的苏一目录、全局声音、三态背诵和重点标注；原文、录音、评分、手势、布局和手动同步不变。

旧进度：先在旧版点同步，确认进度文件已经真正上传，再在新版选择同一progress.json和content-update.zip并手动同步；核对评分、错题与背诵位置后才考虑删除旧版。新旧应用不会自动共享私有数据库。真实手机和Google Drive服务器上传未由本次模拟器验收替代。

签名使用独立的长期Release密钥，未放入源码或普通构建缓存。私钥恢复件只以公钥加密形式经过Actions，随后由所有者私有保管。公开docs/STABLE_SIGNING_CERT.pem仅为证书，不含私钥。

后续Codex发布：使用同一applicationId和原私钥，递增versionCode。设置PM_SIGNING_KEYSTORE为私有p12路径，PM_SIGNING_PASSWORD为私有密码，执行gradle :app:assembleRelease。GitHub自动构建须由所有者设置PM_STABLE_KEYSTORE_B64和PM_STABLE_KEYSTORE_PASSWORD这两个Secrets；当前连接器未设置这些Secrets。缺密钥须停止发布，不能重新生成替代。
