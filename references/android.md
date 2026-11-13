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

Resolve the Google Cloud project, service account ID, and private, Git-ignored JSON path expected by the uploader. Prefer the target project's own helper when available. Otherwise use the [standalone script](../scripts/prepare-google-play-credentials.sh) from this repository or copy it into the target project. It works with Bash 3.2 or later. Relative key paths resolve from the current working directory.

```sh
bash scripts/prepare-google-play-credentials.sh \
  --project example-mobile --service-account play-publisher \
  --key-path ./credentials/google-play/publisher.json --dry-run
```

- **Dry-run** is the default. It checks argument and path shape and prints the planned actions. It leaves cloud status pending and runs without `gcloud` or Python. It creates no directories or files.
- **Apply** requires an explicit `--apply` in place of `--dry-run`, an authenticated `gcloud` CLI with permission to inspect the project and service accounts, and Python 3. It checks both cloud resources before making changes, enables the Android Publisher API if needed, and creates the service account if missing. A failed cloud lookup or a disabled account stops the run.
- **Local JSON** is reused when its structure and account email match and the service account exists. This checks local structure and account identity. Live key validity and Play permissions still need separate evidence. A mismatched or malformed file or a symbolic link at the destination stops the run. A new key is staged privately, checked, and installed with mode `0600` without replacing an existing path. Use a local filesystem that supports hard links.
- **Recovery** depends on the failed step. Run apply again after fixing API or account setup and it will reuse completed cloud setup. If key creation or local installation fails, inspect the service account's keys before retrying. The script reports the Key ID when it can recover it from the staged JSON and removes the temporary copy. If organization policy blocks user-managed keys, ask the project owner which credential source the uploader supports.

Verify or arrange the grant for the exact target app in Play Console **Users and permissions**, using the permissions required for the intended operation.

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

[Android signing and upload keys](https://developer.android.com/studio/publish/app-signing) · [gpd authentication guide](https://github.com/dl-alexandre/Google-Play-Developer-CLI/blob/master/docs/auth-parity-guide.md)

## Example: upgrade an existing Play app

- Resolve the current Play listing's package and compare it with the destination release configuration. Use that listing's upload certificate fingerprint as the expected baseline.
- Compare the destination's configured upload keystore and alias against the baseline. Test a different fingerprint and a missing baseline with synthetic inputs. Both cases should leave reuse unconfirmed.
- Resolve the publisher credential from the destination's release configuration. Check the file shape locally and record Play Console access as pending unless there is evidence for the exact listing.
- Use the standalone script or the project’s helper for a publisher-key dry-run. Point it at a fresh private temporary directory and use synthetic project and account identifiers. Verify that it makes no provider changes and generates no files.
