# iOS release credentials

## Distribution identity and App Store profile

1. Resolve the exact distribution Bundle ID, Apple Developer Team and required capabilities from the target. Identify which build profile the target's release script uses. An App Store profile should match that exact App ID, team and distribution type. Check expiration, required entitlements and the distribution certificate in the profile. A development or Ad Hoc profile is a useful negative control.
2. Check that the P12 opens, the private key matches its distribution certificate, and the certificate is within its validity dates and belongs to the target team. Reuse a same-team identity only when the target profile authorizes that certificate for signing. If the target profile is missing, report the P12 as a local reuse candidate pending a matching profile and confirmation of current Apple status. A local validity check cannot detect a revoked certificate.
3. Prefer the target project's local signing checker. Otherwise, decode the CMS profile with `security cms` or OpenSSL and inspect its relevant plist fields in memory. If using OpenSSL with trust validation disabled for local parsing, report metadata matching only. For P12 validation, derive the public key from the private key inside a local process and compare it to the leaf certificate's public key. Never print private-key output or persist it in a log or temporary file.
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

## App Store Connect upload key

Confirm the upload tool supports the intended credential type. For a Team Key, match the P8, Key ID and Issuer ID and confirm the team, active key status and upload role from authorized account evidence. Team Keys span apps within the same App Store Connect team. The IPA's Bundle ID determines the app that receives the build. Report local key/config presence and platform status separately. An existing P8 may be reused only after the required checks. If there is no valid key, give the App Store Connect Team Keys route or the project's existing creator. Download is one-time. Store the new path and variable names according to the target uploader.

[Apple API key roles and scope](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api) · [Apple upload guide](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds)

## Example: migrate to a new Bundle ID

- Check the source distribution identity against its current profile. If the destination app is in the same team, consider reusing that identity after confirming its status and getting a matching profile for the destination.
- Run the destination's local signing checker against the source profile as a negative control. It should reject a profile whose App ID differs from the destination's. If the project has a checker that accepts only its own credentials, use synthetic inputs for the negative control.
- Map the destination's certificate, profile and password settings to its own local credential paths. For upload, record the expected P8 path, Key ID and Issuer ID settings. Check the destination team's authorized record before marking any existing Team Key reusable.
- If the repository already provides a key-creation dry-run, point its output arguments at fresh private temporary paths. Check that it reports no provider changes and leaves no generated files. Check the helper's default role before providing a live creation command.
