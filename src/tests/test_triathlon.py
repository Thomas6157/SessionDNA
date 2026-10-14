"""Vérifications des frontières temporelles et des métriques piscine."""
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from analyze_triathlon import link_bricks,summarize,SESSION_FIELDS,RECORD_FIELDS,LENGTH_FIELDS

class TriathlonTests(unittest.TestCase):
    def test_brick_boundaries_and_bad_quality(self):
        bike=dict(id='b',filename='b.fit',sport='cycling',status='ok',end_utc='2026-09-01T10:00:00Z',timer_min=60,power_session_mean=180)
        def run(minutes,status='ok'):
            return dict(id='r',filename='r.fit',sport='running',status=status,start_utc=(pd.Timestamp(bike['end_utc'])+pd.Timedelta(minutes=minutes)).isoformat())
        for gap,expected in [(-1,0),(0,1),(30,1),(30.01,0)]:
            self.assertEqual(len(link_bricks([bike,run(gap)])),expected)
        self.assertEqual(link_bricks([bike,run(5,'review')]),[])
        self.assertEqual(link_bricks([{**bike,'status':'review'},run(5)]),[])
    def test_pool_rest_excluded_and_distance_units(self):
        session=dict.fromkeys(SESSION_FIELDS)
        session.update(sport='swimming',start_time='2026-09-01T10:00:00Z',total_elapsed_time=90,total_timer_time=90,total_distance=50,pool_length=25)
        lengths=pd.DataFrame([
            dict(start_time='2026-09-01T10:00:00Z',length_type='active',total_timer_time=25,total_strokes=12),
            dict(start_time='2026-09-01T10:00:25Z',length_type='idle',total_timer_time=30),
            dict(start_time='2026-09-01T10:00:55Z',length_type='active',total_timer_time=35,total_strokes=14)],columns=LENGTH_FIELDS)
        with patch('analyze_triathlon.read_fit',return_value=([session],pd.DataFrame(columns=RECORD_FIELDS),lengths,[],0)):
            rows,_,_=summarize(Path('pool.fit'))
        r=rows[0]
        self.assertEqual(r['length_distance_m'],50)
        self.assertEqual(r['length_active_time_s'],60)
        self.assertEqual(r['pace_active_100m_s'],120)
        self.assertEqual(r['rest_lengths'],1)
        self.assertEqual(r['issues'],[])
    def test_multisession_boundary_record_not_duplicated(self):
        sessions=[]
        for sport,start in [('cycling','2026-09-01T10:00:00Z'),('running','2026-09-01T10:01:00Z')]:
            s=dict.fromkeys(SESSION_FIELDS);s.update(sport=sport,start_time=start,total_elapsed_time=60,total_timer_time=60);sessions.append(s)
        records=pd.DataFrame([dict(timestamp='2026-09-01T10:00:00Z'),dict(timestamp='2026-09-01T10:01:00Z'),dict(timestamp='2026-09-01T10:02:00Z')],columns=RECORD_FIELDS)
        with patch('analyze_triathlon.read_fit',return_value=(sessions,records,pd.DataFrame(columns=LENGTH_FIELDS),[],0)):
            rows,_,_=summarize(Path('multi.fit'))
        self.assertEqual([r['n_records'] for r in rows],[1,2])

if __name__=='__main__':unittest.main()
