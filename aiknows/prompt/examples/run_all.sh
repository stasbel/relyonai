#!/usr/bin/env bash

for nb in *.ipynb; do
    jupyter nbconvert --execute --to notebook --inplace $nb \
        --ExecutePreprocessor.allow_errors=True \
        --ClearMetadataPreprocessor.enabled=True
done
