# Final Kaggle evaluation

The final French benchmark uses the reviewed corpus and frozen release manifest. It does not rerun OCR. Qwen3-4B runs through Hugging Face Transformers with bitsandbytes NF4; no C++ or CUDA compilation is required.

From a clean `develop` checkout, generate the private input bundle:

```bash
uv run --frozen python scripts/build_kaggle_final_bundle.py
```

For the T4 recovery after the first run's 90 full-text CUDA out-of-memory errors, build a new private bundle from the saved results instead:

```bash
uv run --frozen python scripts/build_kaggle_final_bundle.py \
  --previous-results runs/constitution-final-results.zip
```

The recovery bundle includes the original result manifest, model provenance, BM25 answers and selected-pipeline answers. It checks matching corpus, questions, model and system hashes, records the source ZIP checksum, and reruns only the full-text questions. After a single T4 failed with a regular cache, an offloaded cache, and a chunked offloaded cache that restarted the kernel, this run requires **T4 x2**. Accelerate distributes the same pinned Qwen model across both GPUs. The full prompt is prefetched in 512-token passes into a GPU-resident KV cache, then decoded with Transformers. This bounds the attention work per forward pass and avoids the host-RAM pressure of cache offloading. The old 11 BM25 and 19 hybrid generation errors remain recorded as observed failures; the recovery does not cherry-pick replacements. This is a documented post hoc infrastructure repair.

The command verifies the release freeze and writes `runs/constitution-evidence-final-input.zip`. The ZIP includes the 180 reviewed questions, processed corpus, validation runs, release manifest, and a shallow Git checkout. Its Git metadata is embedded in `runs/kaggle-bundle.json` so it survives Kaggle's automatic ZIP extraction. **Keep it in a private Kaggle dataset.** It is ignored by Git and must not be attached to a public notebook or repository.

In Kaggle, select **GPU T4 x2** and enable Internet, add that dataset as an input, open the current `notebooks/kaggle_final.ipynb`, and run its cells in order. The second cell checks both GPU memory pools before loading Qwen; one T4 is rejected without starting the long calculation. The first cell accepts either the ZIP or Kaggle's automatically extracted folder and repairs an interrupted copy. Replace any older input dataset with the newly built ZIP after updating the notebook. If `/kaggle/working` still contains an older commit, the first cell backs up its run to `constitution-final-results-before-upgrade-*.zip` before replacing it. If that run has successful full-text answers, the cell stops so they can be imported into a new recovery bundle; it does not discard them. If the dependency cell asks for a kernel restart, restart and run all cells again. The model is pinned to `Qwen/Qwen3-4B` revision `1cfa9a7208912126459214e8b04321603b3df60c`. The complete corpus needs about 35,600 tokens including the output reserve, above Qwen3-4B's native 32,768-token context. The notebook applies [Qwen's documented YaRN configuration](https://huggingface.co/Qwen/Qwen3-4B#processing-long-texts) with factor 2 and a 65,536-token capacity to all three systems, and records it in the model provenance. If the exact full-text prompt still exceeds capacity, the run records a budget error without truncating the corpus. The notebook verifies the source commit and all private input hashes before opening the 90 reserved test questions. Each answer is saved immediately under `runs/final-reserved-qwen4b-transformers/` and the run resumes in the same Kaggle working directory. A repeated full-text CUDA out-of-memory error stops after one saved error; export that partial result instead of repeating 90 failures.

Use the final cell to create `/kaggle/working/constitution-final-results.zip`, then download it from Kaggle Output before the session closes. The result ZIP may also be created after an interrupted run to preserve completed rows. If the session ends, use that partial ZIP as `--previous-results` when rebuilding the next private bundle: matching successful full-text rows are carried forward, while error rows remain in the archived attempt and are rerun. Bring the completed ZIP back to this workspace for blind packet preparation and final scoring. Do not publish either ZIP; the outputs contain test responses.
