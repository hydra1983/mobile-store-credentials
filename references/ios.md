# iOS release credentials

## Distribution identity and App Store profile

1. Resolve the exact distribution Bundle ID, Apple Developer Team and required capabilities from the target. Identify which build profile the target's release script uses. An App Store profile should match that exact App ID, team and distribution type. Check expiration, required entitlements and the distribution certificate in the profile. A development or Ad Hoc profile is a useful negative control.
2. Check that the P12 opens, the private key matches its distribution certificate, and the certificate is within its validity dates and belongs to the target team. Reuse a same-team identity only when the target profile authorizes that certificate for signing. If the target profile is missing, report the P12 as a local reuse candidate pending a matching profile and confirmation of current Apple status. A local validity check cannot detect a revoked certificate.
3. Prefer the target project's local signing checker. Otherwise, use the [bundled App Store signing checker](#run-the-local-signing-checker). Treat a pass as evidence that the local files match. Apple trust, revocation and platform permissions require separate evidence.
4. If the profile is missing, expired or mismatched, supply the target Bundle ID, team, required capabilities and the Apple certificate resource ID corresponding to the P12. In Apple's portal, select the App Store Connect profile type and the matching certificate. For a CLI path, confirm supported flags with `fastlane sigh --help`. Use a fresh output path to preserve existing files. `--readonly` fetches an existing profile and writes a local copy. Add `--skip_install` to avoid local profile installation. A normal invocation can create a profile.

Example for an authorized create/download using the selected certificate, with no local installation:

```sh
fastlane sigh \
  --app_identifier "$BUNDLE_ID" \
  --team_id "$APPLE_TEAM_ID" \
  --cert_id "$APPLE_CERTIFICATE_ID" \
  --provisioning_name "$PROFILE_NAME" \
  --output_path "$OUTPUT_DIR" \
  --filename "$PROFILE_FILENAME" \
  --skip_install
```

Use the confirmed Team ID and certificate resource ID. Check the downloaded profile's embedded certificate against the P12 even when Fastlane reused an existing profile. If the tool requires the signing identity in the local keychain, follow the project's authorized setup or use the portal. For projects already using Expo-managed signing, the interactive `eas credentials --platform ios` route can export that project's existing EAS credentials. Select the target project and build profile.

[Apple App Store profile guide](https://developer.apple.com/help/account/provisioning-profiles/create-an-app-store-provisioning-profile) · [Fastlane sigh](https://docs.fastlane.tools/actions/sigh/) · [ASC signing reference](https://github.com/rorkai/app-store-connect-cli-skills/blob/main/skills/asc-signing-setup/SKILL.md) · [Expo credential sync](https://docs.expo.dev/app-signing/syncing-credentials/)

## Run the local signing checker

Run from the skill repository root with Python 3 and `openssl` available. Replace the sample Bundle ID, Team ID and file paths with your own. When the skill is installed, use the checker path relative to its `SKILL.md`.

```sh
python3 scripts/check-ios-signing.py \
  --bundle-id com.example.fieldnotes \
  --team-id ABCDE12345 \
  --p12 signing/dist.p12 \
  --profile signing/AppStore.mobileprovision
```

Enter the P12 password at the hidden terminal prompt. For CI, use `--password-env P12_PASSWORD` with the variable supplied by your CI secret store. Add `--require-push` or `--require-apple-sign-in` when the app requires those capabilities. Success exits with code 0. A mismatch or unreadable input exits with a nonzero code and a diagnostic.

The checker compares the App Store profile, team, Bundle ID, expiration dates, and distribution identity without modifying files, installing credentials, or contacting Apple. It verifies CMS content integrity with OpenSSL while skipping signer certificate trust validation. It keeps the decrypted private key in local process memory. [OpenSSL verification options](https://docs.openssl.org/3.0/man1/openssl-cms/#verification-options)

## App Store Connect upload key

Confirm the upload tool supports the intended credential type. For a Team Key, match the P8, Key ID and Issuer ID and confirm the team, active key status and upload role from authorized account evidence. Team Keys span apps within the same App Store Connect team. The IPA's Bundle ID determines the app that receives the build. Report local key/config presence and platform status separately. An existing P8 may be reused only after the required checks. If there is no valid key, give the App Store Connect Team Keys route or the project's existing creator. Download is one-time. Store the new path and variable names according to the target uploader.

[Apple API key roles and scope](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api) · [Apple upload guide](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds)

## Example: migrate to a new Bundle ID

- Check the source distribution identity against its current profile. If the destination app is in the same team, consider reusing that identity after confirming its status and getting a matching profile for the destination.
- Run the destination's local checker or the bundled checker against the source profile as a negative control. Use the destination Bundle ID and the source profile. The checker should reject the mismatched App ID.
- Map the destination's certificate, profile and password settings to its own local credential paths. For upload, record the expected P8 path, Key ID and Issuer ID settings. Check the destination team's authorized record before marking any existing Team Key reusable.
- If the repository already provides a key-creation dry-run, point its output arguments at fresh private temporary paths. Check that it reports no provider changes and leaves no generated files. Check the helper's default role before providing a live creation command.
