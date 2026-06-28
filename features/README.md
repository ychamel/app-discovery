# features/

Each feature that goes through the pipeline gets **one folder** here, named with a
kebab-case slug (e.g. `weekly-digest/`, `quality-score-v1/`, `submission-intake/`).

All artifacts for a feature live together in its folder, so a feature is a
self-contained, self-documenting unit. The agent works on exactly one feature's folder
at a time — the *active feature* named in [../CONTROL.md](../CONTROL.md).

[INDEX.md](INDEX.md) in this directory is the registry of **every** feature and its
outcome — the answer to "have we built anything about X?" that the single active-feature
dashboard in `CONTROL.md` can't give you once there are many folders.

## Standard layout

### Feature Track Layout
```
features/<feature-slug>/
  FEATURE_BRIEF.md    ← Stage 1: what & why (single source of truth for the feature)
  DESIGN.md           ← Stage 2: how it works (architecture, data, contracts, UX)
  TASKS.md            ← Stage 3: ordered, independently verifiable work items
  TEST_PLAN.md        ← Stage 4: acceptance criteria → tests/checks mapping
  RELEASE_NOTES.md    ← Stage 5: user-facing change summary
  OPEN_QUESTIONS.md   ← all stages: ambiguities, deferrals, escalations
  DECISIONS.md        ← all stages: choice + rationale + rejected alternatives
```

### Patch Track Layout
```
features/patch-<patch-slug>/
  PATCH.md            ← Stage P-plan: consolidated brief, root-cause design, and tasks
  TEST_PLAN.md        ← Stage P-build: regression test verification
  RELEASE_NOTES.md    ← Stage P-build: summary of changes + rehearsed rollback
  OPEN_QUESTIONS.md   ← all stages: ambiguities, deferrals, escalations
  DECISIONS.md        ← all stages: choice + rationale + rejected alternatives
```

## Creating a new feature or patch (Coordinator step)

### Feature Track
1. Pick the slug with the user.
2. Create `features/<slug>/` and seed the seven files above (each may start as a heading + "_pending_" so the pipeline has somewhere to write).
3. Add the feature's row to [INDEX.md](INDEX.md) (stage + started date; outcome stays blank until Stage 6).
4. In [../CONTROL.md](../CONTROL.md): set the active feature, `Stage: 1-define`, and the folder path.
5. Hand off to the Product Analyst persona ([../process/personas/phase-1-product-analyst.md](../process/personas/phase-1-product-analyst.md)).

### Patch Track
1. Pick the slug with the user (must start with `patch-`).
2. Create `features/patch-<slug>/` and seed the five files listed in the Patch Track layout.
3. Add the patch's row to [INDEX.md](INDEX.md) (stage + started date; outcome stays blank until completed).
4. In [../CONTROL.md](../CONTROL.md): set the active feature/patch, `Stage: P-plan`, and the folder path.
5. Hand off to the Maintenance Planner persona ([../process/personas/patch-1-planner.md](../process/personas/patch-1-planner.md)).

Folders are never deleted on completion — a shipped feature's or patch's artifacts are the record of what was built and why. Mark its `Stage` as `done` in `CONTROL.md` instead.
