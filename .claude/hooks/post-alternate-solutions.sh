#!/bin/bash
# Post-alternate-solutions hook
# This hook runs after the alternate-solutions agent completes
# It signals to the orchestrator that alternatives are ready for evaluation

echo "Alternate-solutions agent completed. specs/ALTERNATIVE-SOLUTIONS.md created."
echo "Invoke architecture-evaluator agent to evaluate all solutions and select the optimal approach."
