---
name: mobile-store-credentials
description: Inventory, validate, reuse, or plan acquisition of iOS and Android store release credentials for a target app. Use for distribution PKCS#12 identities, App Store provisioning profiles, App Store Connect Team Keys, Android upload keystores, and Google Play publisher service accounts, especially during app onboarding or migration.
---

# Mobile store credentials

1. Resolve the target application directory, platform and release variant. Read its actual release scripts, configuration and overrides to identify the iOS Bundle ID or Android package, store account or team, expected credential paths and variable names. Ask for only the identity, account or source details still missing after inspection. Use a source repo or credential path supplied by the operator. The examples use placeholder app identities, paths and variable names.
2. Read [iOS](references/ios.md) for Apple signing or upload credentials and [Android](references/android.md) for Play signing or upload credentials. Check the target first, then an eligible source. Keep signing, store upload authentication and platform permissions distinct.
3. Report one row per credential with its source, target path and variable names, status, evidence, and next command or action. Use `可复用` / reusable, `待核实` / needs verification, `错配` / mismatch, or `缺件` / missing. A missing target can have a locally verified source candidate. Record local file presence, local identity checks, and platform permissions separately. Missing evidence stays pending. State the comparison basis, especially whether a fingerprint or permission came from local policy or the platform.

Use the project's existing read-only check or dry-run when it fits. Confirm what the command checks before treating its output as evidence. A plan-only dry-run can validate command inputs and output paths. An existing local signing preflight can validate a matching key, certificate and profile. Platform status needs separate evidence.

Keep passwords, private keys and raw credential files out of prompts, tool output, logs and review records. Pass secrets to local tools through a protected prompt, environment or file descriptor. Read trusted configuration as data with the project's loader. Keep decrypted material in local process memory and report only results. Check the target's ignore rules and preserve existing files. Dry-runs can use fresh private temporary paths. Use fixtures for destructive or negative cases.

Credential preparation can be planned without signing a build, registering devices, installing profiles, or changing a provider. Execute only actions authorized by the current task. For a read-only or dry-run request, give the next write command as guidance and keep it unexecuted.
