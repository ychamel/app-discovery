# patches/

Each patch that goes through the **Patch Track** (Maintenance Pipeline) gets **one
folder** here, named with a `patch-` + kebab-case slug (e.g. `patch-try-app-redirect/`,
`patch-profile-form-actions/`).

Patches are bug fixes, refactors, test optimizations, dependency bumps, and technical
chores. They live here, **separate from [../features/](../features/)**, so feature
tracking stays uncongested. A patch **must not** introduce or modify database schemas
(no migrations), change or add public API endpoints, or modify global ADRs — if any of
those are required, the work runs on the standard **Feature Track** instead (see the
scope gate in [../CLAUDE.md](../CLAUDE.md) §2).

[INDEX.md](INDEX.md) in this directory is the registry of **every** patch and its
outcome — the answer to "have we already patched X?".

## Standard layout

```
patches/patch-<slug>/
  PATCH.md            ← Stage P-plan: consolidated brief, root-cause design, and tasks
  TEST_PLAN.md        ← Stage P-build: regression test verification
  RELEASE_NOTES.md    ← Stage P-build: summary of changes + rehearsed rollback
  OPEN_QUESTIONS.md   ← all stages: ambiguities, deferrals, escalations
  DECISIONS.md        ← all stages: choice + rationale + rejected alternatives
```

## Creating a new patch (Coordinator step)

1. Pick the slug with the user (must start with `patch-`).
2. Create `patches/patch-<slug>/` and seed the five files listed above (each may start as
   a heading + "_pending_" so the pipeline has somewhere to write).
3. Add the patch's row to [INDEX.md](INDEX.md) (stage + started date; outcome stays blank
   until close-out).
4. In [../CONTROL.md](../CONTROL.md): set the active patch, `Stage: P-plan`, and the
   folder path.
5. Hand off to the Maintenance Planner persona ([../process/personas/patch-1-planner.md](../process/personas/patch-1-planner.md)).

Folders are never deleted on completion — a shipped patch's artifacts are the record of
what was fixed and why. Mark its `Stage` as `closed-out` in `CONTROL.md` instead.
