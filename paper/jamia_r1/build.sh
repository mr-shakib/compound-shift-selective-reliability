#!/usr/bin/env bash
# Build the JAMIA R1 submission: budget (writes wordcount.tex), supplement
# (its labels are cross-referenced by the main text), main manuscript, then
# the separate figure files JAMIA asks for.
set -euo pipefail
cd "$(dirname "$0")"
python3 budget.py
latexmk -pdf -interaction=nonstopmode -halt-on-error supplement_jamia_r1.tex >/dev/null
latexmk -pdf -interaction=nonstopmode -halt-on-error main_jamia_r1.tex >/dev/null
# Rebuild main once more so cross-document references settle.
latexmk -g -pdf -interaction=nonstopmode -halt-on-error main_jamia_r1.tex >/dev/null
latexmk -pdf -interaction=nonstopmode -halt-on-error tripod_ai_checklist_r1.tex >/dev/null
latexmk -g -pdf -interaction=nonstopmode -halt-on-error cover_letter.tex >/dev/null
mkdir -p figures_for_upload
i=0
for f in fig2_label_composition fig1_h1_specifications fig4_operating_points fig3_risk_coverage fig5_h4_within_site; do
  i=$((i+1))
  cp "../revision/figures/$f.pdf" "figures_for_upload/Figure${i}.pdf"
  pdftoppm -png -r 600 -singlefile "../revision/figures/$f.pdf" "figures_for_upload/Figure${i}"
done
for d in main_jamia_r1 supplement_jamia_r1 tripod_ai_checklist_r1 cover_letter; do
  if grep -q -E "Overfull|undefined|Undefined" "$d.log"; then
    echo "WARNING: $d.log has overfull boxes or undefined references"; grep -n -E "Overfull|ndefined" "$d.log" | head
  fi
done
echo "Built: main_jamia_r1.pdf, supplement_jamia_r1.pdf, tripod_ai_checklist_r1.pdf, cover_letter.pdf, figures_for_upload/"
