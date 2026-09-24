# Building the paper PDF

```
pandoc paper/After_Attention_draft_v0.11.md \
  -o paper/After_Attention_draft_v0.11.pdf \
  --pdf-engine=xelatex \
  -H paper/build/preamble.tex \
  -V documentclass=article -V fontsize=11pt -V geometry:margin=1in \
  --toc --toc-depth=2
```

Requires pandoc and xelatex. xelatex rather than pdflatex because the tables carry
Unicode Greek.

Drafts up to v0.10 were built by `build_pdf.py`, which rendered mathematics by
regular expression. That script could not parse nested fractions: it flattened
`\frac{...}{T}` containing a `\tfrac` into a form where T read as a multiplier
rather than the denominator, which misprinted condition (ii) of Proposition 3 and
every other nested fraction in the paper. The markdown source was correct
throughout; only the generated PDF was wrong. The script is not used any more and
is not in this repository.
