import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {LineChart,BarChart} from 'echarts/charts';
import {GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,MarkAreaComponent} from 'echarts/components';
import {CanvasRenderer} from 'echarts/renderers';
import type {ProfilePoint} from './types';
echarts.use([LineChart,BarChart,GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,MarkAreaComponent,CanvasRenderer]);
export default function ActivityCharts({points}:{points:ProfilePoint[]}){
 const host=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!host.current)return;const chart=echarts.init(host.current);chart.setOption({animation:false,color:['#168779','#df703c','#5084b4'],tooltip:{trigger:'axis'},legend:{bottom:0},grid:{left:45,right:45,top:24,bottom:90},xAxis:{type:'value',name:'min',min:0},yAxis:[{type:'value',name:'km/h',splitLine:{lineStyle:{color:'#e6eceb'}}},{type:'value',name:'bpm',splitLine:{show:false}}],dataZoom:[{type:'inside'},{type:'slider',bottom:28,height:22}],series:[{name:'Vitesse',type:'line',yAxisIndex:0,showSymbol:false,connectNulls:false,data:points.map(p=>[p[0],p[1]])},{name:'Fréquence cardiaque',type:'line',yAxisIndex:1,showSymbol:false,connectNulls:false,data:points.map(p=>[p[0],p[2]])}]});const resize=new ResizeObserver(()=>chart.resize());resize.observe(host.current);return()=>{resize.disconnect();chart.dispose();};},[points]);
 return <><div ref={host} className="chart" role="img" aria-label="Vitesse et fréquence cardiaque au cours de la séance ; zoom disponible"/><p className="footnote">Profil moyenné sur 15 secondes. Les valeurs manquantes restent des interruptions de la courbe. Le temps affiché est le temps écoulé.</p></>;
}
