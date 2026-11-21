#!/usr/bin/env bash
set -euo pipefail

pr=$(gh pr view ${1:+"$1"} --json number,url,headRefOid --jq '"\(.number) \(.url) \(.headRefOid)"')
read -r num url head <<<"$pr"
repo=$(sed -E 's#https://github.com/([^/]+/[^/]+)/pull/.*#\1#' <<<"$url")
owner=${repo%/*} name=${repo#*/}

summary=$(gh api "repos/$repo/issues/$num/comments" --paginate \
  --jq '[.[] | select(.user.login | test("greptile")) | select(.body | contains("greptile_summary"))] | last // empty | "\(.updated_at)\n\(.body)"')

echo "PR: $url (head ${head:0:9})"
if [ -z "$summary" ]; then
  echo "Greptile: no summary yet"
else
  updated=${summary%%$'\n'*}
  body=${summary#*$'\n'}
  plain=$(sed -E 's/<[^>]+>//g; s/&amp;/\&/g' <<<"$body")
  score=$(grep -oE 'Confidence Score: [0-9]/5' <<<"$plain" | head -1 || true)
  impact=$(grep -oE '\*\*\[[A-Za-z ]+ impact\]\*\*[^.]*\.' <<<"$plain" | head -1 | tr -d '*' || true)
  echo "Greptile: ${score:-no score} (updated $updated)"
  [ -n "$impact" ] && echo "$impact"
fi

echo "Unresolved Greptile threads:"
gh api graphql -F owner="$owner" -F name="$name" -F num="$num" -f query='
query($owner:String!,$name:String!,$num:Int!){repository(owner:$owner,name:$name){pullRequest(number:$num){
  reviewThreads(first:100){nodes{isResolved isOutdated comments(first:1){nodes{author{login} path line body url}}}}}}}' \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[]
    | select(.isResolved | not) | .comments.nodes[0] | select(.author.login | test("greptile"))
    | "- \(.path):\(.line // "?") \(.body | gsub("<[^>]+>"; "") | gsub("\\s+"; " ") | .[0:220])\n  \(.url)"' \
  | sed '/^$/d' | { grep . || echo "- none"; }
