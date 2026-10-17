# Gitflow for this repository

- `main` contains reviewed releases. Tag each published version `vMAJOR.MINOR.PATCH` and attach corpus hash, run manifest, and limitations.
- `develop` integrates completed work. Open pull requests into `develop` from `feature/<short-name>`; use `fix/<short-name>` for ordinary corrections.
- `release/<version>` starts from `develop` after the corpus and validation settings are frozen. Only documentation, reproducibility, and release fixes go here. Merge to `main`, tag, then merge back to `develop`.
- `hotfix/<short-name>` starts from `main` for a release defect. Merge to both `main` and `develop` and tag a patch release.
- Protect `main` and `develop` in the remote hosting settings: require CI and review. This setting cannot be encoded in Git history.

For each PR, record tests and any corpus, annotation, or benchmark impact. A changed source or correction creates a new corpus hash. Test questions and outputs must not guide prompt or model selection before the final freeze. Large PDFs, OCR language data, and generated runs stay out of Git; their URLs and hashes go in manifests.

The local `develop` branch has been created. Create feature branches from `develop`. The planning directory and implementation are being added without rewriting `main` history.
