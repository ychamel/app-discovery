# Test Plan: Interest Picker Duplicate Subcategories

This patch ensures that when a tag is assigned to multiple active clusters in the taxonomy, it has unique HTML IDs and labels on the interest picker page, and that clicking one visually synchronizes all checkboxes for that tag across all clusters.

## 1. Automated Regression Test
- **Test Case**: `test_duplicate_tags_have_unique_html_ids_and_matching_labels`
- **Location**: `apps/interests/tests/test_views.py`
- **Verification Details**:
  - Sets up a test scenario with a single tag ("python") assigned to two distinct clusters ("python-cluster-1" and "python-cluster-2").
  - Invokes `GET /interests/` (the interest picker view).
  - Asserts that both checkbox elements have unique ID attributes of the form `tag_{cluster_id}_{tag_id}`.
  - Asserts that each checkbox has a corresponding `<label>` tag with a matching `for` attribute pointing to that specific unique ID.
- **Execution Command**:
  ```bash
  .venv/bin/python manage.py test apps.interests.tests.test_views.PickerRenderTests.test_duplicate_tags_have_unique_html_ids_and_matching_labels
  ```

## 2. Client-side Synchronization Verification
- **Functional Description**: The vanilla JavaScript block embedded at the bottom of the `picker.html` template listens for change events on checkboxes with `name="tag_id"`.
- **Manual Verification Steps**:
  1. Navigate to `/interests/` with a user account.
  2. Locate any tag that appears under multiple clusters.
  3. Click on the text label for one instance of the tag in the second cluster.
  4. Verify that the checkbox for that instance is checked, and that the checkbox for the instance under the first cluster is also checked synchronously.
  5. Uncheck the tag in either cluster and verify both instances are unchecked.
