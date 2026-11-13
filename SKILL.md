---
name: mobile-store-credentials
description: Check and prepare iOS and Android store release credentials when setting up, migrating, or updating an app.
---

# Mobile store credentials

English | [中文简体](SKILL.zh_CN.md)

Start with the app's production release scripts and configuration. Find the
Bundle ID or Android package, the store team or account, and the credential
paths and environment variables. Check the target app's files before looking
for a reusable credential from another project.

- [iOS](references/ios.md) covers `.p12` files, App Store provisioning profiles,
  and App Store Connect Team Keys.
- [Android](references/android.md) covers upload keystores, certificate
  fingerprints, and Google Play service accounts.

For each credential, report what the app expects, what you checked, and what to
do next. Mark it reusable, pending, mismatched, or missing. Say whether you checked
against local files, project configuration, or the store. Report store permissions
separately from local checks.

For read-only work, use local checks or dry-runs. Create keys or change store
settings only with authorization for that action. Keep secrets out of prompts and
logs, and preserve existing credential files.
