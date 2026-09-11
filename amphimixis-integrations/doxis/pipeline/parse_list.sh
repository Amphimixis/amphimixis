#!/usr/bin/env bash
# Usage: parse_list.sh <plain.list> [--limit N] [--from M]
set -euo pipefail

list_file="${1:?usage: parse_list.sh <list-file> [--limit N] [--from M]}"
shift || true

limit=""
from="0"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --limit) limit="${2:?--limit needs a value}" 
    [[ "$limit" =~ ^[0-9]+$ ]] || { echo "--limit must be a non-negative integer" >&2; exit 2; }
    shift 2 ;;
    --from) from="${2:?--from needs a value}";
    [[ "$from" =~ ^[0-9]+$ ]] || { echo "--from must be a non-negative integer" >&2; exit 2; }
    shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ ! -f "$list_file" ]; then
  echo "list file not found: $list_file" >&2
  exit 1
fi

name_list="$(sed -E 's/^[[:space:]]*#.*$//; /^[[:space:]]*$/d' "$list_file" | awk '{ print $1 }')"
[ -n "$limit" ] && name_list="$(
  printf '%s\n' "$name_list" | sed -n "$((from + 1)),$((from + limit))p"
)"

[ -n "$name_list" ] && printf '%s\n' "$name_list" || true
