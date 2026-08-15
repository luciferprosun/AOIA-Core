#!/usr/bin/env bash
set -euo pipefail

final_root=/home/l/AIOA_DEMO_KM/AIOA-Memory-Patch-Final-Recording-Demo
memory_root=/media/l/LSC_DATA/AIOA_WORKSPACE/hackathons/AIOIA_HACKATHONS/Memory-Patch-for-AIOA-Hackathon-CockroachDB
memory_baseline=73e30ec2dad1e31c03a02119c4969e0c78ec76dc
asm_exec=/home/l/.codex/plugins/cache/agent-toolkit-for-aws/aws-core/1.1.0/skills/aws-secrets-manager/references/asm-exec
provider_reference='{{resolve:secretsmanager:arn:aws:secretsmanager:eu-central-1:787391403107:secret:memory-patch-aioa-demo-1a/runtime-EXA07f:SecretString:OPENROUTER_API_KEY:AWSCURRENT}}'

observed_memory_commit="$(git -C "$memory_root" rev-parse HEAD)"
if [[ "$observed_memory_commit" != "$memory_baseline" ]]; then
  echo "Refusing to start: frozen Memory Patch baseline differs." >&2
  exit 1
fi

for resolution_attempt in 1 2 3 4; do
  set +e
  env \
    AWS_PROFILE="${AWS_PROFILE:-aoia-admin}" \
    AWS_REGION="${AWS_REGION:-eu-central-1}" \
    AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-central-1}" \
    OPENROUTER_API_KEY="$provider_reference" \
    "$asm_exec" -- env \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$final_root:$memory_root/src:$memory_root/scripts" \
    "$memory_root/.venv/bin/python" \
    "$final_root/scripts/run_final_recording_demo.py"
  launch_status=$?
  set -e
  if [[ $launch_status -eq 0 ]]; then
    exit 0
  fi
  if [[ $launch_status -eq 70 ]]; then
    exit 70
  fi
  if [[ $resolution_attempt -lt 4 ]]; then
    echo "Secure runtime reference unavailable; retrying asm-exec ($resolution_attempt/4)..." >&2
    sleep 2
  fi
done

echo "Final recording demo did not start: SECURE_RUNTIME_REFERENCE_UNAVAILABLE" >&2
exit 1
