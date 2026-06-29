# Patch: Interest Picker Duplicate Subcategories

## 1. Problem Statement

### Reproduction Steps
1. Log in and navigate to the interest picker page `/interests/`.
2. Ensure there is a tag associated with multiple active clusters (e.g., tag "Python" in both the "Backend Development" and "Data Science" clusters).
3. Find the tag in the second cluster on the page.
4. Hover over and click on the text label for the tag in that second cluster.
5. Observe that the checkbox under the *first* cluster is checked/unchecked instead of the checkbox in the second cluster where the click occurred.

### Root Cause Analysis
In `apps/interests/templates/interests/picker.html` (lines 62-64):
```html
                      <input type="checkbox" name="tag_id" id="tag_{{ item.tag.id }}" value="{{ item.tag.id }}"
                             {% if item.checked %}checked{% endif %} style="width: auto; margin-top: 0.25rem;">
                      <label for="tag_{{ item.tag.id }}" ...>
```
The checkbox `id` and the label `for` attribute are generated using only `tag_{{ item.tag.id }}`. When a tag is associated with multiple active clusters (which is allowed under our taxonomy model), it is rendered multiple times on the interest picker page. As a result, multiple input elements share the same duplicate HTML `id`.

According to HTML specifications, clicking a `<label>` associated with an `id` via the `for` attribute toggles the *first* element in the DOM with that ID. Consequently, clicking the label of a duplicate tag under a subsequent cluster toggles the checkbox under the first cluster, causing visual confusion and incorrect state changes.

## 2. Proposed Fix / Change

### Code-level Design
1. **Unique HTML IDs in template**:
   Update `apps/interests/templates/interests/picker.html` to generate unique HTML `id` values by combining the cluster ID and tag ID.
   - For checkbox: `id="tag_{{ row.cluster.id }}_{{ item.tag.id }}"`
   - For label: `for="tag_{{ row.cluster.id }}_{{ item.tag.id }}"`
   Since cluster IDs are UUIDs, this makes each checkbox/label pair uniquely associated on the page.

2. **Cross-Cluster Visual-Sync Progress Enhancement JS**:
   Per the `DN-Q001-TAXONOMY` resolution, duplicate tags should sync visually when checked/unchecked on the same page before submission.
   We can add a simple client-side vanilla JavaScript snippet inside a `<script>` tag at the bottom of `picker.html` that listens for changes on checkboxes with `name="tag_id"`. When a checkbox value changes, it finds all checkboxes with the same `value` attribute and matches their `checked` state.

   Example:
   ```javascript
   document.addEventListener('DOMContentLoaded', function() {
     const checkboxes = document.querySelectorAll('input[name="tag_id"]');
     checkboxes.forEach(cb => {
       cb.addEventListener('change', function() {
         const val = this.value;
         const isChecked = this.checked;
         document.querySelectorAll(`input[name="tag_id"][value="${val}"]`).forEach(other => {
           other.checked = isChecked;
         });
       });
     });
   });
   ```

### No-Schema Assertion
*This patch contains no schema changes, new public API endpoints, or global ADR updates.*

## 3. Task List

### `T-01`: Write the regression test (Red First)
- **Description**: Add a new test case in `apps/interests/tests/test_views.py` that sets up a tag in two clusters, fetches the interests picker, and asserts that the response contains unique IDs matching the pattern `tag_{cluster_id}_{tag_id}` and that labels point to these unique IDs. The test must fail when run against the current template.
- **Files Touched**: `apps/interests/tests/test_views.py`
- **Definition of Done**: A test case is added, run, and fails with output showing non-unique HTML IDs or missing unique patterns.

### `T-02`: Implement unique HTML IDs
- **Description**: Update the input `id` and label `for` attributes in `picker.html` to include the cluster ID.
- **Files Touched**: `apps/interests/templates/interests/picker.html`
- **Definition of Done**: The template uses unique IDs, and `T-01` passes.

### `T-03`: Implement client-side cross-cluster synchronization
- **Description**: Add vanilla JS to `picker.html` to synchronize checkbox states for identical tag values across clusters.
- **Files Touched**: `apps/interests/templates/interests/picker.html`
- **Definition of Done**: JS snippet is present in the template, and verified to function in the browser when duplicate tags are checked.

### `T-04`: Verify test suite and clean up
- **Description**: Run the entire Django test suite to ensure all tests pass (including the new regression test and all existing 997 tests), and verify the code with `ruff` and `check`.
- **Files Touched**: None
- **Definition of Done**: Python command `.venv/bin/python manage.py test` passes completely, and `ruff check` runs without errors.
