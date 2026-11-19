# Nass — File Manifest

An overview of what this repository contains, and what it deliberately leaves out.

## Layout

| Path | Files | Purpose |
| --- | --- | --- |
| `README.md`, `PUBLIC_FILE_MANIFEST.md` | 2 | Documentation |
| `LICENSE` | 1 | GNU Affero General Public License v3.0, the official text (Nass is licensed AGPL-3.0-only) |
| `requirements.txt`, `requirements-doclayout.txt` | 2 | Runtime dependencies; optional PP-DocLayout dependencies |
| `.env.example`, `.gitignore` | 2 | Configuration template (placeholders only); ignore rules |
| `lab/launch.py`, `lab/__init__.py`, `lab/.streamlit/config.toml` | 3 | Local-only Streamlit launcher and settings |
| `lab/app/` | 7 | Streamlit entry point (`Home.py`), shared components and panels (Automatic Extraction, Benchmark Mode Phase 2, full-PDF runs, API gates) |
| `lab/app/pages/` | 8 | Sidebar sections: Documents, Run Text Extraction, Compare, Ground Truth, Results and Export, OCR VLM Evaluation, Local PDF Extraction Benchmark, **Hybrid PDF Extraction** |
| `lab/config/` | 5 | `auto_extraction.toml` (Automatic Extraction), `lab.toml`, `adapters.toml`, `models_e2.toml`, `providers_e2.toml` |
| `lab/core/auto/` | 17 | Automatic Extraction: configuration, router, layout regions, masking, figure crops, Qari client, pipeline, dedup, duplicate and digit checks, reading order, validation, assembly, run comparison |
| `lab/core/hybrid/` | 10 | Page analysis, decision logic, layout-aware assembly (layout v3), Benchmark Mode runs, Phase 2 enrichment, region rules, number validation |
| `lab/local_pdf_extraction/` | 10 | Native extractors, Arabic logical-order reconstruction, tables, diagnostics, the text-layer benchmark runner |
| `lab/core/e2/` | 25 | OCR/VLM evaluation: model registry and backends, hosted-API gates and runner, rendering, results store, air-gap guard |
| `lab/core/adapters/` | 8 | Text-extraction adapters, loaded through `adapters.toml` |
| `lab/core/` (modules) | 9 | Workspaces, ingest, runner, metrics, Ground Truth and review stores, settings, models |
| `runpod/` | 3 | Qari OCR service (FastAPI), offline batch runner, GPU-host requirements |

The total is 112 files. There is no binary data, no dataset, and no file larger than 1 MB.

## Not included, by policy

| Category | Notes |
| --- | --- |
| PDFs, datasets, Ground Truth, benchmark inputs and outputs | Bring your own documents. The evaluation pages accept your own files, and the optional reviewed document registry `lab/config/api_synthetic_documents.toml` is not shipped (the code treats it as empty). |
| Automated tests and test fixtures | Maintained separately |
| Run folders, OCR outputs, crops, evaluation scores | Generated locally under `AGENTICDOC_RESULTS_DIR` (default `~/agenticdoc/results`) |
| Benchmark and evaluation CLIs, and two evaluation-only pages | Maintained separately; the application does not import them |
| Air-gap lock files and deployment manifest | Optional. Without the manifest, the OCR VLM Evaluation page says so and works otherwise. |
| `.env`, tokens, credentials, endpoint hosts | Create `.env` from `.env.example` |
| Model weights and caches | PP-DocLayout from the official PaddleX URL (see `README.md`); Qwen3-VL and the Qari adapter from Hugging Face |
| Virtual environments, caches, logs, Git history | — |

The `.gitignore` enforces these exclusions, including paths used by the maintainers' private development add-ons.
