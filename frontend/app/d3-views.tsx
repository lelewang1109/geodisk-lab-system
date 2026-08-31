'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export type GeoFeature={properties:{cell_id?:string|number;name?:string};geometry:{type:'Polygon'|'MultiPolygon';coordinates:unknown}};
export type FlowEdge={source:string;target:string;support:number;transition_score:number};

type PartitionProps={
  features:GeoFeature[];width:number;height:number;selected:string;onSelect:(id:string)=>void;
  mode:'spatial'|'annual'|'reference';membership?:Map<string,Record<string,string|number|null>>;stateId?:string;visible?:boolean;hole?:number;
};

function featureId(feature:GeoFeature){return String(feature.properties.cell_id??feature.properties.name??'')}

export function D3PartitionMap({features,width,height,selected,onSelect,mode,membership=new Map(),stateId='S1',visible=true,hole=0}:PartitionProps){
  const ref=useRef<SVGSVGElement>(null);
  useEffect(()=>{
    if(!ref.current)return;
    const svg=d3.select(ref.current).attr('viewBox',`0 0 ${width} ${height}`);
    svg.selectAll('*').remove();
    const root=svg.append('g').attr('class','d3-zoom-root');
    if(!features.length){
      if(mode==='spatial'&&visible){
        const nodes=d3.range(54).map(i=>{const ring=Math.floor(i/18),angle=(i%18)/18*Math.PI*2-.25,radius=42+ring*34;return{id:`CEG-${String(i+27).padStart(3,'0')}`,x:width/2+Math.cos(angle)*radius,y:height/2+Math.sin(angle)*radius,index:i}});
        const scale=d3.scaleSequential(d3.interpolateBlues).domain([0,nodes.length-1]);
        root.selectAll('circle.fallback-cell').data(nodes).join('circle').attr('class','fallback-cell').attr('cx',d=>d.x).attr('cy',d=>d.y).attr('r',d=>d.id===selected?7:4.7).attr('fill',d=>d.id===selected?'#e99a12':scale(d.index)).attr('stroke','#fff').attr('stroke-width',1).style('cursor','pointer').attr('tabindex',0).attr('aria-label',d=>`Spatial cell ${d.id}`).on('pointerenter',(_,d)=>onSelect(d.id)).on('click',(_,d)=>onSelect(d.id)).on('keydown',(event,d)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(d.id)}}).append('title').text(d=>d.id);
      }
      return;
    }
    const collection={type:'FeatureCollection',features} as d3.ExtendedFeatureCollection;
    const projection=d3.geoIdentity().reflectY(true).fitExtent([[8,8],[width-8,height-8]],collection);
    const path=d3.geoPath(projection);
    const blue=d3.scaleSequential(d3.interpolateBlues).domain([0,Math.max(features.length-1,1)]);
    const fill=(feature:GeoFeature,index:number)=>{
      const id=featureId(feature);
      if(id===selected)return '#e99a12';
      if(mode==='reference')return '#e4edf8';
      if(mode==='spatial')return blue(index*.9+features.length*.05);
      const row=membership.get(id);const included=String(row?.[`in_${stateId}`]).toLowerCase()==='true';
      if(!included)return '#edf2f6';
      const category=String(row?.overlap_category||'outside_states');
      if(category==='core_all3')return '#087f79';
      if(category==='pair_shared')return '#49bdb4';
      return '#a8e5df';
    };
    if(visible){
      root.selectAll('path.partition-cell').data(features,featureId).join('path').attr('class',`partition-cell ${mode}`).attr('d',feature=>path(feature as never)??'').attr('fill',fill).attr('fill-opacity',feature=>mode==='annual'&&String(membership.get(featureId(feature))?.[`in_${stateId}`]).toLowerCase()!=='true'?.32:1).attr('stroke','#fff').attr('stroke-width',.75).style('cursor','pointer').attr('tabindex',0).attr('aria-label',feature=>`${mode} cell ${featureId(feature)}`).on('pointerenter',(_,feature)=>onSelect(featureId(feature))).on('click',(_,feature)=>onSelect(featureId(feature))).on('keydown',(event,feature)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(featureId(feature))}}).each(function(feature){d3.select(this).append('title').text(`${mode} cell ${featureId(feature)}`)}).transition().duration(260).attr('fill',fill);
    }
    if(hole>0){root.append('circle').attr('class','d3-domain-hole').attr('cx',width/2).attr('cy',height/2).attr('r',hole).attr('fill','#fff').attr('stroke',mode==='annual'?'#079a91':'#2563eb').attr('stroke-width',2);root.append('text').attr('class','d3-domain-label').attr('x',width/2).attr('y',height/2+4).attr('text-anchor','middle').attr('fill',mode==='annual'?'#087a75':'#2554a8').attr('font-size',12).attr('font-family','ui-monospace, monospace').attr('font-weight',800).text(mode==='annual'?stateId:'G');}
    const zoom=d3.zoom<SVGSVGElement,unknown>().scaleExtent([1,5]).on('zoom',event=>root.attr('transform',event.transform));
    svg.call(zoom).on('dblclick.zoom',null);
    return()=>{svg.on('.zoom',null)};
  },[features,width,height,selected,onSelect,mode,membership,stateId,visible,hole]);
  return <svg ref={ref} className="d3-partition-svg" role="img" aria-label={`${mode} partition; wheel or drag to zoom and pan`}/>;
}

export function D3ProvinceFlow({features,edges,width,height,selected,onSelect,visible=true}: {features:GeoFeature[];edges:FlowEdge[];width:number;height:number;selected:string;onSelect:(id:string)=>void;visible?:boolean}){
  const ref=useRef<SVGSVGElement>(null);
  useEffect(()=>{
    if(!ref.current)return;
    const svg=d3.select(ref.current).attr('viewBox',`0 0 ${width} ${height}`);svg.selectAll('*').remove();
    const defs=svg.append('defs');defs.append('marker').attr('id','d3-flow-arrow').attr('viewBox','0 0 8 8').attr('refX',7).attr('refY',4).attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto').append('path').attr('d','M0 0L8 4 0 8Z').attr('fill','#7550c8');
    const root=svg.append('g');
    if(!features.length)return;
    const collection={type:'FeatureCollection',features} as d3.ExtendedFeatureCollection;
    const projection=d3.geoMercator().fitExtent([[14,9],[width-14,height-9]],collection);const path=d3.geoPath(projection);
    const centers=new Map(features.map(feature=>[featureId(feature),path.centroid(feature as never)]));
    root.selectAll('path.province-shape').data(features,featureId).join('path').attr('class','province-shape').attr('d',feature=>path(feature as never)??'').attr('fill',feature=>featureId(feature)===selected?'#f7d69d':'#ece8fb').attr('stroke',feature=>featureId(feature)===selected?'#e99a12':'#a999d0').attr('stroke-width',feature=>featureId(feature)===selected?1.5:.65).style('cursor','pointer').attr('tabindex',0).attr('aria-label',feature=>`Province ${featureId(feature)}`).on('pointerenter',(_,feature)=>onSelect(featureId(feature))).on('click',(_,feature)=>onSelect(featureId(feature))).on('keydown',(event,feature)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(featureId(feature))}}).append('title').text(feature=>featureId(feature));
    if(visible){root.selectAll('path.flow-link').data(edges).join('path').attr('class','flow-link').attr('d',edge=>{const a=centers.get(edge.source),b=centers.get(edge.target);if(!a||!b)return'';const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-10;return`M${a[0]},${a[1]} Q${mx},${my} ${b[0]},${b[1]}`}).attr('fill','none').attr('stroke','#7550c8').attr('stroke-width',edge=>1+edge.support).attr('stroke-opacity',edge=>.32+edge.transition_score*.6).attr('marker-end','url(#d3-flow-arrow)').append('title').text(edge=>`${edge.source} → ${edge.target}`);}
    const labels=root.selectAll('g.province-node').data(features,featureId).join('g').attr('class','province-node').attr('transform',feature=>{const c=centers.get(featureId(feature))??[0,0];return`translate(${c[0]},${c[1]})`});labels.append('circle').attr('r',feature=>featureId(feature)===selected?5.5:4).attr('fill','#7550c8').attr('stroke','#fff');labels.append('text').attr('x',7).attr('y',-6).attr('fill','#4a3b70').attr('font-size',9).attr('font-weight',700).attr('paint-order','stroke').attr('stroke','#fff').attr('stroke-width',3).text(feature=>featureId(feature));
    const zoom=d3.zoom<SVGSVGElement,unknown>().scaleExtent([1,5]).on('zoom',event=>root.attr('transform',event.transform));svg.call(zoom).on('dblclick.zoom',null);return()=>{svg.on('.zoom',null)};
  },[features,edges,width,height,selected,onSelect,visible]);
  return <svg ref={ref} className="d3-province-svg" role="img" aria-label="Province migration network; wheel or drag to zoom and pan"/>;
}

export function D3MonthlyProfile({values,selected,onSelect,width=260,height=108}:{values:number[];selected:number;onSelect:(index:number)=>void;width?:number;height?:number}){
  const ref=useRef<SVGSVGElement>(null);
  useEffect(()=>{
    if(!ref.current||!values.length)return;
    const svg=d3.select(ref.current).attr('viewBox',`0 0 ${width} ${height}`);svg.selectAll('*').remove();
    const margin={top:9,right:8,bottom:20,left:29};const x=d3.scaleLinear().domain([0,values.length-1]).range([margin.left,width-margin.right]);const extent=d3.extent(values) as [number,number];const pad=Math.max((extent[1]-extent[0])*.15,2);const y=d3.scaleLinear().domain([extent[0]-pad,extent[1]+pad]).nice().range([height-margin.bottom,margin.top]);
    const area=d3.area<number>().x((_,i)=>x(i)).y0(height-margin.bottom).y1(d=>y(d)).curve(d3.curveMonotoneX);const line=d3.line<number>().x((_,i)=>x(i)).y(d=>y(d)).curve(d3.curveMonotoneX);
    svg.append('path').datum(values).attr('class','d3-profile-area').attr('d',area).attr('fill','#d9f3f0');svg.append('path').datum(values).attr('class','d3-profile-line').attr('d',line).attr('fill','none').attr('stroke','#079a91').attr('stroke-width',2);
    svg.append('g').attr('class','d3-axis x').attr('transform',`translate(0,${height-margin.bottom})`).call(d3.axisBottom(x).tickValues(d3.range(values.length).filter(i=>i%2===0)).tickFormat(i=>String(Number(i)+1)).tickSize(3)).call(g=>g.select('.domain').attr('stroke','#cfd9e6')).call(g=>g.selectAll('text').attr('fill','#75849a').attr('font-size',9));svg.append('g').attr('class','d3-axis y').attr('transform',`translate(${margin.left},0)`).call(d3.axisLeft(y).ticks(3).tickSize(-(width-margin.left-margin.right))).call(g=>g.select('.domain').remove()).call(g=>g.selectAll('.tick line').attr('stroke','#e5ebf2')).call(g=>g.selectAll('text').attr('fill','#75849a').attr('font-size',9));
    svg.append('line').attr('class','d3-month-guide').attr('x1',x(selected)).attr('x2',x(selected)).attr('y1',margin.top).attr('y2',height-margin.bottom).attr('stroke','#e99a12').attr('stroke-width',1);svg.selectAll('circle.month-point').data(values).join('circle').attr('class','month-point').attr('cx',(_,i)=>x(i)).attr('cy',d=>y(d)).attr('r',(_,i)=>i===selected?4:2.5).attr('fill',(_,i)=>i===selected?'#e99a12':'#079a91').attr('stroke','#fff').attr('stroke-width',1).append('title').text((d,i)=>`${i+1}: ${d.toFixed(1)}`);
    svg.append('rect').attr('data-chart-hit','').attr('x',margin.left).attr('y',margin.top).attr('width',width-margin.left-margin.right).attr('height',height-margin.top-margin.bottom).attr('fill','transparent').style('cursor','crosshair').on('pointermove',event=>{const [px]=d3.pointer(event);const index=Math.max(0,Math.min(values.length-1,Math.round(x.invert(px))));onSelect(index)}).on('click',event=>{const [px]=d3.pointer(event);onSelect(Math.max(0,Math.min(values.length-1,Math.round(x.invert(px)))))});
  },[values,selected,onSelect,width,height]);
  return <svg ref={ref} className="d3-profile-svg" role="img" aria-label="Monthly PM2.5 profile; move the pointer to select a month"/>;
}
