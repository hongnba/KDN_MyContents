#!/bin/bash
# Wrapper to run test_llm_evaluation for multiple YAML prompt versions automatically.
# Usage:
#   ./run_llm_test_versions.sh [ITERATIONS] [VERSIONS]
# Examples:
#   ./run_llm_test_versions.sh 10 "1,2,3"    # run ver_1, ver_2, ver_3, each 10 iterations
#   ITERATIONS=5 VERSIONS="2" ./run_llm_test_versions.sh

set -euo pipefail

ITERATIONS=${1:-${ITERATIONS:-1}}
VERSIONS=${2:-${VERSIONS:-1,2,3}}
OLLAMA_MODEL=${OLLAMA_MODEL:-gpt-oss:20b}
TEST_IDS_FILE=${TEST_IDS_FILE:-test_ids_weekly_article_test_title_only.txt}

YAML_BASE_DIR="/app/ksubscribe_server/analysis/prompts"
YAML_BASENAME=${YAML_BASENAME:-20260102_geon}
YAML_SUFFIX=${YAML_SUFFIX:-ver}

# container and script paths
PY_CONTAINER=geon_python_unified
EVAL_SCRIPT=/app/ksubscribe_share/test/test_llm_evaluation.py
REPORT_SCRIPT=/app/ksubscribe_share/generate_excel_report.py

echo "Running versions: ${VERSIONS} with ${ITERATIONS} iterations each. Model: ${OLLAMA_MODEL}"

read -r -a VLIST <<< "${VERSIONS//,/ }"
for ver in "${VLIST[@]}"; do
    YAML_PATH="${YAML_BASE_DIR}/${YAML_BASENAME}_${YAML_SUFFIX}_${ver}.yaml"
    echo "=============================================="
    echo "Starting experiments for YAML: ${YAML_PATH}"
    echo "=============================================="

    # check file existence inside container
    if ! docker exec ${PY_CONTAINER} test -f "${YAML_PATH}" 2>/dev/null; then
        echo "Warning: YAML not found in container: ${YAML_PATH} — skipping"
        continue
    fi

    for i in $(seq 1 ${ITERATIONS}); do
        echo "--- Iteration ${i}/${ITERATIONS} for ${YAML_PATH} ---"
        docker exec ${PY_CONTAINER} python3 ${EVAL_SCRIPT} \
            --ollama-model "${OLLAMA_MODEL}" \
            --test-ids "${TEST_IDS_FILE}" \
            --yaml-prompt "${YAML_PATH}"
        echo "Done iteration ${i} for ${YAML_PATH}"
        # small pause to reduce burst load
        sleep 2
    done

    # generate per-version report (use iterations to limit latest N jsons)
    echo "Generating Excel report for model ${OLLAMA_MODEL} (latest ${ITERATIONS} JSONs)"
    docker exec ${PY_CONTAINER} python3 ${REPORT_SCRIPT} --model "${OLLAMA_MODEL}" --iterations "${ITERATIONS}" || echo "Report generation failed (continuing)"

    echo "Finished experiments for ${YAML_PATH}"
    echo
    # short cooldown between versions
    sleep 3
done

echo "All versions completed."
