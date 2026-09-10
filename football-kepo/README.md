## Setup

```bash
export FOOTBALL_CORPUS_PATH="./data/corpus.json"
export FOOTBALL_INJECTIONS_PATH="./data/injections.json"
export FOOTBALL_WORKING_DIR="./football-storage"
export FOOTBALL_ATTACK_WORKING_DIR="./football-storage-attack-copy"

mkdir -p ./results
export FOOTBALL_FINDINGS_PATH="./results/football_findings.jsonl"
export FOOTBALL_REPORT_PATH="./results/football_report.json"
```

## Run

```bash
cd football-kepo
python build_graph.py   # builds the clean graph from data/corpus.json
python run_injection_cycle.py   # shuffled attack+update injection cycle on a copy
```
