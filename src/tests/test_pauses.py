import numpy as np
import pandas as pd
import sys
from pathlib import Path
module_dir=next(parent for parent in Path(__file__).resolve().parents if (parent/'detect_pauses.py').is_file())
sys.path.insert(0,str(module_dir))
from detect_pauses import pair_pauses, detect_with_pauses, match_intervals

idx=pd.date_range('2026-01-01',periods=1500,freq='s',tz='UTC')
events=pd.DataFrame({'timestamp':[idx[0],idx[450],idx[510],idx[-1]],'event_type':['start','stop_all','start','stop_all']})
pauses,issues=pair_pauses(events)
assert not issues and pauses.duration_s.tolist()==[60]
speed=pd.Series(10.,index=idx); speed.iloc[300:750]=15.; speed.iloc[450:510]=np.nan
signal,intervals,fragments,decisions,_=detect_with_pauses(speed,pauses)
assert len(intervals)==1 and len(fragments)==2 and intervals.iloc[0].pause_s==60
assert not signal.loc[idx[450:510],'predicted'].any()
assert intervals.iloc[0].detected_s==390
# Le même trou sans événements reste une coupure.
assert len(detect_with_pauses(speed,pauses.iloc[:0])[1])==2
# Reprise lente : pas de fusion à travers la récupération.
slow=speed.copy(); slow.iloc[510:580]=10.
assert len(detect_with_pauses(slow,pauses)[1])==2
# Pause trop longue : les efforts restent séparés.
long_pauses=pauses.copy(); long_pauses.loc[0,'end_utc']=idx[700]; long_pauses.loc[0,'duration_s']=250
long_speed=pd.Series(10.,index=idx); long_speed.iloc[300:450]=15.; long_speed.iloc[450:700]=np.nan; long_speed.iloc[700:900]=15.
assert len(detect_with_pauses(long_speed,long_pauses)[1])==2
# Vitesses de reprise trop différentes : pas de fusion malgré la pause.
different=speed.copy(); different.iloc[510:750]=20.
assert len(detect_with_pauses(different,pauses)[1])==2
# Deux fragments <120 s peuvent ensemble dépasser le minimum après une pause.
short=pd.Series(10.,index=idx); short.iloc[400:450]=15.; short.iloc[450:510]=np.nan; short.iloc[510:600]=15.
assert len(detect_with_pauses(short,pauses)[1])==1
# Arrêt final : aucun intervalle de pause inventé.
assert pair_pauses(events.iloc[[0,3]])[0].empty
assert pair_pauses(events.iloc[[1,2]])[1]
assert pair_pauses(events.iloc[[0,0,3]])[1]
try: pair_pauses(events.iloc[::-1])
except ValueError: pass
else: raise AssertionError('Out-of-order timer events accepted')
ref=pd.DataFrame([dict(block=1,start_utc=idx[300],end_utc=idx[750])])
matched=match_intervals(signal,intervals,ref,~signal.paused.to_numpy() & signal.speed_kmh.notna().to_numpy())
assert len(matched)==1 and matched.iloc[0].iou==1 and matched.iloc[0].start_error_s==0
print('PASS: pause pairing, final stop, unknown gaps, slow recovery, short fragments, missing/invalid events, no prediction during pause, interval matching.')
