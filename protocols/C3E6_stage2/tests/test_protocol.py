import json, subprocess, sys, unittest, yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ProtocolValidationTest(unittest.TestCase):
 def test_protocol_validation_passes(self):
  p=subprocess.run([sys.executable,str(ROOT/'scripts'/'validate_protocol.py')],cwd=ROOT,capture_output=True,text=True)
  self.assertEqual(p.returncode,0,msg=p.stdout+'\n'+p.stderr)
  r=json.loads((ROOT/'reports'/'validation_report.json').read_text()); self.assertEqual(r['status'],'PASS'); self.assertEqual(r['checks_failed'],0)
 def test_training_remains_locked(self):
  e=yaml.safe_load((ROOT/'config'/'experiment_registry.yaml').read_text()); self.assertFalse(e['authorization']['model_training']); self.assertFalse(e['governance']['training_authorized'])
 def test_external_tuning_is_forbidden(self):
  e=yaml.safe_load((ROOT/'config'/'experiment_registry.yaml').read_text()); self.assertFalse(e['datasets']['external']['tuning_allowed'])
if __name__=='__main__': unittest.main()
