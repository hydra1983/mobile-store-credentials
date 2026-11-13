#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: prepare-google-play-credentials.sh --project PROJECT_ID
       --service-account ACCOUNT_ID --key-path FILE [--dry-run | --apply]

Default: preview locally without calling gcloud or creating files.
--apply uses the active gcloud login and requires Python 3.
EOF
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

project=''
account_id=''
key_path=''
mode=''
while (($#)); do
  case "$1" in
    --project|--service-account|--key-path)
      [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || fail "Missing value for $1."
      case "$1" in
        --project) project=$2 ;;
        --service-account) account_id=$2 ;;
        --key-path) key_path=$2 ;;
      esac
      shift 2
      ;;
    --dry-run|--apply)
      [[ -z "$mode" || "$mode" == "$1" ]] || fail "Choose --dry-run or --apply."
      mode=$1
      shift
      ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown argument: $1." ;;
  esac
done

id_pattern='^[a-z][a-z0-9-]{4,28}[a-z0-9]$'
[[ "$project" =~ $id_pattern ]] || fail "Pass a Google Cloud project ID with --project."
[[ "$account_id" =~ $id_pattern ]] || fail "Pass a service account ID with --service-account."
[[ -n "$key_path" && ! "$key_path" =~ [[:cntrl:]] ]] || fail "Pass a file path with --key-path."
case "${key_path##*/}" in
  ''|.|..) fail "--key-path must name a file." ;;
esac
[[ "$key_path" == /* ]] || key_path="$(pwd -P)/$key_path"
key_dir=${key_path%/*}
key_dir=${key_dir:-/}
[[ ! -L "$key_path" ]] || fail "The output file is a symbolic link."
[[ ! -e "$key_path" || -f "$key_path" ]] || fail "The output path is not a regular file."

ancestor=$key_dir
while [[ ! -d "$ancestor" ]]; do
  [[ ! -e "$ancestor" && ! -L "$ancestor" ]] || fail "An output parent is not a directory."
  ancestor=${ancestor%/*}
  ancestor=${ancestor:-/}
done

api='androidpublisher.googleapis.com'
email="$account_id@$project.iam.gserviceaccount.com"
if [[ "$mode" != --apply ]]; then
  printf 'Dry-run (offline)\nProject: %s\nService account: %s\nJSON path: %s\n' \
    "$project" "$email" "$key_path"
  printf '%s\n' \
    "Check $api and enable it if disabled (cloud status pending)." \
    'Check the service account and create it if missing (cloud status pending).' \
    'Reuse a matching local JSON or create a key if the output file is missing.' \
    'Verify Play Console access separately for the target app.'
  exit 0
fi

command -v gcloud >/dev/null || fail "Install gcloud before using --apply."
command -v python3 >/dev/null || fail "Install Python 3 before using --apply."

inspect_key() {
  python3 - "$1" "$email" "$2" <<'PY'
import json
import re
import sys

path, email, action = sys.argv[1:]
try:
    with open(path, encoding="utf-8") as stream:
        key = json.load(stream)
    if not isinstance(key, dict):
        sys.exit(1)
    if action == "id":
        key_id = key.get("private_key_id")
        if not isinstance(key_id, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", key_id):
            sys.exit(1)
        print(key_id)
    else:
        fields = ("private_key_id", "private_key", "client_id", "token_uri")
        if key.get("type") != "service_account" or key.get("client_email") != email:
            sys.exit(1)
        if not all(isinstance(key.get(field), str) and key[field].strip() for field in fields):
            sys.exit(1)
        if not key["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
            sys.exit(1)
except (OSError, ValueError):
    sys.exit(1)
PY
}

reuse=false
if [[ -f "$key_path" ]]; then
  inspect_key "$key_path" validate || fail "Existing JSON is unusable or belongs to another account. Preserved the file."
  reuse=true
fi

cloud=(gcloud --quiet --project "$project")
enabled_api=$("${cloud[@]}" services list --enabled \
  --filter="config.name=$api" --format='value(config.name)') || fail "Could not check the enabled API."
[[ -z "$enabled_api" || "$enabled_api" == "$api" ]] || fail "Unexpected API lookup result."

account_json=$("${cloud[@]}" iam service-accounts list \
  --filter="email=$email" --format=json) || fail "Could not check the service account."
account_status=$(python3 -c '
import json
import sys

try:
    accounts = json.load(sys.stdin)
    if not isinstance(accounts, list):
        sys.exit(1)
    if not accounts:
        print("missing")
    elif len(accounts) == 1 and accounts[0]["email"] == sys.argv[1]:
        print("disabled" if accounts[0].get("disabled") else "present")
    else:
        sys.exit(1)
except (KeyError, TypeError, ValueError):
    sys.exit(1)
' "$email" <<< "$account_json") || fail "Unexpected service account lookup result."
[[ "$account_status" != disabled ]] || fail "The service account is disabled."
if [[ "$reuse" == true && "$account_status" == missing ]]; then
  fail "The account for the existing JSON was not found. Preserved the file."
fi

if [[ -z "$enabled_api" ]]; then
  "${cloud[@]}" services enable "$api" || fail "Could not enable the Android Publisher API."
fi
if [[ "$account_status" == missing ]]; then
  "${cloud[@]}" iam service-accounts create "$account_id" \
    --display-name='Google Play publisher' || fail "Could not create the service account."
fi

if [[ "$reuse" == true ]]; then
  printf 'Reused existing service-account JSON at %s\n' "$key_path"
else
  umask 077
  mkdir -p -- "$key_dir" || fail "Could not create the output directory."
  [[ ! -e "$key_path" && ! -L "$key_path" ]] || fail "The output file appeared during preparation."
  scratch=$(mktemp -d "$key_dir/.play-publisher.XXXXXXXX") || fail "Could not create a private staging directory."
  staged_key="$scratch/key.json"
  key_attempted=false

  cleanup() {
    local status=$? key_id
    if [[ "$status" != 0 && "$key_attempted" == true ]]; then
      if key_id=$(inspect_key "$staged_key" id); then
        printf 'Review Google Cloud IAM keys for %s. Key ID: %s\n' "$email" "$key_id" >&2
      else
        printf 'A key may have been created. Review Google Cloud IAM keys for %s.\n' "$email" >&2
      fi
    fi
    rm -rf -- "$scratch"
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  key_attempted=true
  "${cloud[@]}" iam service-accounts keys create "$staged_key" \
    --iam-account="$email" --key-file-type=json >/dev/null 2>&1 ||
    fail "Could not create the JSON key. Check Cloud IAM access and organization policy."
  inspect_key "$staged_key" validate || fail "The generated JSON did not pass local validation."
  chmod 600 "$staged_key" || fail "Could not set private permissions on the staged JSON."
  python3 - "$staged_key" "$key_path" <<'PY' || fail "Could not install the generated JSON without overwriting the destination."
import os
import sys

try:
    os.link(sys.argv[1], sys.argv[2])
except OSError:
    sys.exit(1)
PY
  key_attempted=false
  printf 'Created service-account JSON at %s\n' "$key_path"
fi

printf '%s\n' 'Verify Play Console access separately for the target app.'
