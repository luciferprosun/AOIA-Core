# H22 NVIDIA NeMo/NIM Feasibility Audit

## Purpose
Assess whether NVIDIA NeMo/NIM/Guardrails can support AIOA Whitehat without disrupting local development.

## Local Hardware Reality
- CPU/kernel: Linux `l` on x86_64, kernel `6.17.0-23-generic #23~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Tue Apr 14 16:11:48 UTC 2`.
- RAM: `3.7Gi` total, `2.6Gi` used, `645Mi` free, `1.1Gi` available, with `5.8Gi` swap and `4.4Gi` swap already used.
- Disk at repository path: `/dev/mmcblk0p2`, `57G` total, `50G` used, `3.7G` available, `94%` used.
- NVIDIA GPU availability: `nvidia-smi` not found; no usable NVIDIA GPU should be assumed.
- Docker availability: `/usr/bin/docker` exists, but no Docker pulls or container tests were performed.
- Python version: `Python 3.12.3`; interpreter path `/usr/bin/python3`.
- Other tooling: `gh` exists at `/home/l/.local/bin/gh`; `pipx` exists at `/usr/bin/pipx`.

## Options Compared

### 1. Full NVIDIA NeMo Framework
Full NVIDIA NeMo Framework is likely heavy for this local machine. It is commonly oriented around GPU-accelerated training/fine-tuning workflows, containerized environments, NGC-style distribution, and larger development systems.

Recommendation: not recommended for the current weak local machine. Do not install it now, do not pull Docker images, and do not make it part of AIOA runtime.

### 2. NeMo Microservices / Platform
NeMo Microservices / Platform style deployments are likely too heavy for local use here. They should be treated as production or enterprise infrastructure candidates rather than a practical local development dependency for this laptop-class environment.

Recommendation: not recommended locally now. Do not attempt Kubernetes, enterprise platform, or microservice deployment work during current AIOA production tasks.

### 3. NeMo Guardrails Python Library
NeMo Guardrails is the only NVIDIA NeMo-family option that may be feasible as a small local experiment. It is Python-library oriented and can be evaluated as a design/reference layer for conversational safety, rails, and policy modeling.

Constraints: if tested later, use a separate virtual environment under an isolated experiment directory only. Do not install into the project runtime environment. Do not connect it to provider/router/executor logic without a separate governance gate.

Recommendation: potentially feasible later as an isolated CPU-only experiment, not as a production dependency now.

### 4. NVIDIA NIM API / build.nvidia.com
NVIDIA NIM API / build.nvidia.com is the best candidate for near-term exploration because inference can be cloud-hosted and does not require a local NVIDIA GPU. It could later be tested as an external model/provider feasibility probe.

Constraints: it must not become a hard dependency, must not store API keys in the repository, and must not be wired into AIOA runtime until separately approved. Any future probe should use a standalone script and manual secret handling outside git.

Recommendation: best candidate for later evaluation, after the user manually creates or confirms NVIDIA Developer access and API-key availability.

## Recommendation
- Do not interrupt AIOA production.
- Do not install full NeMo Framework.
- Do not pull Docker containers now.
- First create or log into an NVIDIA Developer account manually.
- Later test NIM API from an isolated script only.
- Optional: test NeMo Guardrails in a separate virtual environment after explicit approval.
- Keep NVIDIA tooling out of runtime/provider/router/executor code until a separate integration review.

## Safe Next Steps
1. User manually creates or logs into NVIDIA Developer account.
2. User checks build.nvidia.com models and API key availability.
3. Codex later creates a docs-only provider feasibility plan.
4. If approved, create isolated directory `experiments/nvidia_nim_probe/` with no runtime integration.
5. If approved separately, create isolated virtual environment for a NeMo Guardrails test under `experiments/nemo_guardrails_probe/`, but do not connect it to AIOA runtime.

## Boundaries
- No install was performed.
- No Docker pull was performed.
- No runtime code was modified.
- No provider integration was added.
- No provider/router/executor logic was changed.
- No NVIDIA runtime dependency was added.
- No API keys were requested, exposed, stored, or committed.
- No secrets were committed.
- Current Python Master Library work was not changed.

## Validation
- `python3 -m compileall runtime tests`: passed.
- `PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p "test*.py" -v`: passed, `330` tests OK, `4` skipped.
