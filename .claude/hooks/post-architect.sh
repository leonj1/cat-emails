#!/bin/bash
# Post-architect hook
# This hook runs after the architect agent completes
# It signals to the orchestrator that the DRAFT spec is ready for alternative solutions

echo "Architect agent completed. DRAFT spec created in specs/DRAFT-*.md"
echo "Invoke alternate-solutions agent to generate 3 alternative architectural approaches."
echo "After alternatives are generated, architecture-evaluator will select the optimal solution."
