import {describe,it,expect} from 'vitest';
import {BASE,CACHE,Conflict,equal,merge,persist,rawBackup,readBase,readState,validateItems} from '../src/lib/state-core';
class MemoryStorage implements Storage{data=new Map<string,string>();get length(){return this.data.size;}key(i:number){return [...this.data.keys()][i]??null;}getItem(k:string){return this.data.get(k)??null;}setItem(k:string,v:string){this.data.set(k,String(v));}removeItem(k:string){this.data.delete(k);}clear(){this.data.clear();}}
const key='sessiondna-feedback-v1-test';
describe('durable feedback and migration',()=>{
 it('imports legacy feedback without deleting unrelated browser keys',()=>{const s=new MemoryStorage();s.setItem(key,JSON.stringify({a:{rpe:4}}));s.setItem('elsewhere','keep');expect(readState(s)).toEqual({[key]:{a:{rpe:4}}});persist(s,readState(s));expect(s.getItem('elsewhere')).toBe('keep');});
 it('removes deleted sections from compatibility keys and from the next reload',()=>{const s=new MemoryStorage();persist(s,{[key]:{a:1}});persist(s,{});expect(s.getItem(key)).toBeNull();expect(readState(s)).toEqual({});});
 it('preserves the new snapshot when a compatibility write exceeds quota',()=>{const s=new MemoryStorage();s.setItem(key,'{"a":1}');s.setItem=function(k,v){if(k!==CACHE)throw Error('quota');this.data.set(k,String(v));};persist(s,{[key]:{a:2}});expect(readState(s)).toEqual({[key]:{a:2}});});
 it('does not remove old data when the durable snapshot cannot be saved',()=>{const s=new MemoryStorage();s.setItem(key,'{"a":1}');s.setItem=()=>{throw Error('quota');};expect(()=>persist(s,{})).toThrow('quota');expect(s.getItem(key)).toBe('{"a":1}');});
 it('surfaces corrupted local JSON and keeps the exact raw text for recovery',()=>{const s=new MemoryStorage();s.setItem(key,'{broken');expect(()=>readState(s)).toThrow();expect(rawBackup(s)[key]).toBe('{broken');});
 it('refuses an unreadable merge base instead of accepting a reset',()=>{const s=new MemoryStorage();s.setItem(BASE,'{broken');expect(()=>readBase(s)).toThrow();expect(s.getItem(BASE)).toBe('{broken');});
 it('rejects a restore containing unsupported keys',()=>{expect(()=>validateItems({token:{secret:'x'}})).toThrow();expect(()=>validateItems({[key]:[]})).toThrow();});
});
describe('three-way merge and explicit conflicts',()=>{
 it('merges edits to different sessions on separate devices',()=>{const base={a:{rpe:4},b:{rpe:3}},local={a:{rpe:5},b:{rpe:3}},remote={a:{rpe:4},b:{rpe:7}};expect(merge(base,local,remote)).toEqual({a:{rpe:5},b:{rpe:7}});});
 it('surfaces a conflict on the same field',()=>{expect(()=>merge({a:{rpe:4}},{a:{rpe:5}},{a:{rpe:6}})).toThrow(Conflict);});
 it('preferring local changes only conflicting fields and preserves unrelated server edits',()=>{expect(merge({a:1,b:1},{a:2,b:1},{a:3,b:4},'','local')).toEqual({a:2,b:4});});
 it('preferring remote changes only conflicting fields and preserves unrelated local edits',()=>{expect(merge({a:1,b:1},{a:2,b:4},{a:3,b:1},'','remote')).toEqual({a:3,b:4});});
 it('preserves a deletion when the other device has not changed it',()=>{expect(merge({a:1,b:2},{b:2},{a:1,b:2})).toEqual({b:2});});
 it('does not silently delete a concurrently edited entry',()=>{expect(()=>merge({a:1},{},{a:2})).toThrow(Conflict);});
 it('handles typing while a server POST is in flight without losing server fields',()=>{const sent={a:{notes:'A'},b:1},typed={a:{notes:'B'},b:1},server={a:{notes:'A'},b:2};expect(merge(sent,typed,server)).toEqual({a:{notes:'B'},b:2});});
 it('ignores object key order so unchanged server responses do not trigger another sync',()=>{expect(equal({a:1,b:2},{b:2,a:1})).toBe(true);});
});
