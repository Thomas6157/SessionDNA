import {describe,it,expect} from 'vitest';
import {conflicts,courses,validate} from '../src/lib/planner';
import {duration,monday,weekDates} from '../src/lib/format';
import type {PlanningSettings,Pool,Session} from '../src/types';
const settings:PlanningSettings={wake:'07:00',bed:'22:00',commute:30,before:15,after:15,swimExtra:15};
const s:Session={id:'run',date:'2026-10-01',sport:'running',title:'Footing',objective:'EF',planned_duration_min:60,blocks:[],scheduling:{}};
describe('planning across real-world constraints',()=>{
 it('does not substitute zero for unknown commute',()=>{expect(validate({...settings,commute:''})).toBe(false);expect(validate({...settings,commute:0})).toBe(true);});
 it('blocks a course including transport and preparation margins',()=>{const events=[{title:'AI',start:'2026-10-01T10:00:00+02:00',end:'2026-10-01T12:00:00+02:00'}];expect(conflicts(s,'08:45',settings,events,[s],{})).toContain('Cours / trajet : AI');expect(conflicts(s,'07:30',settings,events,[s],{})).toEqual([]);});
 it('blocks overlap with another training session',()=>{expect(conflicts(s,'18:00',settings,[],[s,{...s,id:'bike',title:'Vélo'}],{bike:'18:45'})).toContain('Autre séance : Vélo');});
 it('preserves the sleep boundary',()=>{expect(conflicts(s,'21:00',settings,[],[s],{})).toContain('Sommeil / limites de journée');});
 it('refuses to schedule an unknown duration',()=>{expect(conflicts({...s,planned_duration_min:null},'15:00',settings,[],[s],{})).toContain('Horaire ou durée invalide');});
 it('does not silently reuse stale swimming pool hours',()=>{const pool:Pool={name:'Pool',source:'',checked:'2026-09-29',valid_from:'2026-09-28',valid_until:'2026-10-04',changing_min:15,evacuation_min:30,hours:{4:['07:00','21:00']}};expect(conflicts({...s,date:'2026-10-08',sport:'swimming'},'15:00',settings,[],[],{},pool)).toContain('Horaires piscine à revérifier pour cette date');expect(conflicts({...s,sport:'swimming'},'20:00',settings,[],[],{},pool)).toContain('Piscine : ouverture, vestiaire ou évacuation');});
 it('clips cross-day calendar events in Paris civil time',()=>{expect(courses([{title:'Cours',start:'2026-09-30T23:00:00+02:00',end:'2026-10-01T08:30:00+02:00'}],'2026-10-01')[0]).toMatchObject({start:0,end:510});});
});
describe('dates and duration',()=>{
 it('rounds over minute 59 without displaying 1 h 60',()=>{expect(duration(119.8)).toBe('2 h');});
 it('keeps unknown data distinct from zero',()=>{expect(duration(null)).toBe('Durée inconnue');expect(duration(0)).toBe('0 min');});
 it('handles the DST week with seven distinct dates',()=>{expect(monday('2026-10-25')).toBe('2026-10-19');expect(weekDates('2026-10-19')).toHaveLength(7);expect(weekDates('2026-10-19')[6]).toBe('2026-10-25');});
});
