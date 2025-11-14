#!/bin/bash
# tests/test_l_menthol_workflow.sh (FIXED)

# Get project root (assuming script is in tests/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Use absolute paths
cp "${PROJECT_ROOT}/data/L-MENTHOL-toxicity-data.json" "${PROJECT_ROOT}/data/toxicity_data_template.json"

# Run test from project root
cd "${PROJECT_ROOT}"
python3 tests/test_l_menthol.py

# Save result
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "${PROJECT_ROOT}/data/test_results"
cp "${PROJECT_ROOT}/data/toxicity_data_template.json" "${PROJECT_ROOT}/data/test_results/L-MENTHOL_result_${TIMESTAMP}.json"

echo "✅ Result saved to: ./data/test_results/L-MENTHOL_result_${TIMESTAMP}.json"