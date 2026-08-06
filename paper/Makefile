# Build the C3E paper.
#
# The toolchain is not installed on the development host. Install with:
#   sudo apt install texlive-latex-recommended texlive-latex-extra \
#                    texlive-science texlive-fonts-recommended latexmk

PAPER = main

.PHONY: all clean watch
all: $(PAPER).pdf

$(PAPER).pdf: $(PAPER).tex references.bib $(wildcard sections/*.tex)
	latexmk -pdf -halt-on-error $(PAPER).tex

watch:
	latexmk -pdf -pvc $(PAPER).tex

clean:
	latexmk -C
	rm -f $(PAPER).bbl $(PAPER).run.xml
