import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import yaml
ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=yaml.safe_load((ROOT/'.github/workflows/generator-macos.yml').read_text())
STEP=next(s for s in WORKFLOW['jobs']['build-for-macos']['steps'] if s.get('name')=='Apply macOS product window title')
class MacTitleTest(unittest.TestCase):
    def run_step(self,xml):
        old=Path.cwd(); previous=os.environ.get('SMARTIA_PRODUCT_DISPLAY_NAME')
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp); os.environ['SMARTIA_PRODUCT_DISPLAY_NAME']='smartia.RDP'
                path=Path('flutter/macos/Runner/Base.lproj/MainMenu.xib');path.parent.mkdir(parents=True);path.write_text(xml)
                exec(compile(STEP['run'],'<actual Mac window title step>','exec'),{})
                return ET.parse(path).getroot()
            finally:
                os.chdir(old)
                if previous is None:os.environ.pop('SMARTIA_PRODUCT_DISPLAY_NAME',None)
                else:os.environ['SMARTIA_PRODUCT_DISPLAY_NAME']=previous
    def test_display_change_preserves_native_module_and_identity(self):
        tree=self.run_step('<document><window title="RustDesk" id="main" customClass="MainFlutterWindow" customModule="RustDesk"/><object bundle="al.smartia.support"/></document>')
        window=tree.find('window');self.assertEqual(window.attrib,{'title':'smartia.RDP','id':'main','customClass':'MainFlutterWindow','customModule':'RustDesk'})
        self.assertEqual(tree.find('object').get('bundle'),'al.smartia.support')
    def test_unknown_upstream_structure_is_rejected(self):
        for xml in ['<document/>','<document><window title="RustDesk"/><window title="RustDesk"/></document>']:
            with self.assertRaises(ValueError):self.run_step(xml)
if __name__=='__main__':unittest.main()
