#!/usr/bin/env bash
# Apply the repository's protection and security settings. For maintainers, run once after the
# repository is made public and again whenever the rules in CONTRIBUTING.md change.
#
#   GH_TOKEN="$(gh auth token --user <maintainer>)" bash tools/protect_main.sh
#
# GitHub refuses most of these on a private repository of a free account.
set -euo pipefail

REPO="${REPO:-sunfish-LittleKight/nightreign-boss-timer}"

echo "Protecting main of $REPO"
gh api -X PUT "repos/$REPO/branches/main/protection" --input - >/dev/null <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Lint and format", "Test (Python 3.11)", "Test (Python 3.13)"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "lock_branch": false
}
JSON

echo "Protecting release tags (v*)"
if ! gh api "repos/$REPO/rulesets" --jq '.[].name' | grep -qx "Release tags"; then
  gh api -X POST "repos/$REPO/rulesets" --input - >/dev/null <<'JSON'
{
  "name": "Release tags",
  "target": "tag",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
  "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}, {"type": "update"}]
}
JSON
fi

echo "Turning on secret scanning, push protection and private vulnerability reports"
gh api -X PATCH "repos/$REPO" --input - >/dev/null <<'JSON'
{
  "security_and_analysis": {
    "secret_scanning": {"status": "enabled"},
    "secret_scanning_push_protection": {"status": "enabled"}
  }
}
JSON
gh api -X PUT "repos/$REPO/private-vulnerability-reporting" >/dev/null
gh api -X PUT "repos/$REPO/vulnerability-alerts" >/dev/null
gh api -X PUT "repos/$REPO/automated-security-fixes" >/dev/null

echo "Requiring approval before workflows run for first-time contributors"
gh api -X PUT "repos/$REPO/actions/permissions/fork-pr-contributor-approval" \
  -f approval_policy=first_time_contributors >/dev/null

echo "Done. Current protection of main:"
gh api "repos/$REPO/branches/main/protection" --jq '{
  checks: .required_status_checks.contexts,
  up_to_date: .required_status_checks.strict,
  admins_included: .enforce_admins.enabled,
  approvals: .required_pull_request_reviews.required_approving_review_count,
  linear: .required_linear_history.enabled,
  conversations: .required_conversation_resolution.enabled,
  force_push: .allow_force_pushes.enabled,
  deletion: .allow_deletions.enabled
}'
