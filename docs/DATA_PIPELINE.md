# DATA PIPELINE (reproducible stages)

Training pipeline (historical, versioned) is separate from the live
inference pipeline (worker). Stages are independently runnable:

```
ingest_coolr.py ─┐
ingest_gsi.py ───┼─→ build_inventory.py (NER filter, date classes, dedup)
ingest_nrsc.py ──┘         ↓ ner_inventory (TEMPORAL/SPATIAL) + report
              build_controls.py (matched NO_RECORDED_LANDSLIDE)
                           ↓
fetch_rainfall.py (Open-Meteo archive, cached, ≤T clip)
ingest_smap.py    (AUTH boundary / manual)
ingest_dem.py     (SRTM 5x5 windows, cached)
ingest_sentinel1.py (ASF REAL metadata discovery)
ingest_osm.py     (Overpass counts, cached)
                           ↓
              build_features.py (provenance + missingness per value)
                           ↓
     build_training_dataset.py --region NER --version ner_v1
                           ↓
              run_leakage_checks.py (binding gates; PARTIAL disclosed)
                           ↓
              train_models.py --dataset ner_v1 (LogReg→RF→GBM)
                           ↓
              evaluate_models.py / register_model.py (gate verdicts)
                           ↓
              final_dataset_audit.py (mandated audit block)
```

Reproduce: build_training_dataset → train_models → evaluate_models →
register_model. Full refresh: run stages top-down (caches make reruns cheap;
`--force` where supported). Imputation: group-median, recorded per cell;
all-missing columns excluded, never zero-filled. Live inference never feeds
training (training reads versioned CSV + caches, never production tables).
