#! /bin/bash


mkdir -p figs/ab-plot
ls -1 figs/*.svg | grep "ab-plot" | xargs -n 1 -I % cp % figs/ab-plot/
mkdir -p figs/bb-idocr
ls -1 figs/*.svg | grep "bb-idocr" | xargs -n 1 -I % cp % figs/bb-idocr/
mkdir -p figs/cc-idocr-facets
ls -1 figs/*.svg | grep "cc-idocr-facets" | xargs -n 1 -I % cp % figs/cc-idocr-facets/
mkdir -p figs/dd-idocr-masks
ls -1 figs/*.svg | grep "dd-idocr-masks" | xargs -n 1 -I % cp % figs/dd-idocr-masks/
mkdir -p figs/ee-legacy
ls -1 figs/*.svg | grep "ee-idocr-masks" | xargs -n 1 -I % cp % figs/ee-legacy
