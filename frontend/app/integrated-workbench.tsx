'use client';

import { useEffect, useMemo, useState } from 'react';
import './integrated-workbench.css';
import { D3MonthlyProfile, D3PartitionMap, D3ProvinceFlow, type FlowEdge } from './d3-views';

const API=process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8000';
const MONTHS=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
const REGIONS=[['湖北','Hubei'],['湖南','Hunan'],['江西','Jiangxi'],['广东','Guangdong'],['福建','Fujian'],['广西','Guangxi'],['安徽','Anhui'],['浙江','Zhejiang']];

type Feature={properties:{cell_id?:string|number;name?:string};geometry:{type:'Polygon'|'MultiPolygon';coordinates:unknown}};
type WorkbenchData={label:string;unit:string;original:{features:Feature[]};display:{features:Feature[]};nodes:Array<Record<string,string|number|boolean|null>>;temporal:Array<Record<string,string|number|null>>};
type AnnualData={annulus:{features:Feature[]};state_intervals:Array<Record<string,string|number|null>>;monthly_summary:Array<Record<string,string|number|null>>;monthly_values:Array<Record<string,string|number|null>>;frequency:Array<Record<string,string|number|null>>;membership:Array<Record<string,string|number|null>>};
type PathData={provinces:{features:Feature[]};case:Record<string,unknown>};
type LegacyData={annual_states:AnnualData;migration_paths:PathData};

export default function IntegratedWorkbench(){
  const [dataset,setDataset]=useState('湖北');
  const [view,setView]=useState<'disk'|'annulus'>('disk');
  const [stateId,setStateId]=useState('S2');
  const [month,setMonth]=useState(7);
  const [step,setStep]=useState(3);
  const [selectedCell,setSelectedCell]=useState('CEG-031');
  const [selectedStateCell,setSelectedStateCell]=useState('1');
  const [selectedProvince,setSelectedProvince]=useState('湖北');
  const [workbench,setWorkbench]=useState<WorkbenchData|null>(null);
  const [legacy,setLegacy]=useState<LegacyData|null>(null);
  const [layers,setLayers]=useState({power:true,states:true,paths:true});
  const [online,setOnline]=useState(false);

  useEffect(()=>{
    let active=true;
    fetch(`${API}/api/workbench?dataset=${encodeURIComponent(dataset)}&view=${view}`).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(data=>{if(active){setWorkbench(data);setOnline(true);const id=data.display?.features?.[0]?.properties?.cell_id;if(id)setSelectedCell(String(id));}}).catch(()=>fetch(`/data/workbench-hubei-${view}.json`).then(r=>r.json()).then(data=>{if(active){setWorkbench(data);setOnline(false);const id=data.display?.features?.[0]?.properties?.cell_id;if(id)setSelectedCell(String(id));}}).catch(()=>{if(active){setWorkbench(null);setOnline(false);}}));
    return()=>{active=false};
  },[dataset,view]);
  useEffect(()=>{
    fetch(`${API}/api/legacy-insights`).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(setLegacy).catch(()=>fetch('/data/legacy-insights.json').then(r=>r.json()).then(setLegacy).catch(()=>setLegacy(null)));
  },[]);

  const original=useMemo(()=>workbench?.original.features||[],[workbench]);
  const spatial=useMemo(()=>workbench?.display.features||[],[workbench]);
  const annual=useMemo(()=>legacy?.annual_states.annulus.features||[],[legacy]);
  const provinces=useMemo(()=>legacy?.migration_paths.provinces.features||[],[legacy]);
  const node=new Map((workbench?.nodes||[]).map(row=>[String(row.cell_id),row])).get(selectedCell);
  const series=(workbench?.temporal||[]).filter(row=>String(row.cell_id)===selectedCell).sort((a,b)=>Number(a.month)-Number(b.month));
  const annualData=legacy?.annual_states;
  const membership=new Map((annualData?.membership||[]).map(row=>[String(row.cell_id),row]));
  const member=membership.get(selectedStateCell);
  const stateSeries=(annualData?.monthly_values||[]).filter(row=>String(row.cell_id)===selectedStateCell).sort((a,b)=>Number(a.month)-Number(b.month));
  const monthly=stateSeries.find(row=>Number(row.month)===month+1);
  const summary=annualData?.monthly_summary||MONTHS.map((m,i)=>({month_name:m,area_weighted_mean_pm25:[62.8,56.6,58.7,51.5,50.5,52.1,48.4,43.1,41.7,50.5,79.3,73.9][i],hotspot_cell_count:[70,34,41,7,9,42,0,0,0,17,111,92][i]}));
  const caseData=(legacy?.migration_paths.case||{}) as Record<string,unknown>;
  const edges=((caseData.regional_edges||[]) as Array<Record<string,unknown>>).filter(edge=>Number(edge.step)<=step+1).map(edge=>({source:String(edge.source),target:String(edge.target),support:Number(edge.support||1),transition_score:Number(edge.transition_score||0)} satisfies FlowEdge));
  const reference=(caseData.reference_sequence||['湖北','安徽','江西','福建']) as string[];
  const labels=(caseData.labels||['2000-01-10','2000-01-11','2000-01-12','2000-01-13']) as string[];
  const values=stateSeries.length?stateSeries.map(row=>Number(row.pm25)):series.length?series.map(row=>Number(row.value)):[62,56,59,51,50,52,48,43,42,51,79,74];

  function toggleLayer(key:keyof typeof layers){setLayers(current=>({...current,[key]:!current[key]}));}
  function selectState(id:string){setStateId(id);const first=annual.find(feature=>{const featureId=String(feature.properties.cell_id??feature.properties.name??'');return String(membership.get(featureId)?.[`in_${id}`]).toLowerCase()==='true'});if(first)setSelectedStateCell(String(first.properties.cell_id??first.properties.name??''));}

  return <main className="iw-shell">
    <header className="iw-header">
      <div className="iw-brand"><b>G·Δ</b><span><strong>GeoDisk Lab</strong><small>INTEGRATED SPATIOTEMPORAL WORKBENCH</small></span></div>
      <div className="iw-story"><span><i className="story-blue"/>Spatial mapping</span><em>→</em><span><i className="story-teal"/>Annual states</span><em>→</em><span><i className="story-purple"/>Migration paths</span></div>
      <div className="iw-context"><i className={online?'online':''}/><b>{online?'LIVE DATA':'EMBEDDED SNAPSHOT'}</b><span>D3 v7.9</span></div>
    </header>

    <section className="iw-layout">
      <aside className="iw-panel iw-controls">
        <PanelTitle code="A" title="Synchronized Controls" subtitle="ONE SCREEN · THREE ANALYSIS LENSES" accent="blue"/>
        <label>DATASET<select value={dataset} disabled={!online} onChange={e=>setDataset(e.target.value)}>{REGIONS.map(region=><option key={region[0]} value={region[0]}>{region[1]} · PM₂.₅</option>)}</select><small>{online?'Live multi-region data':'Published Hubei snapshot'}</small></label>
        <label>TARGET DOMAIN<div className="iw-segment"><button className={view==='disk'?'active blue':''} onClick={()=>setView('disk')}>Disk</button><button className={view==='annulus'?'active blue':''} onClick={()=>setView('annulus')}>Annulus</button></div></label>
        <label>ANNUAL STATE<div className="iw-segment triple">{['S1','S2','S3'].map(id=><button key={id} className={stateId===id?'active teal':''} onClick={()=>selectState(id)}>{id}</button>)}</div><small>{stateId==='S1'?'Jan–Mar · q80 68.5':stateId==='S2'?'Apr–Sep · q80 60.6':'Oct–Dec · q80 87.2'}</small></label>
        <label>MONTH <b>{MONTHS[month]}</b><input className="teal-range" type="range" min="0" max="11" value={month} onChange={e=>setMonth(Number(e.target.value))}/></label>
        <label>PATH STEP <b>0{step+1}</b><input className="purple-range" type="range" min="0" max="3" value={step} onChange={e=>setStep(Number(e.target.value))}/><small>{labels[step]}</small></label>
        <div className="iw-subhead">VISIBLE LAYERS</div>
        <div className="iw-layer-list">{([['power','Power partition','blue'],['states','State membership','teal'],['paths','Migration flow','purple']] as const).map(([key,name,color])=><button key={key} className={layers[key]?'active':''} onClick={()=>toggleLayer(key)}><i className={color}/><span>{name}</span><b>{layers[key]?'ON':'OFF'}</b></button>)}</div>
        <div className="iw-selection-bridge"><small>ACTIVE SELECTIONS</small><b>{selectedCell} <i>/</i> STATE {selectedStateCell}</b><span>{MONTHS[month]} · {stateId} · {view.toUpperCase()}</span></div>
      </aside>

      <section className="iw-canvas">
        <article className="iw-panel iw-spatial"><PanelTitle code="B" title="Spatial Mapping" subtitle="GEOGRAPHIC REFERENCE → FINAL PARTITION" accent="blue"/>
          <div className="spatial-body"><div className="geo-inset"><ViewTag code="B1" label="Geographic"/><D3PartitionMap features={original} width={130} height={218} selected={selectedCell} onSelect={setSelectedCell} mode="reference"/></div>
          <div className="power-view"><ViewTag code="B2" label={view==='disk'?'GeoDisk':'GeoAnnulus'}/><D3PartitionMap features={spatial} width={350} height={230} selected={selectedCell} onSelect={setSelectedCell} mode="spatial" visible={layers.power} hole={view==='annulus'?28:0}/><div className="spatial-scale"><span>LOW</span><i/><span>HIGH</span></div></div></div>
        </article>

        <article className="iw-panel iw-states"><PanelTitle code="C" title="Annual State Lens" subtitle="176 CELLS · FIXED STATE INTERVALS" accent="teal"/>
          <div className="state-body"><div className="state-map"><ViewTag code="C1" label={`${stateId} hotspots`}/><D3PartitionMap features={annual} width={330} height={230} selected={selectedStateCell} onSelect={setSelectedStateCell} mode="annual" membership={membership} stateId={stateId} visible={layers.states} hole={22}/></div>
          <div className="state-side"><div className="state-switch">{['S1','S2','S3'].map(id=><button key={id} className={stateId===id?'active':''} onClick={()=>selectState(id)}><b>{id}</b><span>{id==='S1'?'01–03':id==='S2'?'04–09':'10–12'}</span></button>)}</div><div className="month-spark">{summary.map((row,i)=><button key={i} className={month===i?'active':''} onClick={()=>setMonth(i)} title={MONTHS[i]}><i style={{height:`${Math.max(9,Number(row.area_weighted_mean_pm25)/90*100)}%`}}/><span>{i+1}</span></button>)}</div><div className="state-legend"><span><i className="all3"/>all 3</span><span><i className="pair"/>pair</span><span><i className="specific"/>specific</span></div></div></div>
        </article>

        <article className="iw-panel iw-path"><PanelTitle code="D" title="Migration Path Lens" subtitle="PROVINCE GRAPH · FOUR-DAY CASE WINDOW" accent="purple"/>
          <div className="path-body"><div className="province-map"><ViewTag code="D1" label="Regional transitions"/><D3ProvinceFlow features={provinces} edges={edges} width={760} height={165} selected={selectedProvince} onSelect={setSelectedProvince} visible={layers.paths}/></div></div>
        </article>
      </section>

      <aside className="iw-inspector">
        <section className="iw-panel linked-panel"><PanelTitle code="E" title="Active Selection" subtitle="SPATIAL CELL + ANNUAL CELL" accent="amber"/><div className="cell-head"><b>{selectedCell.slice(-3)}</b><span><strong>{selectedCell}</strong><small>{String(node?.is_boundary).toLowerCase()==='true'?'Boundary cell':'Interior cell'} · annual cell {selectedStateCell}</small></span></div><div className="value-strip"><span><small>{MONTHS[month]} PM₂.₅</small><b>{Number(monthly?.pm25??series[month]?.value??0).toFixed(1)}</b></span><span><small>STATE</small><b>{stateId}</b></span><span><small>DEGREE</small><b>{Number(node?.display_degree??0)}</b></span></div><div className="membership"><small>MEMBERSHIP</small>{['S1','S2','S3'].map(id=><i key={id} className={String(member?.[`in_${id}`]).toLowerCase()==='true'?'active':''}>{id}</i>)}<b>{String(member?.overlap_category||'outside').replaceAll('_',' ')}</b></div></section>

        <section className="iw-panel profile-panel"><PanelTitle code="F" title="Monthly Profile" subtitle="D3 CURVE · HOVER TO CHANGE MONTH" accent="teal"/><div className="profile-chart"><D3MonthlyProfile values={values} selected={month} onSelect={setMonth}/></div><div className="profile-foot"><span>YEAR LOW <b>{Math.min(...values).toFixed(1)}</b></span><span>YEAR HIGH <b>{Math.max(...values).toFixed(1)}</b></span></div></section>

        <section className="iw-panel province-panel"><PanelTitle code="G" title="Path Context" subtitle="PROVINCE + ACTIVE TRANSITION" accent="purple"/><div className="province-head"><span>{selectedProvince}</span><small>{REGIONS.find(row=>row[0]===selectedProvince)?.[1]||'Regional node'}</small></div><div className="path-steps">{reference.map((name,i)=><button key={name} className={`${i<=step?'reached':''} ${name===selectedProvince?'selected':''}`} onClick={()=>{setSelectedProvince(name);setStep(i)}}><span>0{i+1}</span><b>{name}</b><i/></button>)}</div><div className="path-status"><small>ACTIVE DATE</small><b>{labels[step]}</b><span>{edges.length} accumulated edges</span></div></section>
      </aside>
    </section>
  </main>;
}

function PanelTitle({code,title,subtitle,accent}:{code:string;title:string;subtitle:string;accent:'blue'|'teal'|'purple'|'amber'}){return <header className={`iw-panel-title ${accent}`}><b>{code}</b><span><strong>{title}</strong><small>{subtitle}</small></span></header>}
function ViewTag({code,label}:{code:string;label:string}){return <div className="iw-view-tag"><b>{code}</b><span>{label}</span></div>}
