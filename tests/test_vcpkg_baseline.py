"""Exercise the actual workflow step without GitHub or a Windows runner."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / '.github/workflows/generator-windows.yml').read_text())
STEP = next(step for job in WORKFLOW['jobs'].values() for step in job.get('steps', [])
            if step.get('name') == 'Select vcpkg baseline from RustDesk release manifest')


class BaselineTest(unittest.TestCase):
    def test_macos_uses_same_release_manifest_step(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/generator-macos.yml').read_text())
        steps = workflow['jobs']['build-for-macos']['steps']
        selected = next(i for i, step in enumerate(steps) if step.get('name') == STEP['name'])
        setup = next(i for i, step in enumerate(steps) if step.get('name') == 'Setup vcpkg with Github Actions binary cache')
        self.assertLess(selected, setup)
        self.assertEqual(steps[selected]['run'], STEP['run'])

    def run_step(self, baseline):
        old_dir = Path.cwd()
        old_env = os.environ.get('GITHUB_ENV')
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                os.environ['GITHUB_ENV'] = str(Path(tmp) / 'environment')
                Path('vcpkg.json').write_text(json.dumps({'vcpkg-configuration': {'default-registry': {'baseline': baseline}}}))
                exec(compile(STEP['run'], '<workflow baseline step>', 'exec'), {})
                return Path('environment').read_text()
            finally:
                os.chdir(old_dir)
                if old_env is None:
                    os.environ.pop('GITHUB_ENV', None)
                else:
                    os.environ['GITHUB_ENV'] = old_env

    def test_release_pins(self):
        for pin in ('120deac3062162151622ca4860575a33844ba10b', '9e593bb18ea69cc5095e012465dcd675a822ed0d'):
            self.assertEqual(self.run_step(pin), f'VCPKG_COMMIT_ID={pin}\n')

    def test_reject_unpinned_or_injected_input(self):
        for pin in ('', None, 'master', 'a' * 40 + '\nOTHER=value'):
            with self.assertRaises(ValueError):
                self.run_step(pin)


if __name__ == '__main__':
    unittest.main()
