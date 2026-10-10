#!/usr/bin/env bash
set -euo pipefail

# Verifies the publication invariants stated in CLAUDE-PROJECT-RULES.md.
#
# Those rules decide what the outside world sees: a skill in a PUBLIC bucket
# must be reachable from the top-level README and the plugin manifest, and a
# skill in a PRIVATE bucket must appear in neither. Until now nothing checked
# them, so the only thing standing between a drafted-but-unpublished skill and
# the public plugin index was whoever remembered to update three files at once.
# That gap was real, not theoretical: the four `misc/` skills shipped without
# manifest entries and stayed that way until a later pass noticed.
#
# Deliberately dependency-free (bash + coreutils + grep + sed, no node/jq) so it
# runs identically in CI, in a pre-commit hook, and on a laptop with nothing
# installed. The manifest is a flat list of path strings, so reading the lines
# of its `skills` array is sufficient and cannot be fooled by key ordering.
# (check-invariants.test.mjs uses node to build fixture trees; the checker
# itself does not.)
#
# Exits 0 when every invariant holds, 1 otherwise, listing each violation.

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

# Promoted: must be in both public indexes.
PUBLIC_BUCKETS=(engineering productivity misc)
# Not promoted: must be in neither.
PRIVATE_BUCKETS=(personal in-progress deprecated)

MANIFEST=".claude-plugin/plugin.json"
ROOT_README="README.md"

# Shortest run of prose that counts as the "one-line description" a bucket
# README must carry beside each link. Low enough to never argue with a terse
# but real description, high enough that stray punctuation is not mistaken for
# one.
MIN_DESCRIPTION_CHARS=10

failures=0
# Skill directories walked by rule 1; see the floor check after that loop.
inspected=0

fail() {
  printf '  FAIL  %s\n' "$1"
  failures=$((failures + 1))
}

# Skill directory names within a bucket, one per line. Silent for a bucket that
# does not exist, so adding a bucket to the lists above is not a hard error.
skills_in() {
  local bucket="$1" dir
  [ -d "skills/$bucket" ] || return 0
  for dir in "skills/$bucket"/*/; do
    # Guards the unexpanded glob when a bucket holds no skill directories.
    [ -d "$dir" ] || continue
    basename "$dir"
  done
}

# Every element of the manifest's `skills` array, one per line, exactly as
# written (quotes stripped, spelling untouched). Scoped to the array rather than
# grepping the whole file so a path-like string in another field can never be
# read as a published skill, and a typo'd element such as `./skils/personal/x`
# is still seen and judged instead of silently skipped. The second sed drops the
# `"skills"` key token that the range's first line carries.
manifest_skill_entries() {
  sed -n '/"skills"[[:space:]]*:[[:space:]]*\[/,/\]/p' "$MANIFEST" |
    sed '1s/.*\[//' |
    grep -oE '"[^"]*"' |
    tr -d '"' || true
}

# True if the manifest lists this skill, compared on the resolved path rather
# than the spelling. Still whole-string equality, so `tdd` never matches
# `tdd-extra`.
#
# This used to be a byte-exact grep for "./skills/<bucket>/<skill>". That is
# right when a PRESENT entry is required (rule 2: a mis-spelled public entry
# fails loudly) but backwards for rule 4, which asks whether a private skill is
# ABSENT: there any spelling that is not byte-identical ("./skills/x/y/" copied
# off a directory listing, "skills/x/y" without the "./") read as "not
# published" although the entry names the same directory, and the gate stayed
# green.
# The leading "./" and trailing "/" are stripped here so those two realistic
# hand-edit mistakes get the right message ("is listed") in one run; every other
# spelling is rejected by rule 6, so no entry can be silently absent from here.
in_manifest() {
  local want="skills/$1/$2" entry
  while IFS= read -r entry; do
    entry="${entry#./}"
    entry="${entry%/}"
    [ "$entry" = "$want" ] && return 0
  done < <(manifest_skill_entries)
  return 1
}

# True if $file contains a markdown link whose TARGET is this skill's SKILL.md
# and whose TEXT mentions the skill name — rule 3 ("must link the skill name to
# its SKILL.md") is about the link text, not merely the presence of the path.
links_skill() {
  local file="$1" bucket="$2" skill="$3" path_re link
  case "$file" in
    "$ROOT_README") path_re="\\./skills/$bucket/$skill/SKILL\\.md" ;;
    *)              path_re="\\./$skill/SKILL\\.md" ;;
  esac
  while IFS= read -r link; do
    # Link text is everything between the outer [ ] — if it names the skill,
    # this link satisfies the rule.
    case "${link%%](*}" in
      *"$skill"*) return 0 ;;
    esac
  done < <(grep -oE "\\[[^]]*\\]\\($path_re\\)" "$file" || true)
  return 1
}

echo "Checking publication invariants (CLAUDE-PROJECT-RULES.md) in $REPO"
echo

echo "0. every bucket under skills/ is classified public or private"
# Without this, the two lists above are a SILENT ALLOW-LIST: add skills/writing/ tomorrow
# and every rule below skips it, so the gate passes having checked nothing about the one
# bucket nobody has reviewed yet. That is the exact failure this script exists to prevent,
# so an unclassified bucket is an error rather than a thing to ignore.
for dir in skills/*/; do
  [ -d "$dir" ] || continue
  bucket="$(basename "$dir")"
  known=0
  for b in "${PUBLIC_BUCKETS[@]}" "${PRIVATE_BUCKETS[@]}"; do
    [ "$b" = "$bucket" ] && known=1 && break
  done
  [ "$known" -eq 1 ] || fail "skills/$bucket is in neither PUBLIC_BUCKETS nor PRIVATE_BUCKETS in $(basename "$0") — classify it (and add it to the right public indexes) rather than leaving it unchecked"
done

echo "1. every skill directory has a SKILL.md"
for bucket in "${PUBLIC_BUCKETS[@]}" "${PRIVATE_BUCKETS[@]}"; do
  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    inspected=$((inspected + 1))
    [ -f "skills/$bucket/$skill/SKILL.md" ] || fail "skills/$bucket/$skill has no SKILL.md"
  done < <(skills_in "$bucket")
done
# Every rule here is a loop over skills_in, which is silent for a missing bucket, and a loop
# over nothing passes. Rename or drop skills/ (a reorg, or an upstream sync that changes the
# layout) and all of them iterate zero skills, so the verdict below reads "OK" with nothing
# verified while the manifest and README links may be broken. Rule 0 cannot catch it either:
# it only reacts to a bucket it finds. Finding no skill at all is a failure, not a clean run.
[ "$inspected" -gt 0 ] || fail "no skill directories found in any bucket under skills/, so no rule in this run checked anything (was skills/ renamed or removed?)"

echo "2. every public skill has a $MANIFEST entry"
for bucket in "${PUBLIC_BUCKETS[@]}"; do
  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    in_manifest "$bucket" "$skill" || fail "skills/$bucket/$skill is missing from $MANIFEST"
  done < <(skills_in "$bucket")
done

echo "3. every public skill is linked by name from $ROOT_README"
for bucket in "${PUBLIC_BUCKETS[@]}"; do
  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    links_skill "$ROOT_README" "$bucket" "$skill" ||
      fail "$ROOT_README has no link naming '$skill' and pointing at skills/$bucket/$skill/SKILL.md"
  done < <(skills_in "$bucket")
done

echo "4. no private skill appears in either public index"
for bucket in "${PRIVATE_BUCKETS[@]}"; do
  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    ! in_manifest "$bucket" "$skill" || fail "unpromoted skills/$bucket/$skill is listed in $MANIFEST"
    if grep -qF "skills/$bucket/$skill/SKILL.md" "$ROOT_README"; then
      fail "unpromoted skills/$bucket/$skill is referenced in $ROOT_README"
    fi
  done < <(skills_in "$bucket")
done

echo "5. every bucket README lists each of its skills, with a description"
for bucket in "${PUBLIC_BUCKETS[@]}" "${PRIVATE_BUCKETS[@]}"; do
  readme="skills/$bucket/README.md"
  if [ ! -d "skills/$bucket" ]; then continue; fi
  if [ ! -f "$readme" ]; then
    fail "skills/$bucket has no README.md"
    continue
  fi
  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    if ! links_skill "$readme" "$bucket" "$skill"; then
      fail "$readme has no link naming '$skill' and pointing at ./$skill/SKILL.md"
      continue
    fi
    # The rule asks for a one-line description alongside the link, so a bare
    # bullet holding only the link is a violation. Everything up to and
    # including the link is cut with a literal match (no regex, so a skill name
    # is never reinterpreted as a pattern), then the bold markers and the
    # em-dash separator are stripped. Testing merely for "some character after
    # the link" is not enough: the house format closes with `**`, which would
    # satisfy it on its own.
    marker="](./$skill/SKILL.md)"
    line="$(grep -F "$marker" "$readme" | head -1)"
    desc="${line#*"$marker"}"
    desc="$(printf '%s' "$desc" | sed -E 's/^[*[:space:]—–·-]+//')"
    if [ "${#desc}" -lt "$MIN_DESCRIPTION_CHARS" ]; then
      fail "$readme lists '$skill' without a one-line description after the link"
    fi
  done < <(skills_in "$bucket")
done

echo "6. every $MANIFEST entry is written canonically and resolves to a real skill"
# Canonical spelling is required, not just tolerated: in_manifest (rules 2 and 4)
# only forgives a leading "./" and a trailing "/", so this is what stops any
# other spelling of the same directory ("./skills/./x/y", ".//skills/x/y",
# "../", an absolute path) from naming a skill that rule 4 counts as absent. The
# first character of each segment excludes "." so "." and ".." segments fail.
# Every entry is either canonical (in_manifest resolves it) or flagged here, so
# none can be missing from both.
while IFS= read -r entry; do
  [ -n "$entry" ] || continue
  if [[ ! "$entry" =~ ^\./skills/[^/.][^/]*/[^/.][^/]*$ ]]; then
    fail "$MANIFEST entry '$entry' is not written as './skills/<bucket>/<skill>' (no trailing slash, no extra './' or '../' segment, not absolute), so the other rules cannot account for it"
    continue
  fi
  [ -f "${entry#./}/SKILL.md" ] || fail "$MANIFEST entry '$entry' has no SKILL.md"
done < <(manifest_skill_entries)

echo "7. every skill link in a public index resolves to a real skill"
# The mirror of rule 6 for the other public index. Rules 2, 3 and 5 only run
# forward (skill on disk -> index entry), so deleting or renaming a skill used
# to leave its README link behind as a published 404 while this gate stayed
# green: rule 6 caught the manifest half of that edit and nothing caught the
# README half.
while IFS= read -r link; do
  [ -n "$link" ] || continue
  [ -f "${link#./}" ] || fail "$ROOT_README links '$link', which has no SKILL.md"
done < <(grep -oE '\]\(\./skills/[^)]+/SKILL\.md\)' "$ROOT_README" |
  sed -E 's/^\]\(//; s/\)$//' | sort -u || true)

for bucket in "${PUBLIC_BUCKETS[@]}" "${PRIVATE_BUCKETS[@]}"; do
  readme="skills/$bucket/README.md"
  [ -f "$readme" ] || continue
  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    [ -f "skills/$bucket/$skill/SKILL.md" ] ||
      fail "$readme links './$skill/SKILL.md', which has no SKILL.md"
  done < <(grep -oE '\]\(\./[^)/]+/SKILL\.md\)' "$readme" |
    sed -E 's|^\]\(\./||; s|/SKILL\.md\)$||' | sort -u || true)
done

echo
if [ "$failures" -eq 0 ]; then
  echo "OK — all publication invariants hold."
  exit 0
fi
printf 'FAILED — %d violation(s). See CLAUDE-PROJECT-RULES.md for the rules.\n' "$failures"
exit 1
