# Data: the Elliptic Bitcoin dataset

The source is the "Elliptic Data Set" on Kaggle, published by Elliptic. It is not stored in this repo (the files are large, and the licence may restrict redistribution). Download it from Kaggle and place the three CSVs in `data/raw/elliptic_bitcoin_dataset/`.

The dataset is a Bitcoin transaction graph. Each **node** is a transaction, each **edge** is a flow of coins from one transaction to a later one that spends it, and every transaction belongs to one of **49 time steps**. Some transactions are labelled illicit or licit; most are not.

## The three files

| File | Rows | Header row | What it holds |
|---|---|---|---|
| `elliptic_txs_features.csv` | 203,769 | **no** | one row per transaction: id, time step, 165 anonymised features |
| `elliptic_txs_classes.csv` | 203,769 | yes (`txId,class`) | the label of each transaction |
| `elliptic_txs_edgelist.csv` | 234,355 | yes (`txId1,txId2`) | directed edges between transactions |

### Features: 167 columns

| Position | Raw | Pipeline name | Type |
|---|---|---|---|
| 1 | transaction id | `tx_id` | int64 |
| 2 | time step | `time_step` | int64, 1 to 49 |
| 3 to 167 | 165 anonymised features | `feat_1` to `feat_165` | float64 |

Per the dataset's published description, the first 93 features describe the transaction itself and the remaining 72 aggregate information about its neighbouring transactions. All are anonymised, so their meaning is not recoverable.

The file has **no header row**, so the first line is already a transaction. Reading it with a plain `pd.read_csv` would take that transaction as the column names and silently lose it. The loader supplies the names and checks the column count (see [DECISIONS.md](../DECISIONS.md)).

### Classes: the `unknown` problem

| Raw value | Meaning | Rows | Pipeline `label` |
|---|---|---|---|
| `1` | illicit | 4,545 | `1` |
| `2` | licit | 42,019 | `2` |
| `unknown` | not labelled | 157,205 (77%) | null |

The column mixes numbers with the word `unknown`, which makes it a text column. The pipeline keeps the original text in `class_raw` and adds `label`, a nullable integer (`Int64`) where `unknown` is a real null. A plain integer column cannot hold nulls, so pandas would turn the labels into floats.

### Edges: direction and names

Each edge is directed: money flowed from the first transaction to the second. The raw columns `txId1` and `txId2` do not say which is which, so the pipeline renames them to `src_tx_id` and `dst_tx_id`. Phase 2 counts out-degree from `src_tx_id` and in-degree from `dst_tx_id`, and mixing them up would silently swap the features.

## Time steps

There are 49 time steps, numbered 1 to 49 with no gaps. They are very uneven in size:

| | Transactions | Step |
|---|---|---|
| Smallest | 1,089 | 27 |
| Largest | 7,880 | 1 |

Edges per step range from 1,168 to 9,164. The uneven sizes matter later: Airflow will run one job per time step, and the jobs will take different amounts of time.

Published results on this dataset show that models trained on the early steps collapse in performance after time step 43. That shift is what the drift check in Phase 6 is built to show.

## What was verified

Checked against the real files, and enforced on every run by the pipeline:

| Check | Result |
|---|---|
| Time steps are integers from 1 to 49 | pass, no gaps |
| Duplicate `tx_id` in features or classes | none |
| Nulls in the features | none |
| Classes and features have exactly the same transaction ids | yes |
| Edge endpoints missing from the features file (orphan edges) | none |
| Duplicate edges, self-loops, reverse pairs | none |
| Edges that connect two different time steps | **none** |

The last row is the important one. Because no edge crosses a time step, **each time step is a self-contained graph**. That is why edges are partitioned by their source transaction's step, and why Spark and Airflow can process one step at a time with no cross-step joins.

These checks show that the current files are clean. They do not prove a future version of the dataset will be, so the pipeline re-runs them every time.

## Output

The pipeline writes Parquet to `data/processed/`, one folder per time step, with the step in the folder name (`time_step=7/`). The partition column is left out of the files, following the convention DuckDB and Spark expect. See [architecture.md](architecture.md) for the layout and how reruns behave.
