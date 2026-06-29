# Release Notes: Interest Picker Duplicate Subcategories

## Summary
Resolved a user-experience issue where clicking on a tag label on the interest picker page (`/interests/`) toggled the checkbox of the first occurrence of that tag on the page, even if the user clicked a subsequent occurrence under a different cluster.

This was caused by duplicate HTML `id` values generated for the same tag when it belonged to multiple clusters.

## Changes
- **Template Update**: Modified `apps/interests/templates/interests/picker.html` to generate unique HTML `id` and label `for` attributes by prefixing the tag ID with the cluster ID (e.g., `tag_{cluster_id}_{tag_id}`).
- **Sync JS**: Added a lightweight vanilla JavaScript listener in the template that automatically keeps duplicate tag checkboxes in visual synchronization. Clicking or checking one instance of a tag now updates all instances of that tag on the page.

## Rollback Procedure (DU-REL-1)
This patch is fully backward-compatible and requires no database migrations.
To rollback this patch:
1. Revert the commit containing the changes, or run:
   ```bash
   git checkout HEAD~1 -- apps/interests/templates/interests/picker.html apps/interests/tests/test_views.py
   ```
2. Verify rollback by running the test suite to ensure the system is stable:
   ```bash
   .venv/bin/python manage.py test
   ```
