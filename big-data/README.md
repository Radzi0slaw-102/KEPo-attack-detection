## Setup

```bash
source ../.venv/bin/activate
cd lightrag-att-det
export VARIANT=Graph-Story   # or: Graph-Medical | MuSiQue
export KEPO_DATASET_DIR=./data/$VARIANT
export KEPO_GENERATOR_MODEL=qwen2.5:32b
export KEPO_FABRICATOR_MODEL=qwen2.5:32b
export KEPO_EVALUATOR_MODEL=qwen2.5:32b
```

## 1. Fetch corpus & targets (skipped automatically if already present)

```bash
python fetch_corpus.py $VARIANT $KEPO_DATASET_DIR
python fetch_targets.py $VARIANT $KEPO_DATASET_DIR
```

## 2. Build the clean graph

```bash
export LIGHTRAG_WORKING_DIR=./storage/$VARIANT
python build_graph.py
```

## 3. Attack a copy of the clean graph

```bash
cp -r ./storage/$VARIANT ./storage/${VARIANT}-attack
export LIGHTRAG_WORKING_DIR=./storage/${VARIANT}-attack
python attack.py
```