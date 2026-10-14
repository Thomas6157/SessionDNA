from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import json
import tempfile
import unittest
from training_week import validate_week
from import_training_week import import_week

def example():
    step=dict(type='work',duration_sec=60,distance_m=None,target_rpe=dict(min=2,max=3),instructions='Facile')
    session=dict(id='2026-09-28-running-01',date='2026-09-28',sport='running',title='Exemple',objective='Test',planned_duration_min=2,planned_distance_m=None,target_session_rpe=dict(min=2,max=3,scale='0-10'),blocks=[dict(name='Bloc',repeat=2,steps=[step])],scheduling=dict(fixed_date=True,preferred_time=None,allowed_dates=[],linked_session_id=None,constraints=[]))
    return dict(schema_version='sessiondna.training_week.v1',week_start='2026-09-28',timezone='Europe/Paris',sessions=[session])

class TrainingTests(unittest.TestCase):
    def test_repetition_count_and_immutability(self):
        data=example();before=copy.deepcopy(data);audit=validate_week(data)
        self.assertEqual(audit['errors'],[]);self.assertEqual(audit['sessions'][0]['explicit_duration_sec'],120);self.assertEqual(data,before)
    def test_duplicate_outside_week_and_dangling_link(self):
        data=example();data['sessions'].append(copy.deepcopy(data['sessions'][0]));data['sessions'][0]['date']='2026-10-05';data['sessions'][0]['scheduling']['linked_session_id']='missing'
        errors=' '.join(validate_week(data)['errors']);self.assertIn('dupliqués',errors);self.assertIn('hors de la semaine',errors);self.assertIn('liaison',errors)
    def test_invalid_numeric_targets(self):
        for target in [dict(min=8,max=3),dict(min=0,max=11),dict(min=float('nan'),max=4),dict(min=True,max=4)]:
            data=example();data['sessions'][0]['target_session_rpe']=target;self.assertTrue(validate_week(data)['errors'])
    def test_partial_duration_is_not_fake_total(self):
        data=example();data['sessions'][0]['blocks'][0]['steps'][0]['duration_sec']=None
        audit=validate_week(data);self.assertEqual(audit['errors'],[]);self.assertFalse(audit['sessions'][0]['all_durations_explicit']);self.assertTrue(audit['notes'])
    def test_import_idempotent_and_versions_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'plan.json';source.write_text(json.dumps(example()))
            first,created=import_week(source,root/'weeks');self.assertTrue(created)
            self.assertEqual((first/'source.json').read_bytes(),source.read_bytes())
            same,created=import_week(source,root/'weeks');self.assertFalse(created);self.assertEqual(same,first)
            data=example();data['sessions'][0]['title']='Révision';source.write_text(json.dumps(data))
            revised,created=import_week(source,root/'weeks');self.assertTrue(created);self.assertNotEqual(first,revised);self.assertTrue((first/'source.json').exists())
    def test_reject_invalid_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'plan.json';source.write_text('{}')
            with self.assertRaises(ValueError):import_week(source,root/'weeks')
            self.assertFalse((root/'weeks').exists())

if __name__=='__main__':unittest.main()
