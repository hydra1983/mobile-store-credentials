# Mobile Store Credentials

`mobile-store-credentials` is an agent skill for preparing iOS and Android release credentials when onboarding an app, migrating a build setup, or updating an existing store listing. It checks what the project expects, identifies which credentials can be reused, and lists missing items, configuration variables, and next steps.

- **iOS** — Distribution identities (`.p12`), App Store provisioning profiles, and App Store Connect Team Keys (`.p8`). [iOS reference](references/ios.md)
- **Android** — Upload keystores, upload certificate fingerprints, and Google Play publisher service accounts. [Android reference](references/android.md)

## Install

Run from your app repository to install for Codex in that project.

```sh
npx skills add hydra1983/mobile-store-credentials --skill mobile-store-credentials --agent codex
```

Add `--global` to make the skill available across projects. See the [Skills CLI reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md) for other supported agents and installation options.

## Use in Codex

Open your app repository in Codex and mention `$mobile-store-credentials` in a prompt. Use relative paths and app identifiers to identify the release target. Keep secret values out of the prompt.

**Check iOS credentials after a Bundle ID change**

```text
$mobile-store-credentials Check the production iOS release for apps/mobile
with Bundle ID com.example.fieldnotes. We have a distribution certificate
from another app on the same Apple Developer team. Check what can be reused,
what provisioning profile we need, and what upload permissions remain
unverified. Use read-only checks and dry-runs.
```

**Check signing for an existing Google Play listing**

```text
$mobile-store-credentials Review the Android release for com.example.fieldnotes.
Compare the configured upload keystore with the upload certificate fingerprint
in our release configuration. Locate the publisher service account configuration
and list any permissions to verify in Play Console. Use read-only checks.
```

The skill reports local findings and lists any platform permissions that still need confirmation. Its instructions are in [SKILL.md](SKILL.md).
