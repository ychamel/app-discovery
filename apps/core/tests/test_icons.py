from django.template import Template, Context, TemplateDoesNotExist
from django.test import SimpleTestCase


class IconTemplateTagTests(SimpleTestCase):
    """
    Verify the icon template tag renders SVGs correctly and fails loud for missing icons.
    """

    def test_render_known_icon(self):
        """Known icon renders SVG template containing inline classes/attributes."""
        template = Template("{% load icons %}{% icon 'search' %}")
        rendered = template.render(Context({}))
        self.assertIn('<svg class="icon"', rendered)
        self.assertIn("viewBox", rendered)
        self.assertIn("</svg>", rendered)

    def test_render_unknown_icon_raises_error(self):
        """Unknown icon raises TemplateDoesNotExist in Django rendering."""
        template = Template("{% load icons %}{% icon 'non_existent_icon_xyz' %}")
        with self.assertRaises(TemplateDoesNotExist):
            template.render(Context({}))
