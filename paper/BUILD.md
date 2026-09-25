# Building the paper PDF

```
pandoc paper/After_Attention_draft_v0.15.md \
  -o paper/After_Attention_draft_v0.15.pdf \
  --pdf-engine=xelatex \
  -H paper/build/preamble.tex \
  -V documentclass=article -V fontsize=10pt -V geometry:margin=1in \
  --resource-path=.:paper
```

Requires pandoc and xelatex. xelatex rather than pdflatex because the tables carry
Unicode Greek.

**Settings, corrected 25 Sep 2026.** This file used to say 11pt with `--toc --toc-depth=2`.
That does not reproduce the v0.13 or v0.14 PDFs: they are set at 10pt with no table of
contents (11pt gives about 44 pages against 36). The 10pt, no-TOC command above does.

**Checked with a different engine.** `brew install pandoc tectonic`, then the same command
with `--pdf-engine=tectonic` (a self-contained XeTeX-based engine, no TeX distribution
needed). Rebuilding v0.14 that way reproduces the posted v0.14's text (98.7% word-stream
match; 37 pages against 36, from small line-break differences). The v0.15 PDF was built
this way.

Drafts up to v0.10 were built by `build_pdf.py`, which rendered mathematics by
regular expression. That script could not parse nested fractions: it flattened
`\frac{...}{T}` containing a `\tfrac` into a form where T read as a multiplier
rather than the denominator, which misprinted condition (ii) of Proposition 3 and
every other nested fraction in the paper. The markdown source was correct
throughout; only the generated PDF was wrong. The script is not used any more and
is not in this repository.
