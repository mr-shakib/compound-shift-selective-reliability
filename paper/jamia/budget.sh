#!/usr/bin/env bash
# JAMIA Research and Applications budget check.
#
# Counts what JAMIA counts. The body limit covers Background and Significance
# through Conclusion and excludes the abstract, references, figure legends and
# table notes -- so whole table and figure environments are stripped before
# counting, not just their captions.
#
# Usage: ./budget.sh

set -euo pipefail
cd "$(dirname "$0")"

WORD_LIMIT=4000
TABLE_LIMIT=4
FIGURE_LIMIT=6
ABSTRACT_LIMIT=250

strip_display() {
  # Drop table and figure environments whole; they are not body words.
  perl -0777 -pe 's/\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}//gs' "$1"
}

count_words() {
  strip_display "$1" | detex 2>/dev/null | tr -s '[:space:]' '\n' | grep -c '[[:alnum:]]' || true
}

printf '%-34s %8s\n' "SECTION" "WORDS"
printf '%-34s %8s\n' "----------------------------------" "--------"

total=0
for f in sections/*.tex; do
  w=$(count_words "$f")
  total=$((total + w))
  printf '%-34s %8d\n' "$(basename "$f" .tex)" "$w"
done

printf '%-34s %8s\n' "----------------------------------" "--------"
printf '%-34s %8d\n' "BODY TOTAL" "$total"
printf '%-34s %8d\n' "JAMIA limit" "$WORD_LIMIT"

over=$((total - WORD_LIMIT))
if [ "$over" -gt 0 ]; then
  pct=$((over * 100 / WORD_LIMIT))
  printf '%-34s %8d  (%d%% over)\n' "MUST CUT" "$over" "$pct"
else
  printf '%-34s %8d\n' "HEADROOM" "$((-over))"
fi

echo
# Abstract lives between \section*{Abstract} and the \clearpage that follows it.
abs=$(perl -0777 -ne 'print $1 if /\\section\*\{Abstract\}(.*?)\\clearpage/s' main_jamia.tex \
      | detex 2>/dev/null | tr -s '[:space:]' '\n' | grep -c '[[:alnum:]]' || true)
printf '%-34s %8d  (limit %d)\n' "ABSTRACT" "$abs" "$ABSTRACT_LIMIT"

echo
tables=$( { cat sections/*.tex | grep -c '\\begin{table'; } || true)
figures=$( { cat sections/*.tex | grep -c '\\begin{figure'; } || true)
printf '%-34s %8d  (limit %d)\n' "TABLES" "$tables" "$TABLE_LIMIT"
printf '%-34s %8d  (limit %d)\n' "FIGURES" "$figures" "$FIGURE_LIMIT"
printf '%-34s %8d  (limit %d)\n' "DISPLAY ITEMS TOTAL" "$((tables + figures))" "$((TABLE_LIMIT + FIGURE_LIMIT))"

echo
todo=$( { grep -ro '\[TO COMPLETE\|\[INSERT\|\[DEGREES\]\|\[DEPARTMENT\]\|\[ORCID\|\[REPOSITORY\|\[FULL POSTAL\|\[INSTITUTIONAL EMAIL' . --include='*.tex' || true; } | wc -l)
overb=$( { grep -ro '\\overbudget{' . --include='*.tex' || true; } | wc -l)
printf '%-34s %8d\n' "PLACEHOLDERS TO FILL" "$todo"
printf '%-34s %8d\n' "OVER-BUDGET MARKERS" "$overb"
