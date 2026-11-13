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

[Android signing and upload keys](https://developer.android.com/studio/publish/app-signing) · [Google Play API setup](https://developers.google.com/android-publisher/getting_started) · [Expo Android release reference](https://github.com/expo/skills/blob/main/plugins/expo/skills/eas-app-stores/references/play-store.md)

## Example: upgrade an existing Play app

- Resolve the current Play listing's package and compare it with the destination release configuration. Use that listing's upload certificate fingerprint as the expected baseline.
- Compare the destination's configured upload keystore and alias against the baseline. Test a different fingerprint and a missing baseline with synthetic inputs. Both cases should leave reuse unconfirmed.
- Resolve the publisher credential from the destination's release configuration. Check the file shape locally and record Play Console access as pending unless there is evidence for the exact listing.
- If the repository already provides a publisher-key dry-run, point it at a fresh private temporary directory and use synthetic project and account identifiers. Verify that it makes no provider changes and generates no files. Google Cloud IAM key creation and Play Console access remain separate operations.
