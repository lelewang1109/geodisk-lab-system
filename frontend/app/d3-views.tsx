'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export type GeoFeature={properties:{cell_id?:string|number;name?:string};geometry:{type:'Polygon'|'MultiPolygon';coordinates:unknown}};
export type FlowEdge={source:string;target:string;support:number;transition_score:number};
export type EdgeStatus={source:string;target:string;status:'preserved'|'lost'|'new'};

const COLORS={
  ink:'#2e3d4f',muted:'#7b8996',line:'#d8e0e4',blue:'#2f789f',blueDark:'#225d7d',
  blueSoft:'#dcebf1',coral:'#d76552',coralSoft:'#f5dfda',mint:'#78bcae',mintSoft:'#dff1ec',
  amber:'#e7a63a',paper:'#fbfcfc',neutral:'#edf1f2',
};

function featureId(feature:GeoFeature){return String(feature.properties.cell_id??feature.properties.name??'')}
function collection(features:GeoFeature[]){return {type:'FeatureCollection',features} as d3.ExtendedFeatureCollection}

type PartitionProps={
  features:GeoFeature[]; width:number; height:number; selected:string; onSelect:(id:string)=>void;
  mode:'spatial'|'annual'|'reference'; membership?:Map<string,Record<string,string|number|null>>;
  stateId?:string; visible?:boolean; values?:Map<string,number>; colorMode?:'scalar'|'fidelity'|'boundary';
  boundaryCells?:Set<string>; edgeStatus?:EdgeStatus[]; showNeighbors?:boolean; compact?:boolean;
};

export function D3PartitionMap({
  features,width,height,selected,onSelect,mode,membership=new Map(),stateId='S1',visible=true,
  values=new Map(),colorMode='scalar',boundaryCells=new Set(),edgeStatus=[],showNeighbors=false,compact=false,
}:PartitionProps){
  const ref=useRef<SVGSVGElement>(null);
  useEffect(()=>{
    if(!ref.current)return;
    const svg=d3.select(ref.current).attr('viewBox',`0 0 ${width} ${height}`);
    svg.selectAll('*').remove();
    svg.append('title').text(`${mode} partition`);
    svg.append('desc').text('Select a cell to coordinate the map, relation view and monthly profile.');
    const root=svg.append('g').attr('class','d3-zoom-root');
    if(!features.length)return;
    const projection=d3.geoIdentity().reflectY(true).fitExtent([[compact?3:10,compact?3:10],[width-(compact?3:10),height-(compact?3:10)]],collection(features));
    const path=d3.geoPath(projection);
    const numeric=features.map(feature=>values.get(featureId(feature))).filter((value):value is number=>Number.isFinite(value));
    const extent=(d3.extent(numeric) as [number,number])||[0,1];
    if(extent[0]===extent[1])extent[1]=extent[0]+1;
    const scalar=d3.scaleSequential(d3.interpolateRgbBasis([COLORS.blueSoft,'#8fc3d2',COLORS.blueDark])).domain(extent);
    const fidelity=d3.scaleSequential(d3.interpolateRgbBasis([COLORS.coralSoft,'#f6f2df',COLORS.blue])).domain([0,1]);
    const fill=(feature:GeoFeature)=>{
      const id=featureId(feature);
      if(id===selected)return COLORS.amber;
      if(mode==='reference')return boundaryCells.has(id)?'#e4eaec':'#f0f3f4';
      if(mode==='annual'){
        const row=membership.get(id); const included=String(row?.[`in_${stateId}`]).toLowerCase()==='true';
        if(!included)return '#f0f3f3';
        const category=String(row?.overlap_category||'');
        if(category==='core_all3')return '#357f77';
        if(category==='pair_shared')return COLORS.mint;
        return '#b9ddd5';
      }
      if(colorMode==='boundary')return boundaryCells.has(id)?COLORS.coralSoft:COLORS.blueSoft;
      if(colorMode==='fidelity')return fidelity(values.get(id)??0);
      return scalar(values.get(id)??extent[0]);
    };
    if(visible){
      root.selectAll('path.partition-cell').data(features,featureId).join('path')
        .attr('class',feature=>`partition-cell ${mode}${featureId(feature)===selected?' selected':''}`)
        .attr('d',feature=>path(feature as never)??'').attr('fill',fill)
        .attr('fill-opacity',feature=>mode==='annual'&&String(membership.get(featureId(feature))?.[`in_${stateId}`]).toLowerCase()!=='true'?.28:1)
        .attr('stroke',feature=>featureId(feature)===selected?'#8f5f16':'#ffffff')
        .attr('stroke-width',feature=>featureId(feature)===selected?1.8:(compact?.45:.75))
        .attr('vector-effect','non-scaling-stroke').style('cursor','pointer').attr('tabindex',0)
        .attr('aria-label',feature=>`${mode} cell ${featureId(feature)}`)
        .on('click',(_,feature)=>onSelect(featureId(feature)))
        .on('keydown',(event,feature)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(featureId(feature))}})
        .each(function(feature){
          const id=featureId(feature); const value=values.get(id);
          d3.select(this).append('title').text(`${id}${Number.isFinite(value)?` · ${Number(value).toFixed(2)}`:''}`);
        });
    }
    if(showNeighbors&&selected){
      const centroids=new Map(features.map(feature=>[featureId(feature),path.centroid(feature as never)]));
      const incident=edgeStatus.filter(edge=>edge.source===selected||edge.target===selected);
      root.append('g').attr('class','neighbor-links').selectAll('path').data(incident).join('path')
        .attr('d',edge=>{const other=edge.source===selected?edge.target:edge.source;const a=centroids.get(selected),b=centroids.get(other);if(!a||!b)return'';const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-7;return`M${a[0]},${a[1]} Q${mx},${my} ${b[0]},${b[1]}`})
        .attr('fill','none').attr('stroke',edge=>edge.status==='lost'?COLORS.coral:edge.status==='new'?COLORS.mint:COLORS.blue)
        .attr('stroke-width',edge=>edge.status==='preserved'?1.8:1.4).attr('stroke-dasharray',edge=>edge.status==='lost'?'4 3':null)
        .attr('stroke-opacity',.9).attr('vector-effect','non-scaling-stroke').style('pointer-events','none');
    }
    if(!compact){
      const zoom=d3.zoom<SVGSVGElement,unknown>().scaleExtent([1,6]).on('zoom',event=>root.attr('transform',event.transform));
      svg.call(zoom).on('dblclick.zoom',null);
      return()=>{svg.on('.zoom',null)};
    }
  },[features,width,height,selected,onSelect,mode,membership,stateId,visible,values,colorMode,boundaryCells,edgeStatus,showNeighbors,compact]);
  return <svg ref={ref} className="d3-partition-svg" role="img" aria-label={`${mode} partition; click a cell to select, drag or wheel to navigate`}/>;
}

export function D3ProvinceFlow({features,edges,width,height,selected,onSelect,visible=true,quiet=false}:{features:GeoFeature[];edges:FlowEdge[];width:number;height:number;selected:string;onSelect:(id:string)=>void;visible?:boolean;quiet?:boolean}){
  const ref=useRef<SVGSVGElement>(null);
  useEffect(()=>{
    if(!ref.current)return;
    const svg=d3.select(ref.current).attr('viewBox',`0 0 ${width} ${height}`);svg.selectAll('*').remove();
    svg.append('title').text('Regional context and migration flow');
    const defs=svg.append('defs');
    defs.append('marker').attr('id',`flow-arrow-${quiet?'q':'m'}`).attr('viewBox','0 0 8 8').attr('refX',7).attr('refY',4).attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto').append('path').attr('d','M0 0L8 4 0 8Z').attr('fill',COLORS.coral);
    const root=svg.append('g'); if(!features.length)return;
    const projection=d3.geoMercator().fitExtent([[quiet?8:14,quiet?8:12],[width-(quiet?8:14),height-(quiet?8:12)]],collection(features));
    const path=d3.geoPath(projection); const centers=new Map(features.map(feature=>[featureId(feature),path.centroid(feature as never)]));
    root.selectAll('path.province-shape').data(features,featureId).join('path').attr('class','province-shape')
      .attr('d',feature=>path(feature as never)??'').attr('fill',feature=>featureId(feature)===selected?'#f7e2b8':'#e9eff1')
      .attr('stroke',feature=>featureId(feature)===selected?COLORS.amber:'#aebbc2').attr('stroke-width',feature=>featureId(feature)===selected?1.6:.7)
      .attr('vector-effect','non-scaling-stroke').style('cursor','pointer').attr('tabindex',0).attr('aria-label',feature=>`Province ${featureId(feature)}`)
      .on('click',(_,feature)=>onSelect(featureId(feature))).on('keydown',(event,feature)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(featureId(feature))}})
      .append('title').text(feature=>featureId(feature));
    if(visible){
      root.selectAll('path.flow-link').data(edges).join('path').attr('class','flow-link')
        .attr('d',edge=>{const a=centers.get(edge.source),b=centers.get(edge.target);if(!a||!b)return'';const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2-(quiet?5:12);return`M${a[0]},${a[1]} Q${mx},${my} ${b[0]},${b[1]}`})
        .attr('fill','none').attr('stroke',COLORS.coral).attr('stroke-width',edge=>.8+edge.support*.7)
        .attr('stroke-opacity',edge=>.25+edge.transition_score*.65).attr('marker-end',`url(#flow-arrow-${quiet?'q':'m'})`)
        .attr('vector-effect','non-scaling-stroke').append('title').text(edge=>`${edge.source} → ${edge.target}`);
    }
    if(!quiet){
      const labels=root.selectAll('g.province-node').data(features,featureId).join('g').attr('class','province-node').attr('transform',feature=>{const c=centers.get(featureId(feature))??[0,0];return`translate(${c[0]},${c[1]})`});
      labels.append('circle').attr('r',feature=>featureId(feature)===selected?5:3.5).attr('fill',feature=>featureId(feature)===selected?COLORS.amber:COLORS.blue).attr('stroke','#fff');
      labels.append('text').attr('x',6).attr('y',-5).attr('fill',COLORS.ink).attr('font-size',10).attr('font-weight',500).attr('paint-order','stroke').attr('stroke','#fff').attr('stroke-width',3).text(feature=>featureId(feature));
    }
    const zoom=d3.zoom<SVGSVGElement,unknown>().scaleExtent([1,5]).on('zoom',event=>root.attr('transform',event.transform));svg.call(zoom).on('dblclick.zoom',null);return()=>{svg.on('.zoom',null)};
  },[features,edges,width,height,selected,onSelect,visible,quiet]);
  return <svg ref={ref} className="d3-province-svg" role="img" aria-label="Regional context map; click a province to change dataset"/>;
}

export function D3MonthlyProfile({values,selected,onSelect,width=500,height=120}:{values:number[];selected:number;onSelect:(index:number)=>void;width?:number;height?:number}){
  const ref=useRef<SVGSVGElement>(null);
  useEffect(()=>{
    if(!ref.current||!values.length)return;
    const svg=d3.select(ref.current).attr('viewBox',`0 0 ${width} ${height}`);svg.selectAll('*').remove();
    svg.append('title').text('Monthly scalar profile');
    const margin={top:10,right:10,bottom:22,left:36};const x=d3.scaleLinear().domain([0,values.length-1]).range([margin.left,width-margin.right]);const extent=d3.extent(values) as [number,number];const pad=Math.max((extent[1]-extent[0])*.16,2);const y=d3.scaleLinear().domain([extent[0]-pad,extent[1]+pad]).nice().range([height-margin.bottom,margin.top]);
    const area=d3.area<number>().x((_,i)=>x(i)).y0(height-margin.bottom).y1(d=>y(d)).curve(d3.curveMonotoneX);const line=d3.line<number>().x((_,i)=>x(i)).y(d=>y(d)).curve(d3.curveMonotoneX);
    svg.append('path').datum(values).attr('d',area).attr('fill',COLORS.blueSoft).attr('fill-opacity',.72);
    svg.append('path').datum(values).attr('d',line).attr('fill','none').attr('stroke',COLORS.blue).attr('stroke-width',2);
    svg.append('g').attr('transform',`translate(0,${height-margin.bottom})`).call(d3.axisBottom(x).tickValues(d3.range(values.length)).tickFormat(i=>String(Number(i)+1)).tickSize(3)).call(g=>g.select('.domain').attr('stroke',COLORS.line)).call(g=>g.selectAll('text').attr('fill',COLORS.muted).attr('font-size',10));
    svg.append('g').attr('transform',`translate(${margin.left},0)`).call(d3.axisLeft(y).ticks(3).tickSize(-(width-margin.left-margin.right))).call(g=>g.select('.domain').remove()).call(g=>g.selectAll('.tick line').attr('stroke',COLORS.line).attr('stroke-opacity',.7)).call(g=>g.selectAll('text').attr('fill',COLORS.muted).attr('font-size',10));
    svg.append('line').attr('x1',x(selected)).attr('x2',x(selected)).attr('y1',margin.top).attr('y2',height-margin.bottom).attr('stroke',COLORS.coral).attr('stroke-width',1.2);
    svg.selectAll('circle.month-point').data(values).join('circle').attr('cx',(_,i)=>x(i)).attr('cy',d=>y(d)).attr('r',(_,i)=>i===selected?4.5:2.5).attr('fill',(_,i)=>i===selected?COLORS.coral:COLORS.blue).attr('stroke','#fff').attr('stroke-width',1).append('title').text((d,i)=>`Month ${i+1}: ${d.toFixed(1)}`);
    svg.append('rect').attr('x',margin.left).attr('y',margin.top).attr('width',width-margin.left-margin.right).attr('height',height-margin.top-margin.bottom).attr('fill','transparent').style('cursor','crosshair').on('click',event=>{const [px]=d3.pointer(event);onSelect(Math.max(0,Math.min(values.length-1,Math.round(x.invert(px)))))});
  },[values,selected,onSelect,width,height]);
  return <svg ref={ref} className="d3-profile-svg" role="img" aria-label="Monthly profile; click a month to coordinate all temporal views"/>;
}

export function D3EgoComparison({referenceEdges,displayEdges,selected,width=320,height=250}:{referenceEdges:string[][];displayEdges:string[][];selected:string;width?:number;height?:number}){
  const ref=useRef<SVGSVGElement>(null);
  useEffect(()=>{
    if(!ref.current)return;
    const svg=d3.select(ref.current).attr('viewBox',`0 0 ${width} ${height}`);svg.selectAll('*').remove();
    svg.append('title').text(`Reference and display neighbors for ${selected}`);
    const neighbors=(edges:string[][])=>new Set(edges.filter(edge=>edge[0]===selected||edge[1]===selected).map(edge=>edge[0]===selected?edge[1]:edge[0]));
    const left=neighbors(referenceEdges),right=neighbors(displayEdges);const union=[...new Set([...left,...right])].sort();
    const y=d3.scalePoint<string>().domain(union).range([28,height-30]).padding(.35);const xLeft=58,xCenter=width/2,xRight=width-58,yCenter=height/2;
    svg.append('text').attr('x',xLeft).attr('y',15).attr('text-anchor','middle').attr('fill',COLORS.muted).attr('font-size',10).text(`REFERENCE · ${left.size}`);
    svg.append('text').attr('x',xRight).attr('y',15).attr('text-anchor','middle').attr('fill',COLORS.muted).attr('font-size',10).text(`DISPLAY · ${right.size}`);
    svg.append('line').attr('x1',xCenter).attr('x2',xCenter).attr('y1',24).attr('y2',height-20).attr('stroke',COLORS.line);
    for(const id of union){
      const yy=y(id)??yCenter;const common=left.has(id)&&right.has(id);
      if(left.has(id))svg.append('path').attr('d',`M${xCenter-8},${yCenter} C${xCenter-45},${yCenter} ${xLeft+34},${yy} ${xLeft},${yy}`).attr('fill','none').attr('stroke',common?COLORS.blue:COLORS.coral).attr('stroke-width',common?1.4:1.6).attr('stroke-dasharray',common?null:'4 3').attr('opacity',.8);
      if(right.has(id))svg.append('path').attr('d',`M${xCenter+8},${yCenter} C${xCenter+45},${yCenter} ${xRight-34},${yy} ${xRight},${yy}`).attr('fill','none').attr('stroke',common?COLORS.blue:COLORS.mint).attr('stroke-width',common?1.4:1.6).attr('opacity',.8);
      if(left.has(id)){svg.append('circle').attr('cx',xLeft).attr('cy',yy).attr('r',4).attr('fill',common?COLORS.blue:COLORS.coral);svg.append('text').attr('x',xLeft-7).attr('y',yy+3).attr('text-anchor','end').attr('fill',COLORS.ink).attr('font-size',9).text(id.slice(-5));}
      if(right.has(id)){svg.append('circle').attr('cx',xRight).attr('cy',yy).attr('r',4).attr('fill',common?COLORS.blue:COLORS.mint);svg.append('text').attr('x',xRight+7).attr('y',yy+3).attr('fill',COLORS.ink).attr('font-size',9).text(id.slice(-5));}
      if(common)svg.append('line').attr('x1',xLeft+4).attr('x2',xRight-4).attr('y1',yy).attr('y2',yy).attr('stroke',COLORS.blueSoft).attr('stroke-width',.7).lower();
    }
    svg.append('circle').attr('cx',xCenter).attr('cy',yCenter).attr('r',18).attr('fill','#fff').attr('stroke',COLORS.amber).attr('stroke-width',2);
    svg.append('text').attr('x',xCenter).attr('y',yCenter-2).attr('text-anchor','middle').attr('fill',COLORS.ink).attr('font-size',8).attr('font-weight',600).text('ACTIVE');
    svg.append('text').attr('x',xCenter).attr('y',yCenter+8).attr('text-anchor','middle').attr('fill',COLORS.muted).attr('font-size',7).text(selected.slice(-5));
  },[referenceEdges,displayEdges,selected,width,height]);
  return <svg ref={ref} className="d3-ego-svg" role="img" aria-label="Reference versus displayed neighbor comparison"/>;
}
