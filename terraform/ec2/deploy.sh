#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required but not installed" >&2
  exit 1
fi

if [[ ! -f terraform.tfvars ]]; then
  echo "terraform.tfvars is missing. Copy terraform.tfvars.example first." >&2
  exit 1
fi

terraform init
terraform plan -out=tfplan

if [[ "${APPLY:-false}" == "true" ]]; then
  terraform apply tfplan
else
  echo "Plan created at $SCRIPT_DIR/tfplan"
  echo "Re-run with APPLY=true to apply the plan."
fi