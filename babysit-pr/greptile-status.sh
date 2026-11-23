#!/usr/bin/env bash
set -euo pipefail

self="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
dir="${XDG_CACHE_HOME:-$HOME/.cache}/greptile-poller"
lock="$dir/poller.lock"
mkdir -p "$dir/watch" "$dir/state"

usage() {
  echo "usage: greptile-status.sh [--wait] [--timeout SECS] [pr]" >&2
  exit 64
}

poller_alive() {
  local pid
  pid=$(cat "$lock/pid" 2>/dev/null) && [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

run_poller() {
  local interval=${GREPTILE_POLL_INTERVAL:-30} stale=120
  if ! mkdir "$lock" 2>/dev/null; then
    poller_alive && exit 0
    rm -rf "$lock"
    mkdir "$lock" 2>/dev/null || exit 0
  fi
  echo $$ >"$lock/pid"
  trap 'rm -rf "$lock"' EXIT
  while :; do
    local now keys=() f key ts
    now=$(date +%s)
    for f in "$dir"/watch/*; do
      [ -e "$f" ] || continue
      read -r key ts <"$f" 2>/dev/null || { rm -f "$f"; continue; }
      if [ $((now - ${ts:-0})) -gt "$stale" ]; then rm -f "$f"; continue; fi
      keys+=("$key")
    done
    [ ${#keys[@]} -eq 0 ] && exit 0
    local uniq q="query{" i=0 o r n
    uniq=$(printf '%s\n' "${keys[@]}" | sort -u)
    while read -r key; do
      IFS=/ read -r o r n <<<"$key"
      q+="p$i: repository(owner:\"$o\",name:\"$r\"){nameWithOwner pullRequest(number:$n){number state headRefOid commits(last:1){nodes{commit{checkSuites(first:20){nodes{app{slug} checkRuns(first:5,filterBy:{checkName:\"Greptile Review\"}){nodes{status conclusion startedAt}}}}}}}}} "
      i=$((i + 1))
    done <<<"$uniq"
    q+="}"
    local out
    if out=$(gh api graphql -f query="$q" 2>&1); then
      now=$(date +%s)
      jq -r '.data[] | select(.pullRequest != null)
        | .pullRequest as $p
        | ([$p.commits.nodes[0].commit.checkSuites.nodes[] | select(.app.slug | test("greptile")) | .checkRuns.nodes[]]
           | sort_by(.startedAt) | last) as $run
        | "\(.nameWithOwner)/\($p.number) \($p.headRefOid) \(
            if $p.state != "OPEN" then ($p.state | ascii_downcase)
            elif $run == null then "none"
            else ([$run.status, $run.conclusion] | map(select(. != null) | ascii_downcase) | join("-")) end)"' \
        <<<"$out" | while read -r key head status; do
          tmp=$(mktemp "$dir/state/.tmp.XXXXXX")
          echo "$now $head $status" >"$tmp"
          mv "$tmp" "$dir/state/${key//\//__}"
        done
    else
      echo "$(date) poll failed: $out" >>"$dir/poller.log"
    fi
    sleep "$interval"
  done
}

ensure_poller() {
  poller_alive && return
  nohup "$self" --poller >>"$dir/poller.log" 2>&1 </dev/null &
}

wait=0 timeout=1800 grace=300 target=""
while [ $# -gt 0 ]; do
  case $1 in
    --poller) run_poller; exit 0 ;;
    --wait) wait=1 ;;
    --timeout) timeout=${2:?}; shift ;;
    -*) usage ;;
    *) target=$1 ;;
  esac
  shift
done

read -r num url head <<<"$(gh pr view ${target:+"$target"} --json number,url,headRefOid --jq '"\(.number) \(.url) \(.headRefOid)"')"
repo=$(sed -E 's#https://github.com/([^/]+/[^/]+)/pull/.*#\1#' <<<"$url")
owner=${repo%/*} name=${repo#*/}
state="unknown"

if [ "$wait" = 1 ]; then
  key="$repo/$num"
  watch="$dir/watch/${key//\//__}.$$"
  statefile="$dir/state/${key//\//__}"
  trap 'rm -f "$watch"' EXIT
  start=$(date +%s) head_since=$start last_msg=""
  while :; do
    now=$(date +%s)
    echo "$key $now" >"$watch"
    ensure_poller
    polled=0 shead="" state="waiting-for-poll"
    [ -f "$statefile" ] && read -r polled shead state <"$statefile"
    if [ "$polled" -ge "$start" ]; then
      [ "$shead" != "$head" ] && head=$shead head_since=$now
      case $state in completed*|closed|merged) break ;; esac
      if [ "$state" = none ] && [ $((now - head_since)) -ge "$grace" ]; then
        echo "Greptile: no review started for ${head:0:9} after ${grace}s, stopped waiting" >&2
        break
      fi
    else
      state="waiting-for-poll"
    fi
    if [ $((now - start)) -ge "$timeout" ]; then
      echo "Greptile: still '$state' for ${head:0:9} after ${timeout}s, stopped waiting" >&2
      break
    fi
    msg="Greptile: $state for ${head:0:9}"
    [ "$msg" != "$last_msg" ] && echo "$msg, waiting ($((now - start))s)" >&2 && last_msg=$msg
    sleep 5
  done
  rm -f "$watch"
else
  state=$(gh api "repos/$repo/commits/$head/check-runs?check_name=Greptile%20Review" \
    --jq '[.check_runs[] | select(.app.slug | test("greptile"))] | sort_by(.started_at) | last
      | if . == null then "none" else [.status, .conclusion] | map(select(. != null)) | join("-") end')
fi

summary=$(gh api "repos/$repo/issues/$num/comments" --paginate \
  --jq '[.[] | select(.user.login | test("greptile")) | select(.body | contains("greptile_summary"))] | last // empty | "\(.updated_at)\n\(.body)"')

echo "PR: $url (head ${head:0:9})"
echo "Greptile review of head: $state"
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

if [ "$wait" = 1 ]; then
  case $state in completed*|closed|merged) exit 0 ;; *) exit 2 ;; esac
fi
