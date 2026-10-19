# Final Kaggle evaluation

The final French benchmark uses the reviewed corpus and frozen release manifest. It does not rerun OCR. Qwen3-4B runs through Hugging Face Transformers with bitsandbytes NF4; no C++ or CUDA compilation is required.

From a clean `develop` checkout, generate the private input bundle:

```bash
uv run --frozen python scripts/build_kaggle_final_bundle.py
```

The command verifies the release freeze and writes `runs/constitution-evidence-final-input.zip`. The ZIP includes the 180 reviewed questions, processed corpus, validation runs, release manifest, and a shallow Git checkout. Its Git metadata is embedded in `runs/kaggle-bundle.json` so it survives Kaggle's automatic ZIP extraction. **Keep it in a private Kaggle dataset.** It is ignored by Git and must not be attached to a public notebook or repository.

In Kaggle, enable GPU and Internet, add that dataset as an input, open the current `notebooks/kaggle_final.ipynb`, and run its cells in order. The first cell accepts either the ZIP or Kaggle's automatically extracted folder and repairs an interrupted copy. Replace any older input dataset with the newly built ZIP after updating the notebook. If the dependency cell asks for a kernel restart, restart and run all cells again. The model is pinned to `Qwen/Qwen3-4B` revision `1cfa9a7208912126459214e8b04321603b3df60c`. The complete corpus needs about 35,600 tokens including the output reserve, above Qwen3-4B's native 32,768-token context. The notebook applies [Qwen's documented YaRN configuration](https://huggingface.co/Qwen/Qwen3-4B#processing-long-texts) with factor 2 and a 65,536-token capacity to all three systems, and records it in the model provenance. If the exact full-text prompt still exceeds capacity, the run records a budget error without truncating the corpus. The notebook verifies the source commit and all private input hashes before opening the 90 reserved test questions. It then runs the full-text, BM25, and selected hybrid systems with the same model and prompt. Each answer is saved immediately under `runs/final-reserved-qwen4b-transformers/` and the run resumes in the same Kaggle working directory.

Use the final cell to create `/kaggle/working/constitution-final-results.zip`, then download it from Kaggle Output before the session closes. The result ZIP may also be created after an interrupted run to preserve completed rows. Bring that ZIP back to this workspace for blind packet preparation and final scoring. Do not publish either ZIP; the outputs contain test responses.
