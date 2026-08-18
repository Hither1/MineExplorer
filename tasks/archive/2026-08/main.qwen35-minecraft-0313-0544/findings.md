# Findings

Record only findings that change a decision, hypothesis, implementation contract, or
interpretation. Link to exact code, run IDs, logs, artifacts, papers, or commits instead of
copying their full contents.

| date | finding | evidence | confidence | implication |
|---|---|---|---|---|
| 2026-08-16 | The direct remote sandbox path is supported: the client sends JSON HTTP requests to `MC_SANDBOX_URL` and requires no local Docker. | `env/minerl_sandbox.py`; README Section 1 | high | MineExplorer may run on a223 while the evaluator runs on a219. |
| 2026-08-16 | a223 has 8 currently idle A100 80GB GPUs; all eight passed an independent 1024x1024 FP16 CUDA matmul and have zero reported ECC/row-remap errors. | a223 `nvidia-smi` and per-GPU PyTorch smoke | high for current health | Use GPU 0 first; the reported bad GPU is not currently identifiable from NVML/CUDA smoke evidence. |
| 2026-08-16 | a223 cannot run Docker as `ruihan`: socket is `root:docker 0660`, docker group contains only `ops`, passwordless sudo and root SSH are unavailable. | a223 `id`, `getent group docker`, `docker run --rm hello-world`, `sudo -n` | high | An authorized identity must start the README image or grant group access. |
| 2026-08-16 | Qwen3.5-27B is multimodal and its architecture plus required serving flags are present in a223's vLLM 0.19.0, but the approximately 55GB BF16 checkpoint is not cached. | official model card; vLLM registry/help; targeted cache probe | high | Model acquisition remains the second external gate. |
| 2026-08-16 | The agent can submit up to 20 screenshot frames per turn, while Qwen3.5 defaults to thinking. | `mc_agent/agent.py`; `mc_agent/llm_provider.py`; official model card | high | Bound image history/context and disable thinking for the initial Minecraft smoke. |
| 2026-08-16 | The image archive was modified at 04:01:06 by an orphaned downloader after its earlier validation, so its previous SHA-256 certificate is invalid. | final a223 process stop and archive `stat` | high | Do not use or `docker load` the retained archive without a fresh download or full revalidation. |
