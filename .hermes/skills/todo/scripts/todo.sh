#!/usr/bin/env bash
# The owner's to-do list, kept as GitHub issues. (dev) items get the `dev` label, which
# the developer watches.
# Usage: todo.sh | todo.sh add "<title>" ["<details>"] | todo.sh edit <n> "<title>" ["<details>"]
#        todo.sh note <n> "<text>" | todo.sh done <n>
set -euo pipefail
cd /srv/whitelabel
footer="Added from the site assistant on behalf of the owner."

# Split "(dev) Title" into label + title; refuse a title that is really a description.
parse_title() {
  label=owner; title=$1
  if [[ "$title" =~ ^\(dev\)[[:space:]]* ]]; then label=dev; title=${title#*)}; title=${title# }; fi
  [ -n "$title" ] || { echo "Needs a title."; exit 1; }
  [ ${#title} -le 90 ] || { echo "That title is ${#title} characters. Keep it to one line and put the rest in the details."; exit 1; }
}
compose_body() {  # details -> issue body
  local b=""; [ -n "$1" ] && b="$1"$'\n\n'
  [ "$label" = dev ] && b="${b}Needs the developer. "
  printf '%s' "${b}${footer}"
}
open_title() {  # number -> title, or fail
  gh issue view "$1" --json title,state -q 'select(.state=="OPEN") | .title' 2>/dev/null || true
}
number() { [[ "$1" =~ ^[0-9]+$ ]] || { echo "Which number? /todo $2 12"; exit 1; }; }

case "${1:-}" in
  add)
    parse_title "${2:-}"
    url=$(gh issue create --title "$title" --label "$label" --body "$(compose_body "${3:-}")")
    echo "Added #${url##*/}: $title"; echo; "$0" ;;
  edit)
    n=${2:-}; number "$n" edit
    old=$(open_title "$n"); [ -n "$old" ] || { echo "No open item #$n."; exit 1; }
    parse_title "${3:-$old}"
    # An item already marked (dev) stays that way unless the new title says (dev) itself.
    [ "$(gh issue view "$n" --json labels -q '[.labels[].name] | index("dev")')" = null ] || label=dev
    args=(--title "$title")
    [ -n "${4:-}" ] && args+=(--body "$(compose_body "$4")")
    [ "$label" = dev ] && args+=(--add-label dev --remove-label owner)
    gh issue edit "$n" "${args[@]}" >/dev/null
    echo "Updated #$n: $title"; [ -n "${4:-}" ] && echo "Details replaced."; echo; "$0" ;;
  note)
    n=${2:-}; number "$n" note
    [ -n "${3:-}" ] || { echo "Nothing to add."; exit 1; }
    [ -n "$(open_title "$n")" ] || { echo "No open item #$n."; exit 1; }
    gh issue comment "$n" --body "$3"$'\n\n'"— via the site assistant, on behalf of the owner." >/dev/null
    echo "Noted on #$n."; echo; "$0" ;;
  done)
    n=${2:-}; number "$n" done
    title=$(open_title "$n"); [ -n "$title" ] || { echo "No open item #$n."; exit 1; }
    gh issue close "$n" --comment "Done, via the site assistant." >/dev/null
    echo "Done #$n: $title"; echo; "$0" ;;
  "")
    echo "Pending:"
    gh issue list --state open --limit 30 --json number,title,labels \
      -q '.[] | "  #\(.number)  \(if any(.labels[]; .name=="dev") then "(dev) " else "" end)\(.title)"' | { grep . || echo "  (nothing)"; }
    echo; echo "Done recently:"
    gh issue list --state closed --limit 5 --json number,title,closedAt \
      -q '.[] | "  ✓ #\(.number)  \(.title)  (\(.closedAt | sub("T.*";"")))"' | { grep . || echo "  (nothing yet)"; }
    ;;
  *) echo "Usage: /todo | /todo add <title> [details] | /todo edit <n> <title> [details] | /todo note <n> <text> | /todo done <n>"; exit 1 ;;
esac
