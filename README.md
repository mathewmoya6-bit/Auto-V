# AUTO-V — New Modules: Instant Value & Vehicle Assessments

Scaffolds for the two new modules from your sidebar plan, built to match the
pattern visible in your `main.py` (FastAPI, `app/api/v1/api.py` router
aggregator, `settings.api_v1_prefix`).

## What's in here

```
instant_value/
  schemas.py   -> app/schemas/instant_value.py
  service.py   -> app/services/instant_value_service.py
  router.py    -> app/api/v1/endpoints/instant_value.py

vehicle_assessments/
  schemas.py   -> app/schemas/vehicle_assessment.py
  service.py   -> app/services/vehicle_assessment_service.py
  router.py    -> app/api/v1/endpoints/vehicle_assessments.py

api_router_update.py -> snippet to add to app/api/v1/api.py
```

Copy each file to the path shown in its header comment inside your repo.

## Module design

**Instant Value** — a quick, standalone estimate tool. Takes make/model/year/
mileage/condition and returns an estimate immediately, no vehicle record
required. If the caller is authenticated, the estimate is saved to their
history. This is separate from your existing `Valuation` module, which
presumably operates on an already-created `Vehicle`.

**Vehicle Assessments** — a composite report layered *on top of* your
existing `Valuation`, `Inspections`, and `Mileage` modules. It pulls the
latest record from each, scores them, and produces one overall
condition grade (A–F) with recommendations. It doesn't replace those
modules or duplicate their storage.

New endpoints (7 total):

| Method | Path |
|---|---|
| POST | `/api/v1/instant-value/estimate` |
| GET | `/api/v1/instant-value/estimate/{estimate_id}` |
| GET | `/api/v1/instant-value/history` |
| POST | `/api/v1/vehicles/{vehicle_id}/assessments` |
| GET | `/api/v1/vehicles/{vehicle_id}/assessments` |
| GET | `/api/v1/assessments/{assessment_id}` |
| GET | `/api/v1/assessments/{assessment_id}/report` |

## Things I had to assume (please verify/adjust)

I only had your `main.py`, not the rest of the repo, so I couldn't see your
actual model names, DB session dependency, or auth dependency. Every place
that needs one is marked `# TODO(integration)` or commented out:

1. **`get_db`** — your DB session dependency. Assumed to live in
   `app.api.deps`.
2. **`get_current_user`** (required) and **`get_current_user_optional`**
   (returns `None` instead of 401 when no token given) — assumed to live in
   `app.api.deps`. If you don't have the "optional" variant, you'll need to
   add one for the public-friendly Instant Value endpoint, or just make the
   whole module require auth if you'd rather keep it simple.
3. **Ownership checks** — e.g. verifying the caller owns `vehicle_id` before
   creating/reading an assessment. Your `Vehicles`/`Inspections` modules
   almost certainly already have this pattern (probably a `404` if the
   vehicle doesn't belong to `current_user`) — reuse it here instead of
   whatever I'd guess at.
4. **Persistence** — both services are pure-logic + stubbed save/read
   functions (commented-out SQLAlchemy calls). No new tables were assumed to
   exist yet; you'll need migrations for `instant_value_estimates` and
   `vehicle_assessments` tables if you want history/persistence rather than
   fire-and-forget calculation.
5. **Pricing data** in `instant_value_service.py` is a placeholder
   straight-line depreciation heuristic — swap `_estimate_base_value` for
   whatever real pricing source your `Valuation` module already uses, so the
   two don't give wildly different numbers for the same car.

## Next steps

1. Drop the files into your repo at the paths in each header comment.
2. Uncomment the `Depends(...)` lines once you point them at your real
   `app.api.deps` functions.
3. Wire in `api_router_update.py`'s two `include_router` calls.
4. Add the two new tables/migrations if you want persistence (or ship it
   stateless first and add storage later — the endpoints work either way).
5. Hit `/docs` again — you should now see **Instant Value** and
   **Vehicle Assessments** as two new tags alongside your existing nine.
