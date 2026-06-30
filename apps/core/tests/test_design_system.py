import os
import re
from django.conf import settings
from django.test import SimpleTestCase


class DesignSystemEnumerationTests(SimpleTestCase):
    """
    Enumeration guard test for the design system (T-02, DESIGN.md §3.4).
    Ensures that all referenced CSS tokens and component classes are defined in app.css.
    """

    def setUp(self):
        self.base_dir = settings.BASE_DIR
        self.css_path = os.path.join(self.base_dir, "apps", "core", "static", "core", "app.css")
        self.apps_dir = os.path.join(self.base_dir, "apps")

    def test_design_system_definitions(self):
        """
        Verify that T-01 regression anchors are defined in app.css.
        """
        with open(self.css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        css_no_comments = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)
        defined_tokens = set(re.findall(r"(--[a-zA-Z0-9_.-]+)\s*:", css_no_comments))

        defined_classes = set()
        for block in css_no_comments.split("}"):
            if "{" in block:
                selector = block.split("{")[0].strip()
                for cls in re.findall(r"\.([a-zA-Z][a-zA-Z0-9_-]*)", selector):
                    defined_classes.add(cls)

        # Assert T-01 tokens are defined
        required_tokens = {
            "--font-size-md",
            "--font-size-4xl",
            "--space-0.5",
            "--space-1.5",
            "--space-2.5",
            "--space-3.5",
        }
        for token in required_tokens:
            self.assertIn(token, defined_tokens, f"Token {token} is not defined in app.css")

        # Assert btn--sm is defined
        self.assertIn("btn--sm", defined_classes, "Class btn--sm is not defined in app.css")

    def test_design_system_tokens_alignment(self):
        """
        Verify that all referenced CSS custom properties are defined in app.css.
        """
        with open(self.css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        css_no_comments = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)
        defined_tokens = set(re.findall(r"(--[a-zA-Z0-9_.-]+)\s*:", css_no_comments))

        # Find referenced tokens in CSS: var(--token-name)
        referenced_tokens = set(re.findall(r"var\((--[a-zA-Z0-9_.-]+)\)", css_no_comments))

        # Find referenced tokens in non-widget templates
        for root, dirs, files in os.walk(self.apps_dir):
            if "widget/templates/widget" in root:
                continue
            for file in files:
                if file.endswith(".html"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        template_content = f.read()
                    
                    tokens_in_template = re.findall(r"var\((--[a-zA-Z0-9_.-]+)\)", template_content)
                    referenced_tokens.update(tokens_in_template)

        # Assert referenced ⊆ defined
        undefined_referenced_tokens = referenced_tokens - defined_tokens
        self.assertEqual(
            undefined_referenced_tokens,
            set(),
            f"Referenced CSS tokens are not defined in app.css: {undefined_referenced_tokens}"
        )

    def test_design_system_classes_alignment(self):
        """
        Verify that all referenced component classes are defined in app.css.
        """
        with open(self.css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        css_no_comments = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)
        
        defined_classes = set()
        for block in css_no_comments.split("}"):
            if "{" in block:
                selector = block.split("{")[0].strip()
                for cls in re.findall(r"\.([a-zA-Z][a-zA-Z0-9_-]*)", selector):
                    defined_classes.add(cls)

        referenced_classes = set()

        # Component class prefixes/exact names we want to enforce
        component_prefixes = (
            "btn--", "badge--", "legend-swatch--", "media--", "empty-state__", "hero__",
            "app-card__", "devlog__", "facet__", "form-field__"
        )
        component_exact = {
            "btn", "card", "badge", "empty-state", "hero", "app-grid", "app-page",
            "site-header", "site-nav", "site-brand", "site-nav-links", "site-nav-signout",
            "site-main", "site-footer", "messages", "message", "table-wrap", "skip-link",
            "visually-hidden", "fact-strip", "facet", "tab", "toolbar",
            "text-muted", "text-error", "text-success", "text-accent", "text-sm", "text-xs",
            "page-header", "m-0", "full-width", "icon",
            "font-semibold", "font-bold", "font-normal",
            "form-field", "form-section", "form-section-title", "required-indicator",
            "data-row", "muted-caption", "checkbox-label", "profile-details", "stat-value",
            "card-heading", "card-heading--divided", "metric-value", "metric-label",
        }
        
        ignored_semantic_classes = {
            "hero__tagline",
            "devlog",
            "devlog__empty",
            "app-page-reviews"  # Will be defined in W4/T-07
        }

        def is_component_class(cls):
            if cls in ignored_semantic_classes:
                return False
            if cls in component_exact:
                return True
            for prefix in component_prefixes:
                if cls.startswith(prefix):
                    return True
            return False

        # Gather class references from non-widget templates
        for root, dirs, files in os.walk(self.apps_dir):
            if "widget/templates/widget" in root:
                continue
            for file in files:
                if file.endswith(".html"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    class_matches = re.findall(r'class=["\']([^"\']+)["\']', content)
                    for match in class_matches:
                        for cls in match.split():
                            if "{" in cls or "}" in cls or "%" in cls or "|" in cls or "=" in cls:
                                continue
                            if is_component_class(cls):
                                referenced_classes.add(cls)

        # Assert referenced ⊆ defined
        undefined_referenced_classes = referenced_classes - defined_classes
        self.assertEqual(
            undefined_referenced_classes,
            set(),
            f"Referenced component classes are not defined in app.css: {undefined_referenced_classes}"
        )

    def test_inline_styles_count(self):
        """
        Verify that the number of inline style attributes in non-widget templates
        is at or below the M2 ceiling of 400.
        """
        style_count = 0
        for root, dirs, files in os.walk(self.apps_dir):
            if "widget/templates/widget" in root:
                continue
            for file in files:
                if file.endswith(".html"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    matches = re.findall(r'\sstyle=["\']([^"\']*)["\']', content)
                    style_count += len(matches)

        print(f"\n[M2 Floor check] Total inline style= attributes found: {style_count}")
        self.assertLessEqual(style_count, 400, f"Too many inline style attributes: {style_count} (must be <= 400)")
