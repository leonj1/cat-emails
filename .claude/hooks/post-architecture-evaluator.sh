#!/bin/bash
# Post-architecture-evaluator hook
# This hook runs after the architecture-evaluator agent completes
# It signals to the orchestrator that the optimal solution has been selected

echo "Architecture-evaluator agent completed. specs/ARCHITECTURE-EVALUATION.md created."
echo "Optimal solution selected. Invoke request-fidelity-validator to validate the spec preserves user intent."
