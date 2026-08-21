#!/usr/bin/env bash
# npj Digital Medicine Article budget check.
#
# The npj count differs from JAMIA's in two ways that matter:
#   - Methods is counted SEPARATELY from the 5,000-word main text.
#   - The display-item limit is 10 combined, not 4 tables plus 6 figures.
# Table and figure environments are stripped whole before counting, so legends
# and table contents stay out of the prose totals.
#
# Usage: ./budget.sh

set -euo pipefail
cd "$(dirname "$0")"

MAIN_LIMIT=5000
METHODS_LIMIT=3000       # "typically do not exceed"; may be longer if necessary
DISPLAY_LIMIT=10
ABSTRACT_LIMIT=150
REF_LIMIT=70
TITLE_LIMIT=15

strip_display() {
  perl -0777 -pe 's/\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}//gs' "$1"
}

count_words() {
  strip_display "$1" | detex 2>/dev/null | tr -s '[:space:]' '\n' | grep -c '[[:alnum:]]' || true
}

printf '%-34s %8s\n' "SECTION" "WORDS"
printf '%-34s %8s\n' "----------------------------------" "--------"

main=0
for f in sections/01_opening.tex sections/02_results.tex sections/03_discussion.tex; do
  w=$(count_words "$f"); main=$((main + w))
  printf '%-34s %8d\n' "$(basename "$f" .tex)" "$w"
done
printf '%-34s %8s\n' "----------------------------------" "--------"
printf '%-34s %8d  (limit %d)\n' "MAIN TEXT" "$main" "$MAIN_LIMIT"

over=$((main - MAIN_LIMIT))
if [ "$over" -gt 0 ]; then
  printf '%-34s %8d  (%d%% over)\n' "MUST CUT" "$over" "$((over * 100 / MAIN_LIMIT))"
else
  printf '%-34s %8d\n' "HEADROOM" "$((-over))"
fi

echo
meth=$(count_words sections/04_methods.tex)
printf '%-34s %8d  (guide %d, may exceed)\n' "METHODS (counted separately)" "$meth" "$METHODS_LIMIT"

echo
abs=$(perl -0777 -ne 'print $1 if /\\begin\{abstract\}(.*?)\\end\{abstract\}/s' main_npjdm.tex \
      | detex 2>/dev/null | tr -s '[:space:]' '\n' | grep -c '[[:alnum:]]' || true)
printf '%-34s %8d  (limit %d, unstructured)\n' "ABSTRACT" "$abs" "$ABSTRACT_LIMIT"

# npj caps the title at 15 words and forbids punctuation and active verbs.
title=$(perl -0777 -ne 'print $1 if /\\bfseries\s+(.*?)\\par/s' main_npjdm.tex \
        | tr -s '[:space:]' ' ' | sed 's/[{}\\]//g')
tw=$(echo "$title" | tr -s ' ' '\n' | grep -c '[[:alnum:]]' || true)
printf '%-34s %8d  (limit %d)\n' "TITLE WORDS" "$tw" "$TITLE_LIMIT"
if echo "$title" | grep -q '[?!:;,]'; then
  printf '%-34s %8s\n' "  TITLE PUNCTUATION" "FOUND ⚠"
fi

echo
tables=$( { cat sections/*.tex | grep -c '\\begin{table'; } || true)
figures=$( { cat sections/*.tex | grep -c '\\begin{figure'; } || true)
total=$((tables + figures))
printf '%-34s %8d\n' "Tables" "$tables"
printf '%-34s %8d\n' "Figures" "$figures"
printf '%-34s %8d  (limit %d combined)\n' "DISPLAY ITEMS" "$total" "$DISPLAY_LIMIT"
[ "$total" -gt "$DISPLAY_LIMIT" ] && printf '%-34s %8d\n' "  must remove" "$((total - DISPLAY_LIMIT))"

echo
refs=$( { grep -c '^@' ../references.bib; } || true)
printf '%-34s %8d  (guide %d)\n' "REFERENCES" "$refs" "$REF_LIMIT"

echo
todo=$( { grep -ro '\[TO COMPLETE\|\[OPTIONAL\|\[DEPARTMENT\]\|\[REPOSITORY\|\[INSTITUTIONAL EMAIL' . --include='*.tex' || true; } | wc -l)
overb=$( { grep -ro '\\overbudget{' . --include='*.tex' || true; } | wc -l)
printf '%-34s %8d\n' "PLACEHOLDERS TO FILL" "$todo"
printf '%-34s %8d\n' "OVER-BUDGET MARKERS" "$overb"
