"""Navegación del producto actual, sin pantallas ni pilotos retirados."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

from app.bootstrap import create_studio
from app.config import Settings


class WorkbenchTests(unittest.TestCase):
    def test_clean_global_view_and_three_channels(self):
        """Abre los tres canales sin datos antiguos ni dependencias de proveedores."""
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config').mkdir()
            (root/'config/canales.json').write_text(json.dumps({'channels':[{'id':code,'name':code,'category':'test','folder':code} for code in ('MIS','TEC','CIE')]}))
            studio=create_studio(Settings(root))
            with patch('app.workbench.create_studio',return_value=studio):
                app=AppTest.from_file('app/main.py').run()
                self.assertFalse(app.exception)
                self.assertTrue(any(b.key=='start_all_channels' for b in app.button))
                self.assertFalse(app.radio)
                for code in ('MIS','TEC','CIE'):
                    app.selectbox(key='phase1_context').set_value(code).run()
                    self.assertFalse(app.exception)
                    self.assertTrue(any(c.key=='auto_zip_'+code for c in app.checkbox))
                    self.assertFalse(any('históric' in s.value.lower() for s in app.subheader))
