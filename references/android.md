# Android release credentials

## Upload signing identity

1. Resolve the production `applicationId` and Play Console app. For an existing app enrolled in Play App Signing, compare the candidate keystore's certificate with the **Upload key certificate** for that app. The **App signing key certificate** identifies Google's signing of the delivered APKs and is a different comparison for update tests. Use a trusted policy copy when the platform record is unavailable and label the result as a local comparison. Stop the reuse decision when the fingerprint baseline is missing or different. Preserve the incumbent upload key and direct any required reset to the Play account owner.
2. For a first release, check whether an upload identity was already registered or prepared. If one still needs to be created, use the target project's existing signing workflow or a `keytool` generation plan using placeholders. Keep generation for the authorized setup task.
3. Resolve the keystore, alias and password variable from the target configuration. Use the JDK that the project expects. For the example below, set `UPLOAD_STORE_PASSWORD` in the child environment through the project's config loader. Require the selected alias to be a `PrivateKeyEntry`. A `trustedCertEntry` can carry the correct public certificate and still lacks a signing key. Parse the SHA-256 fingerprint locally, normalize separators and case, compare to the known upload fingerprint, and emit only the entry type and match result. Record actual signing and any separate key password as untested unless independently verified.

```sh
keytool -J-Duser.language=en -J-Duser.country=US -list -v \
  -keystore "$UPLOAD_KEYSTORE" -alias "$UPLOAD_KEY_ALIAS" \
  -storepass:env UPLOAD_STORE_PASSWORD
```

## Google Play publisher service account

Check that the configured JSON exists, is a service-account credential, and has the fields required by the project's uploader. Verify the account's publishing permissions for the exact target app and intended operation from authorized Play Console evidence. A well-formed local file is evidence of file shape. Report Play permissions as pending when unverified. A Google Cloud IAM identity and key can be provisioned independently of its Play Console grant.

### Prepare a publisher credential with gcloud

Start with the target project's configured credential. If it already has an appropriate service account and a usable key, verify their access before considering a new key. Otherwise, resolve the approved Google Cloud project, the service account email or intended account ID, and the output path expected by the uploader. Prefer the target project's own helper when available.

Inspect the API and account with read-only commands. Set `GOOGLE_CLOUD_PROJECT_ID` and `PLAY_SERVICE_ACCOUNT_EMAIL` to the values for this setup.

```sh
gcloud services list --enabled --project "${GOOGLE_CLOUD_PROJECT_ID:?}" \
  --filter='config.name:androidpublisher.googleapis.com' --format='value(config.name)'
gcloud iam service-accounts describe "${PLAY_SERVICE_ACCOUNT_EMAIL:?}" \
  --project "${GOOGLE_CLOUD_PROJECT_ID:?}" --format='value(email)'
```

An empty result from a successful API listing means the API is disabled. Resolve permission errors before deciding that an API or account is missing. For offline or dry-run requests, report the planned actions without executing the commands that change Cloud resources. Use the project's existing provisioning dry-run when available.

When authorized, enable the API if disabled and create an account only if a new one is needed. For creation, set `PLAY_PUBLISHER_ACCOUNT_ID` to the chosen account ID, then use the resulting account email for key creation and Play access.

```sh
gcloud services enable androidpublisher.googleapis.com --project "${GOOGLE_CLOUD_PROJECT_ID:?}"
gcloud iam service-accounts create "${PLAY_PUBLISHER_ACCOUNT_ID:?}" \
  --project "${GOOGLE_CLOUD_PROJECT_ID:?}" --display-name='Google Play publisher'
```

When the uploader requires a new JSON key and key creation is authorized, set `PLAY_SERVICE_ACCOUNT_JSON` to a new file in the target app's private, Git-ignored credentials directory. Resolve and check the destination before creating it. If organization policy blocks user-managed keys, ask the project owner which supported credential source the uploader should use.

```sh
(
  set -eu
  : "${PLAY_SERVICE_ACCOUNT_JSON:?Set a new service-account JSON path}"
  test ! -e "$PLAY_SERVICE_ACCOUNT_JSON" && test ! -L "$PLAY_SERVICE_ACCOUNT_JSON" || exit 1
  umask 077
  mkdir -p -- "$(dirname -- "$PLAY_SERVICE_ACCOUNT_JSON")"
  gcloud iam service-accounts keys create "$PLAY_SERVICE_ACCOUNT_JSON" \
    --iam-account="${PLAY_SERVICE_ACCOUNT_EMAIL:?}" \
    --key-file-type=json --project "${GOOGLE_CLOUD_PROJECT_ID:?}"
  chmod 600 "$PLAY_SERVICE_ACCOUNT_JSON"
)
```

Check the JSON type and account email locally without printing the file. In Play Console **Users and permissions**, verify or arrange the grant for this service account and the exact target app. Use the permissions required by the intended operation. Cloud IAM setup and Play Console access are separate.

[Enable an API](https://cloud.google.com/sdk/gcloud/reference/services/enable) · [Create a service account](https://cloud.google.com/sdk/gcloud/reference/iam/service-accounts/create) · [Create a service account key](https://cloud.google.com/sdk/gcloud/reference/iam/service-accounts/keys/create) · [Google Play API setup](https://developers.google.com/android-publisher/getting_started)

### Optional package-access probe with gpd

If `gpd` is available and a temporary Play edit is authorized, use the target project's effective service-account JSON and exact production package. Set `PLAY_SERVICE_ACCOUNT_JSON` to the credential file path and `ANDROID_PACKAGE` to the resolved package.

```sh
gpd auth check \
  --key-path "${PLAY_SERVICE_ACCOUNT_JSON:?Set the service-account JSON path}" \
  --package "${ANDROID_PACKAGE:?Set the production package}" \
  --store-tokens never --output json
```

This online probe creates an uncommitted Play edit and attempts to delete it. Check that the result names the intended package, reports `valid: true`, and contains no cleanup error. Record package-level edit access as the evidence and verify the intended upload or release permission separately. If the probe is unavailable, fails, or cleanup fails, report the result without raw credentials or account details. For offline or strict read-only work, use `gpd auth check --help` for command validation and leave platform access pending.

[Android signing and upload keys](https://developer.android.com/studio/publish/app-signing) · [gpd authentication guide](https://github.com/dl-alexandre/Google-Play-Developer-CLI/blob/master/docs/auth-parity-guide.md) · [Expo Android release reference](https://github.com/expo/skills/blob/main/plugins/expo/skills/eas-app-stores/references/play-store.md)

## Example: upgrade an existing Play app

- Resolve the current Play listing's package and compare it with the destination release configuration. Use that listing's upload certificate fingerprint as the expected baseline.
- Compare the destination's configured upload keystore and alias against the baseline. Test a different fingerprint and a missing baseline with synthetic inputs. Both cases should leave reuse unconfirmed.
- Resolve the publisher credential from the destination's release configuration. Check the file shape locally and record Play Console access as pending unless there is evidence for the exact listing.
- If the repository already provides a publisher-key dry-run, point it at a fresh private temporary directory and use synthetic project and account identifiers. Verify that it makes no provider changes and generates no files. Google Cloud IAM key creation and Play Console access remain separate operations.
