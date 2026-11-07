"""Exercise the actual workflow patch, including nested Ok(()) in newer RustDesk."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '''pub fn check_software_update() {
    start_checker();
}
pub async fn do_check_software_update() -> Result<()> {
    let (request, url) = version_check_request();
    if request.is_empty() { return Ok(()); }
    send(request, url).await
}
pub fn unrelated() { key_exchange(); }
'''
GUARD = '\n    // Custom releases are managed by the Smartia agent.\n    if !is_rustdesk() { return; }'


class UpdateGuardTest(unittest.TestCase):
    def test_actual_workflows_preserve_new_upstream_body(self):
        for workflow in ('generator-windows.yml', 'generator-macos.yml'):
            data = yaml.safe_load((ROOT / '.github/workflows' / workflow).read_text())
            step = next(step for job in data['jobs'].values() for step in job.get('steps', [])
                        if step.get('name') == 'Guard custom-client upstream update checks')
            for source in (SOURCE, SOURCE.replace('pub fn check_software_update()', 'pub fn changed()'), SOURCE + SOURCE):
                original_dir = Path.cwd()
                with tempfile.TemporaryDirectory() as temp:
                    try:
                        os.chdir(temp)
                        Path('src').mkdir()
                        Path('src/common.rs').write_text(source)
                        page = Path('flutter/lib/desktop/pages/desktop_home_page.dart')
                        page.parent.mkdir(parents=True)
                        page.write_text('updateUrl.isNotEmpty')
                        with patch('subprocess.run') as parser:
                            if source.count('pub fn check_software_update() {') != 1:
                                with self.assertRaises(ValueError):
                                    exec(compile(step['run'], '<workflow>', 'exec'), {})
                                self.assertEqual(Path('src/common.rs').read_text(), source)
                                parser.assert_not_called()
                            else:
                                exec(compile(step['run'], '<workflow>', 'exec'), {})
                                self.assertEqual(Path('src/common.rs').read_text().replace(GUARD, '', 1), source)
                                self.assertEqual(page.read_text(), 'false')
                                parser.assert_called_once()
                    finally:
                        os.chdir(original_dir)


if __name__ == '__main__':
    unittest.main()
