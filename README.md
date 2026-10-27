# GraphGuard

A data engineering pipeline over the Elliptic Bitcoin transaction dataset (about 200k transactions across 49 time steps).

## Setup (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

Place the Elliptic CSVs in `data/raw/` (gitignored):
`elliptic_txs_features.csv`, `elliptic_txs_classes.csv`, `elliptic_txs_edgelist.csv`.

### Troubleshooting: `CERTIFICATE_VERIFY_FAILED` on pip install

Antivirus HTTPS scanning (e.g. Avast Web Shield) re-signs traffic with its own root certificate, which Python's bundled CA list does not trust. Make pip use the Windows certificate store instead:

```powershell
$env:PIP_USE_FEATURE="truststore"
pip install -e ".[dev]"
```

## Status

Phase 0: setup.
