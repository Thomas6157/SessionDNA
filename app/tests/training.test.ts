import {describe,it,expect} from 'vitest';
import {isLinked,planningTimes,questionAnswers,questionValues,stepDuration} from '../src/lib/training';
import type {Planning,Session,TrainingWeek} from '../src/types';
describe('training provenance and legacy feedback',()=>{
 it('does not reuse hours from another version of the same week',()=>{
  const planning={weeks:{original:{run:'10:00'},replacement:{run:'16:00'}}} as unknown as Planning;
  const week={plan:{week_start:'2026-09-28'},manifest:{source_sha256:'original'}} as TrainingWeek;
  expect(planningTimes(planning,week)).toEqual({run:'10:00'});
  expect(planningTimes(planning,{...week,manifest:{source_sha256:'new'}})).toEqual({});
 });
 it('requires manual review of both members of a linked pair',()=>{
  const bike={id:'bike',scheduling:{}} as Session;
  const run={id:'run',scheduling:{linked_session_id:'bike'}} as Session;
  expect(isLinked(bike,[bike,run])).toBe(true);
  expect(isLinked(run,[bike,run])).toBe(true);
  expect(isLinked({id:'swim',scheduling:{}} as Session,[bike,run])).toBe(false);
 });
 it('displays short recovery durations without rounding to minutes',()=>{
  expect(stepDuration(20)).toBe('20 s');expect(stepDuration(90)).toBe('1 min 30 s');expect(stepDuration(900)).toBe('15 min');
 });
 it('preserves old answers indexed by the full question',()=>{
  const questions=['Sensations ?','Récupération. Comment ?'];
  const previous={'Sensations ?':'Bien','Récupération. Comment ?':'Correcte',extra:'À conserver'};
  expect(questionValues(questions,previous)).toEqual(['Bien','Correcte']);
  expect(questionAnswers(questions,['Mieux','Correcte'],previous)).toEqual({...previous,'Sensations ?':'Mieux'});
 });
 it('converts the temporary q0 convention to meaningful report labels',()=>{
  expect(questionValues(['Sensations ?'],{q0:'Bien'})).toEqual(['Bien']);
  expect(questionAnswers(['Sensations ?'],['Bien'],{q0:'Bien'})).toEqual({'Sensations ?':'Bien'});
 });
});
