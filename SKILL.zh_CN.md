# 移动应用商店发布凭据

[English](SKILL.md) | 中文简体

接入新应用、迁移构建或更新已有应用时，用这个 Skill 检查和准备 iOS、Android 的商店发布凭据。

先读应用的正式发布脚本和配置，找出 Bundle ID 或 Android 包名、商店团队或账号，以及凭据路径和环境变量。先查目标应用已有的文件，再看能否从其他项目复用。

- [iOS 指南](references/ios.md)涵盖 `.p12` 文件、App Store 描述文件和 App Store Connect Team Key。
- [Android 指南](references/android.md)涵盖上传 keystore、证书指纹和 Google Play 服务账号。

逐项写清楚应用需要什么、查了什么、下一步怎么做，并标为「可复用」「待核实」「错配」或「缺件」。注明核对依据来自本地文件、项目配置还是商店后台。商店权限和本地检查结果分开记录。

只读任务用本地检查或 dry-run。创建密钥或更改商店设置前，确认本次操作已获授权。保护好密码和私钥，别放进提示或日志，也别覆盖现有凭据文件。
