from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class StaticAssetTests(SimpleTestCase):
    def test_application_static_assets_are_discoverable(self):
        self.assertIsNotNone(finders.find('work/app.css'))
        self.assertIsNotNone(finders.find('work/app.js'))

    def test_stylesheet_contains_current_design_rules(self):
        path=finders.find('work/app.css')
        with open(path,'r',encoding='utf-8') as stylesheet:
            css=stylesheet.read()
        self.assertIn('--surface',css)
        self.assertIn('.map-filters',css)
        self.assertIn('.board-dropzone',css)
