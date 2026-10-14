const assert=require('node:assert/strict');
const {merge}=require('../triathlon_web/sync.js');
assert.deepEqual(merge({}, {}, {a:{value:1}}),{a:{value:1}});
assert.deepEqual(merge({}, {a:{value:1}}, {}),{a:{value:1}});
assert.deepEqual(merge({a:1,b:1},{a:2,b:1},{a:1,b:2}),{a:2,b:2});
assert.throws(()=>merge({a:1},{a:2},{a:3}),/Deux versions/);
assert.deepEqual(merge({a:1,b:1},{b:1},{a:1,b:2}),{b:2});
assert.deepEqual(merge({a:1},{a:2},{a:2}),{a:2});
console.log('Synchronisation : fusion, nouvel appareil, suppression et conflit vérifiés.');
