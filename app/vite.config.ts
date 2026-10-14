import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import {readFileSync,writeFileSync,readdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
export default defineConfig({resolve:{preserveSymlinks:true},plugins:[react(),{name:'sessiondna-offline-shell',closeBundle(){const directory=resolve('dist');const html=readFileSync(resolve(directory,'index.html'),'utf-8');const hash=createHash('sha256').update(html).digest('hex').slice(0,12);const assets=readdirSync(resolve(directory,'assets')).filter(name=>/\.(js|css)$/.test(name)).map(name=>'/assets/'+name);const sw=readFileSync(resolve(directory,'sw.js'),'utf-8').replace('__BUILD_ID__',hash).replace('/*PRECACHE_ASSETS*/',assets.map(s=>JSON.stringify(s)).join(','));writeFileSync(resolve(directory,'sw.js'),sw);}}],server:{host:'127.0.0.1',proxy:{'/api':'http://127.0.0.1:8765'}},build:{chunkSizeWarningLimit:1500,rollupOptions:{output:{manualChunks:{react:['react','react-dom'],charts:['echarts'],maps:['maplibre-gl']}}}}});
