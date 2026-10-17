# Local generation option

The offline model path uses the official Apache 2.0 [Qwen3 1.7B GGUF](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF) through [llama.cpp's local server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md). It avoids a paid generation API. The 1.83 GB Q8 model was selected for this machine's 8 GB RAM and CPU only setup; a larger model may swap heavily. This is a capacity choice, not a demonstrated quality winner. The 4B model should be compared only after corpus review and benchmark labels exist.

Install llama.cpp from its official instructions, download the model into `data/models/Qwen3-1.7B-Q8_0.gguf`, then run:

```bash
llama-server -m data/models/Qwen3-1.7B-Q8_0.gguf --host 127.0.0.1 --port 8080 -c 4096 -t 4 --jinja
constitution-evidence ask 'Que dit l’article 20 ?' --generator local
```

The UI's “Résumé local expérimental” mode calls the same local server. Set `LOCAL_LLM_URL` and `LOCAL_MODEL_ID` if its address or served model ID differs. The adapter sends the selected passages, asks for JSON claims and exact quotes, and checks IDs, hashes, offsets, and quote equality after generation. A valid quote does not prove the model's explanation follows from it; claims are marked `unverified_semantic`. On an unreviewed OCR corpus, `answered` is downgraded to `partially_answered` and a source warning is included.

The 4,096 token server context excludes a full text baseline. The local adapter rejects context over 8,000 characters instead of silently truncating it. This model may be slow on the current CPU and should not be presented as legally reliable without the planned French evaluation.
