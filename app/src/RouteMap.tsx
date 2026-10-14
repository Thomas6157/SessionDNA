import {useEffect,useRef} from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import bbox from '@turf/bbox';
import length from '@turf/length';
import type {FeatureCollection} from 'geojson';
import {num} from './lib/format';
export default function RouteMap({geojson}:{geojson:FeatureCollection}){
 const host=useRef<HTMLDivElement>(null);const distance=length(geojson,{units:'kilometers'});
 useEffect(()=>{if(!host.current||!geojson.features.length)return;const bounds=bbox(geojson);if(bounds.some(n=>!Number.isFinite(n)))return;const map=new maplibregl.Map({container:host.current,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#e8efeb'}}]},center:[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2],zoom:12,attributionControl:false});map.addControl(new maplibregl.NavigationControl(),'top-right');map.on('load',()=>{map.addSource('route',{type:'geojson',data:geojson});map.addLayer({id:'route-line',type:'line',source:'route',paint:{'line-color':'#127d72','line-width':4,'line-opacity':0.95},layout:{'line-cap':'round','line-join':'round'}});map.fitBounds([[bounds[0],bounds[1]],[bounds[2],bounds[3]]],{padding:40,maxZoom:16,duration:0});});return()=>map.remove();},[geojson]);
 return <><div ref={host} className="route-map" role="img" aria-label="Tracé GPS de la séance"/><p className="footnote">Tracé GPS · {num(distance,2)} km sur les points disponibles. Affichage local sans fond de carte externe ; aucun parcours transmis à un fournisseur de tuiles.</p></>;
}
