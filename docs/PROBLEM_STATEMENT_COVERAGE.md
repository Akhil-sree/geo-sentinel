# PROBLEM STATEMENT COVERAGE MATRIX

| Requirement | Implementation | Evidence | Test | Status | Limitation |
|---|---|---|---|---|---|
| Rainfall monitoring | Open-Meteo adapter + mock, persisted, trim | 1328 live rows 2026-09-14 | live + persist tests | DONE (live opt-in) | keyless provider only |
| Soil moisture | observed/modeled split, source tags | `soil_moisture_source` in data-status | validation tests | DONE (modeled) | no in-situ sensors |
| Satellite | metadata layer, quarantine, SAR banner | `scene_status`, SIMULATED banner | quarantine test | PARTIAL | no imagery |
| Terrain | 8 profiles + provenance meta | `/gis/provenance` | endpoint test | PARTIAL | no DEM/aspect/curvature |
| Historical landslides | 10 events → events_v2 (n=24) | CSV+JSON+gate PASS | dataset test | PARTIAL | n=24, demo inventory |
| AI prediction | LogReg/RF/GBM + Mamba pipeline + registry | model card metrics | training tests | DONE (weak, honest) | F1 ~0.5, none promoted |
| Periodic monitoring | 15-min worker, jobs, idempotency | `/jobs`, `/worker-status` | lock/idempotency tests | DONE | not streaming (labeled) |
| GIS | zones/cells/trajectory/hotspots/exposure | drilldown endpoint | e2e test | DONE | static boundaries |
| Roads | 8 segments, statuses, provenance | `/roads` + provenance | e2e test | DONE (demo) | static network |
| Villages/infra | zone population, emergency tasks | priorities endpoint | — | PARTIAL | indicative figures |
| Field reports + photo/video + geotag | GPS/mime/magic/size/hash, idempotent sync | 409/415/422/201 paths | failure tests | DONE | moderation manual |
| Alerts | threshold/cooldown/escalation/ack/resolve/audit | lifecycle endpoints | e2e + idem tests | DONE (mock delivery) | no live SMS run |
| Multilingual | en/hi reviewed, fallback en | templates + lang_status | — | DONE | as/mni fallback |
| Offline | IndexedDB queue, retry, sync status UI | queue + status line | offline tests | DONE (field scope) | not full PWA |
| Routing | A* slope-aware + baseline compare | cost fn + baseline_route | e2e test | DONE | "lower-exposure", not safe |
| Prioritization | urgency composite endpoint | emergency-priorities | — | DONE | weights are config |
| Cloud deployment | compose + prod profile + migrate | Dockerfile/migrate | migrate run | PARTIAL | daemon down, pg unbooted |
| Security | roles, SecretBox, headers, limits, audit | headers/limits/audit | 401/403 tests | DONE (demo-grade) | no JWT |
| Audit | REPORT_/ALERT_ actions | audit_logs | e2e test | DONE | — |
| Explainability | permutation/importance/heuristic + method | method field | XAI tests | DONE | no SHAP (labeled) |
