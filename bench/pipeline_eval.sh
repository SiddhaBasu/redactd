#!/bin/bash
# Full ensemble on a given eval set: run each component, then score the combination with propagation.
set -e; cd "$(dirname "$0")/.."; . .venv/bin/activate
EV=${1:-eval_gretel_fin_holdout}
for d in regex org_rules openmed_small gliner_knowledgator; do THREADS=${THREADS:-1} python bench/run_eval.py $d $EV 2>&1 | grep '^{' | cut -c1-260; done
python bench/ensemble_eval.py $EV regex,openmed_small,gliner_knowledgator,org_rules --prop --miss
