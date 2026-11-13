#!/usr/bin/env python3
"""Check local App Store signing inputs with Python 3 and OpenSSL."""

import argparse
import getpass
import os
import plistlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def openssl(*args, data=None, password=None):
    environment = {**os.environ, "LC_ALL": "C"}
    if password is not None:
        environment["IOS_CHECK_P12_PASSWORD"] = password
    return subprocess.run(
        ["openssl", *args], input=data, env=environment, capture_output=True,
        check=True, timeout=30,
    ).stdout


def load_profile(path):
    try:
        payload = openssl("smime", "-verify", "-inform", "DER", "-noverify", "-in", str(path))
        profile = plistlib.loads(payload)
    except (subprocess.CalledProcessError, plistlib.InvalidFileException, ValueError):
        raise ValueError("Cannot decode or verify the profile's CMS contents.") from None
    if not isinstance(profile, dict) or not isinstance(profile.get("Entitlements"), dict):
        raise ValueError("The profile is missing required signing metadata.")
    return profile


def check_profile(profile, args, now):
    entitlements = profile["Entitlements"]
    prefix, _, bundle_id = entitlements.get("application-identifier", "").partition(".")
    if bundle_id != args.bundle_id:
        raise ValueError("The provisioning profile does not match the target Bundle ID.")
    if profile.get("TeamIdentifier") != [args.team_id] or entitlements.get(
        "com.apple.developer.team-identifier", args.team_id
    ) != args.team_id:
        raise ValueError("The provisioning profile does not match the target team.")
    if prefix not in profile.get("ApplicationIdentifierPrefix", [args.team_id]):
        raise ValueError("The provisioning profile has an inconsistent App ID prefix.")
    if entitlements.get("get-task-allow") is not False or "ProvisionedDevices" in profile or profile.get("ProvisionsAllDevices"):
        raise ValueError("Expected an App Store distribution profile.")
    expiration = profile.get("ExpirationDate")
    if not isinstance(expiration, datetime) or expiration.replace(tzinfo=timezone.utc) <= now:
        raise ValueError("The provisioning profile is expired or has no valid expiration date.")
    if args.require_push and entitlements.get("aps-environment") != "production":
        raise ValueError("The profile lacks the production push entitlement.")
    if args.require_apple_sign_in and "Default" not in entitlements.get("com.apple.developer.applesignin", []):
        raise ValueError("The profile lacks the Sign in with Apple entitlement.")


def check_identity(profile, path, password, team_id, now):
    args = ("pkcs12", "-in", str(path), "-passin", "env:IOS_CHECK_P12_PASSWORD")
    try:
        certificate = openssl(*args, "-clcerts", "-nokeys", password=password)
        private_key = openssl(*args, "-nocerts", "-nodes", password=password)
    except subprocess.CalledProcessError:
        raise ValueError("Cannot open the P12. Check its password and OpenSSL compatibility.") from None
    if certificate.count(b"-----BEGIN CERTIFICATE-----") != 1 or len(
        re.findall(rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----", private_key)
    ) != 1:
        raise ValueError("The P12 must contain one leaf certificate and one private key.")

    der = openssl("x509", "-outform", "DER", data=certificate)
    if der not in profile.get("DeveloperCertificates", []):
        raise ValueError("The profile does not authorize the P12 certificate.")
    if openssl("x509", "-noout", "-pubkey", data=certificate) != openssl("pkey", "-pubout", data=private_key):
        raise ValueError("The P12 private key does not match its certificate.")
    subject = openssl("x509", "-noout", "-subject", "-nameopt", "sep_multiline", data=certificate).decode()
    if not re.search(r"^[ \t]*CN[ \t]*=[ \t]*(Apple Distribution|iPhone Distribution):", subject, re.MULTILINE):
        raise ValueError("The P12 must contain an Apple distribution certificate.")
    if not re.search(rf"^[ \t]*OU[ \t]*=[ \t]*{team_id}[ \t]*$", subject, re.MULTILINE):
        raise ValueError("The P12 certificate does not match the target team.")
    dates = openssl("x509", "-noout", "-dates", data=certificate).decode().splitlines()
    start, end = (
        datetime.strptime(line.split("=", 1)[1], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        for line in dates
    )
    if not start <= now < end:
        raise ValueError("The P12 certificate is outside its validity period.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-id", required=True, help="Exact production Bundle ID")
    parser.add_argument("--team-id", required=True, help="Expected Apple Developer Team ID")
    parser.add_argument("--p12", type=Path, required=True, help="Distribution certificate and private key")
    parser.add_argument("--profile", type=Path, required=True, help="App Store .mobileprovision file")
    parser.add_argument("--password-env", metavar="NAME", help="Read the P12 password from this environment variable")
    parser.add_argument("--require-push", action="store_true", help="Require production push entitlement")
    parser.add_argument("--require-apple-sign-in", action="store_true", help="Require Sign in with Apple entitlement")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Z0-9]{10}", args.team_id):
        parser.error("--team-id must contain 10 uppercase letters or digits")
    if not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", args.bundle_id):
        parser.error("--bundle-id must be an explicit Bundle ID")

    try:
        if not args.p12.is_file() or not args.profile.is_file():
            raise ValueError("Both the P12 and the provisioning profile must be readable files.")
        now = datetime.now(timezone.utc)
        profile = load_profile(args.profile)
        check_profile(profile, args, now)
        if args.password_env:
            password = os.environ.get(args.password_env)
            if password is None:
                raise ValueError("The selected password environment variable is unset.")
        elif sys.stdin.isatty():
            password = getpass.getpass("P12 password: ")
        else:
            raise ValueError("Use a terminal password prompt or --password-env for a non-interactive check.")
        check_identity(profile, args.p12, password, args.team_id, now)
    except ValueError as error:
        sys.exit(str(error))
    except (TypeError, AttributeError, IndexError):
        sys.exit("Invalid profile or certificate metadata.")
    except (OSError, subprocess.SubprocessError):
        sys.exit("Local signing check failed. Check OpenSSL and input file access.")
    print("Local signing inputs match. Apple trust, revocation and upload access were not verified.")


if __name__ == "__main__":
    main()
