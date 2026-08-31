'use client';

import { useEffect, useMemo, useState } from 'react';
import './integrated-workbench.css';
import {
  D3EgoComparison,D3MonthlyProfile,D3PartitionMap,D3ProvinceFlow,
  type EdgeStatus,type FlowEdge,type GeoFeature,
} from './d3-views';

const API=process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8000';
const MONTHS=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
const DATASETS=[
  {id:'湖北',name:'Hubei',slug:'hubei',group:'CEG PM₂.₅'},
  {id:'湖南',name:'Hunan',slug:'hunan',group:'CEG PM₂.₅'},
  {id:'江西',name:'Jiangxi',slug:'jiangxi',group:'CEG PM₂.₅'},
  {id:'广东',name:'Guangdong',slug:'guangdong',group:'CEG PM₂.₅'},
  {id:'福建',name:'Fujian',slug:'fujian',group:'CEG PM₂.₅'},
  {id:'广西',name:'Guangxi',slug:'guangxi',group:'CEG PM₂.₅'},
  {id:'安徽',name:'Anhui',slug:'anhui',group:'CEG PM₂.₅'},
  {id:'浙江',name:'Zhejiang',slug:'zhejiang',group:'CEG PM₂.₅'},
  {id:'NCEP-AirTemp-Africa-2000',name:'NCEP Africa',slug:'ncep-africa',group:'Climate grid'},
  {id:'NE-Admin0-Africa',name:'Natural Earth Africa',slug:'natural-earth-africa',group:'Irregular regions'},
  {id:'NASA-Exoplanet-SkyGrid',name:'NASA Exoplanet',slug:'nasa-exoplanet',group:'Astronomy'},
] as const;

type Lens='topology'|'states'|'flow';
type Representation='reference'|'disk'|'annulus';
type ColorMode='scalar'|'fidelity'|'boundary';
type Row=Record<string,string|number|boolean|null>;
type WorkbenchData={
  dataset:string;label:string;unit:string;view:'disk'|'annulus';method:string;
  original:{features:GeoFeature[]};display:{features:GeoFeature[]};reference_edges:string[][];display_edges:string[][];
  nodes:Row[];temporal:Row[];cells:Row[];metadata:Record<string,unknown>;
};
type AnnualData={annulus:{features:GeoFeature[]};state_intervals:Row[];monthly_summary:Row[];monthly_values:Row[];frequency:Row[];membership:Row[]};
type LegacyData={annual_states:AnnualData;migration_paths:{provinces:{features:GeoFeature[]};case:Record<string,unknown>}};

const normalizedEdge=(edge:string[])=>[...edge].sort().join('\u0000');

export default function IntegratedWorkbench(){
  const [dataset,setDataset]=useState('湖北');
  const [representation,setRepresentation]=useState<Representation>('disk');
  const view=representation==='annulus'?'annulus':'disk';
  const [lens,setLens]=useState<Lens>('topology');
  const [colorMode,setColorMode]=useState<ColorMode>('scalar');
  const [stateId,setStateId]=useState('S2');
  const [month,setMonth]=useState(7);
  const [step,setStep]=useState(2);
  const [selectedCell,setSelectedCell]=useState('');
  const [selectedStateCell,setSelectedStateCell]=useState('1');
  const [selectedProvince,setSelectedProvince]=useState('湖北');
  const [showNeighbors,setShowNeighbors]=useState(true);
  const [paramsOpen,setParamsOpen]=useState(false);
  const [neighborModel,setNeighborModel]=useState<'4'|'8'>('4');
  const [toleranceIndex,setToleranceIndex]=useState(2);
  const [layers,setLayers]=useState(6);
  const [areaPenalty,setAreaPenalty]=useState(.035);
  const [weightedEdges,setWeightedEdges]=useState(true);
  const [workbench,setWorkbench]=useState<WorkbenchData|null>(null);
  const [legacy,setLegacy]=useState<LegacyData|null>(null);
  const [online,setOnline]=useState(false);

  useEffect(()=>{
    let active=true;const entry=DATASETS.find(item=>item.id===dataset)??DATASETS[0];
    fetch(`${API}/api/workbench?dataset=${encodeURIComponent(dataset)}&view=${view}`)
      .then(response=>{if(!response.ok)throw new Error();return response.json()})
      .then(data=>{if(active){setWorkbench(data);setOnline(true);setSelectedCell(String(data.display?.features?.[0]?.properties?.cell_id??''));}})
      .catch(()=>fetch(`/data/workbench-${entry.slug}-${view}.json`).then(response=>response.json()).then(data=>{if(active){setWorkbench(data);setOnline(false);setSelectedCell(String(data.display?.features?.[0]?.properties?.cell_id??''));}}).catch(()=>{if(active)setWorkbench(null)}));
    return()=>{active=false};
  },[dataset,view]);

  useEffect(()=>{
    fetch(`${API}/api/legacy-insights`).then(response=>{if(!response.ok)throw new Error();return response.json()}).then(setLegacy)
      .catch(()=>fetch('/data/legacy-insights.json').then(response=>response.json()).then(setLegacy).catch(()=>setLegacy(null)));
  },[]);

  const original=useMemo(()=>workbench?.original.features||[],[workbench]);
  const spatial=useMemo(()=>workbench?.display.features||[],[workbench]);
  const annual=useMemo(()=>legacy?.annual_states.annulus.features||[],[legacy]);
  const provinces=useMemo(()=>legacy?.migration_paths.provinces.features||[],[legacy]);
  const nodes=useMemo(()=>new Map((workbench?.nodes||[]).map(row=>[String(row.cell_id),row])),[workbench]);
  const cells=useMemo(()=>new Map((workbench?.cells||[]).map(row=>[String(row.cell_id),row])),[workbench]);
  const boundaryCells=useMemo(()=>new Set((workbench?.nodes||[]).filter(row=>String(row.is_boundary).toLowerCase()==='true').map(row=>String(row.cell_id))),[workbench]);
  const node=nodes.get(selectedCell);

  const referenceEdges=useMemo(()=>workbench?.reference_edges||[],[workbench]);
  const displayEdges=useMemo(()=>workbench?.display_edges||[],[workbench]);
  const edgeStatus=useMemo<EdgeStatus[]>(()=>{
    const reference=new Set(referenceEdges.map(normalizedEdge));const display=new Set(displayEdges.map(normalizedEdge));
    const all=new Set([...reference,...display]);
    return [...all].map(key=>{const [source,target]=key.split('\u0000');return {source,target,status:reference.has(key)&&display.has(key)?'preserved':reference.has(key)?'lost':'new'};});
  },[referenceEdges,displayEdges]);

  const temporalRows=useMemo(()=>workbench?.temporal||[],[workbench]);
  const series=useMemo(()=>temporalRows.filter(row=>String(row.cell_id)===selectedCell).sort((a,b)=>Number(a.month)-Number(b.month)),[temporalRows,selectedCell]);
  const scalarValues=useMemo(()=>{
    const map=new Map<string,number>();
    for(const [id,row] of cells){
      const temporal=temporalRows.find(item=>String(item.cell_id)===id&&Number(item.month)===month+1);
      const value=Number(temporal?.value??row[`month_${String(month+1).padStart(2,'0')}_pm25`]??row.annual_mean_pm25??0);
      map.set(id,Number.isFinite(value)?value:0);
    }
    return map;
  },[cells,temporalRows,month]);
  const fidelityValues=useMemo(()=>new Map([...nodes].map(([id,row])=>[id,Number(row.node_adj_f1??0)])),[nodes]);
  const mapValues=colorMode==='fidelity'?fidelityValues:scalarValues;

  const annualData=legacy?.annual_states;
  const membership=useMemo(()=>new Map((annualData?.membership||[]).map(row=>[String(row.cell_id),row])),[annualData]);
  const stateSeries=(annualData?.monthly_values||[]).filter(row=>String(row.cell_id)===selectedStateCell).sort((a,b)=>Number(a.month)-Number(b.month));
  const stateValues=stateSeries.map(row=>Number(row.pm25));
  const monthlyValues=series.length?series.map(row=>Number(row.value)):stateValues.length?stateValues:[62,57,59,52,50,52,48,43,42,51,79,74];
  const selectedValue=scalarValues.get(selectedCell)??monthlyValues[month]??0;

  const caseData=(legacy?.migration_paths.case||{}) as Record<string,unknown>;
  const labels=(caseData.labels||['2000-01-10','2000-01-11','2000-01-12','2000-01-13']) as string[];
  const pathSequence=(caseData.reference_sequence||['湖北','安徽','江西','福建']) as string[];
  const flowEdges=((caseData.regional_edges||[]) as Array<Record<string,unknown>>).filter(edge=>Number(edge.step)<=step+1).map(edge=>({source:String(edge.source),target:String(edge.target),support:Number(edge.support||1),transition_score:Number(edge.transition_score||0)} satisfies FlowEdge));

  const currentDataset=DATASETS.find(item=>item.id===dataset)??DATASETS[0];
  const mainTitle=lens==='topology'?(representation==='reference'?'Geographic reference':workbench?.method||'Final Power partition'):lens==='states'?`${stateId} annual pollution state`:'Regional transition field';
  const mainSubtitle=lens==='topology'?`${workbench?.label||currentDataset.name} · ${MONTHS[month]} · ${colorMode}`:lens==='states'?'Fixed annual geometry · linked month and state selection':`${labels[step]} · directional gateway evidence`;
  const toleranceValues=['1e-6','5e-6','2e-5','1e-4','5e-4'];

  function chooseProvince(name:string){
    setSelectedProvince(name);
    if(DATASETS.some(item=>item.id===name)){setDataset(name);setLens('topology');setRepresentation('disk');}
  }
  function chooseState(id:string){
    setStateId(id);setLens('states');
    const first=annual.find(feature=>{const featureId=String(feature.properties.cell_id??feature.properties.name??'');return String(membership.get(featureId)?.[`in_${id}`]).toLowerCase()==='true'});
    if(first)setSelectedStateCell(String(first.properties.cell_id??first.properties.name??''));
  }

  return <main className="va-shell">
    <header className="va-header">
      <div className="va-brand"><b>GΔ</b><span><strong>GeoDisk Lab</strong><small>TOPOLOGY-AWARE VISUAL ANALYTICS</small></span></div>
      <nav className="va-story" aria-label="Analysis workflow"><span className="active">A <b>Context</b></span><i/>
        <span>B <b>Transform</b></span><i/><span>C <b>State</b></span><i/><span>D <b>Diagnose</b></span></nav>
      <div className="va-status"><i className={online?'online':''}/><span>{online?'LIVE BACKEND':'REPRODUCIBLE SNAPSHOT'}</span><b>D3 7.9</b></div>
    </header>

    <section className="va-workspace">
      <aside className="va-left">
        <PanelHead code="A" title="Global context" subtitle="Select a region to enter the analysis"/>
        <div className="context-map"><D3ProvinceFlow features={provinces} edges={flowEdges} width={270} height={290} selected={selectedProvince} onSelect={chooseProvince} visible={lens==='flow'} quiet={false}/></div>
        <label className="field-label">DATASET
          <select value={dataset} onChange={event=>{const id=event.target.value;setDataset(id);if(DATASETS.some(item=>item.id===id&&item.group==='CEG PM₂.₅'))setSelectedProvince(id)}}>
            {DATASETS.map(item=><option key={item.id} value={item.id}>{item.name} · {item.group}</option>)}
          </select>
        </label>
        <div className="control-block">
          <span className="control-label">ANALYSIS LENS</span>
          <div className="lens-switch">{([['topology','Topology'],['states','States'],['flow','Flow']] as const).map(([id,label])=><button key={id} className={lens===id?'active':''} onClick={()=>setLens(id)}>{label}</button>)}</div>
        </div>
        <div className="control-grid">
          <label><span>COLOR ENCODING</span><select value={colorMode} onChange={event=>setColorMode(event.target.value as ColorMode)}><option value="scalar">Scalar value</option><option value="fidelity">Node fidelity</option><option value="boundary">Boundary / interior</option></select></label>
          <label><span>MONTH <b>{MONTHS[month]}</b></span><input type="range" min="0" max="11" value={month} onChange={event=>setMonth(Number(event.target.value))}/></label>
        </div>
        <label className="check-row"><input type="checkbox" checked={showNeighbors} onChange={event=>setShowNeighbors(event.target.checked)}/><span>Reveal selected-cell adjacency</span></label>
        <button className="parameter-button" onClick={()=>setParamsOpen(true)}><span>Experiment parameters</span><b>{neighborModel}-N · ε {toleranceValues[toleranceIndex]}</b></button>
      </aside>

      <section className="va-center">
        <article className="main-view">
          <header className="main-toolbar">
            <div><small>B · PRIMARY VIEW</small><strong>{mainTitle}</strong><span>{mainSubtitle}</span></div>
            <div className="representation-switch" aria-label="Representation">
              {([['reference','Map'],['disk','Disk'],['annulus','Annulus']] as const).map(([id,label])=><button key={id} className={representation===id?'active':''} onClick={()=>{setRepresentation(id);setLens('topology')}}>{label}</button>)}
            </div>
          </header>
          <div className="main-stage">
            {lens==='topology'&&<>
              <D3PartitionMap features={representation==='reference'?original:spatial} width={800} height={480} selected={selectedCell} onSelect={setSelectedCell} mode={representation==='reference'?'reference':'spatial'} values={mapValues} colorMode={colorMode} boundaryCells={boundaryCells} edgeStatus={edgeStatus} showNeighbors={showNeighbors}/>
              {representation!=='reference'&&<button className="reference-inset" onClick={()=>setRepresentation('reference')} aria-label="Open geographic reference"><span>REFERENCE</span><D3PartitionMap features={original} width={150} height={110} selected={selectedCell} onSelect={setSelectedCell} mode="reference" boundaryCells={boundaryCells} compact/></button>}
              <div className="main-legend"><span><i className="blue"/>preserved</span><span><i className="coral"/>lost</span><span><i className="mint"/>new</span><em>scroll to zoom · drag to pan · click to select</em></div>
            </>}
            {lens==='states'&&<><D3PartitionMap features={annual} width={800} height={480} selected={selectedStateCell} onSelect={setSelectedStateCell} mode="annual" membership={membership} stateId={stateId}/><div className="main-legend state"><span><i className="state-core"/>all 3 states</span><span><i className="mint"/>shared</span><span><i className="mint-light"/>specific</span><em>click any state cell to inspect its annual profile</em></div></>}
            {lens==='flow'&&<><D3ProvinceFlow features={provinces} edges={flowEdges} width={800} height={480} selected={selectedProvince} onSelect={chooseProvince}/><div className="main-legend flow"><span><i className="coral"/>active transition</span><em>flow width encodes support · opacity encodes transition score</em></div></>}
          </div>
        </article>

        <section className="evidence-row">
          <article className="state-multiples">
            <PanelHead code="C" title="Annual state motifs" subtitle="Click a small multiple to promote it"/>
            <div className="state-glyph-row">{['S1','S2','S3'].map(id=><button key={id} className={stateId===id?'active':''} onClick={()=>chooseState(id)}><span><b>{id}</b><small>{id==='S1'?'JAN–MAR':id==='S2'?'APR–SEP':'OCT–DEC'}</small></span><D3PartitionMap features={annual} width={150} height={115} selected={selectedStateCell} onSelect={setSelectedStateCell} mode="annual" membership={membership} stateId={id} compact/></button>)}</div>
          </article>
          <article className="temporal-profile">
            <PanelHead code="C2" title="Temporal evidence" subtitle="Click the profile to coordinate month"/>
            <div className="profile-wrap"><D3MonthlyProfile values={monthlyValues} selected={month} onSelect={setMonth} width={500} height={142}/></div>
          </article>
        </section>
      </section>

      <aside className="va-right">
        <section className="relation-view">
          <PanelHead code="D" title="Relation diagnosis" subtitle="Reference versus final Power neighbors"/>
          <div className="selection-line"><span><b>{selectedCell.slice(-8)||'—'}</b><small>{String(node?.is_boundary).toLowerCase()==='true'?'BOUNDARY CELL':'INTERIOR CELL'}</small></span><em>{selectedValue.toFixed(1)} {workbench?.unit||''}</em></div>
          <D3EgoComparison referenceEdges={referenceEdges} displayEdges={displayEdges} selected={selectedCell}/>
          <div className="relation-legend"><span><i className="blue"/>preserved</span><span><i className="coral"/>lost</span><span><i className="mint"/>new</span></div>
          <div className="diagnostic-sentence">Node F1 <b>{Number(node?.node_adj_f1??0).toFixed(2)}</b><i/>
            direction error <b>{Number(node?.node_direction_error_deg??0).toFixed(1)}°</b><i/>order accuracy <b>{Number(node?.node_neighbor_order_accuracy??0).toFixed(2)}</b></div>
        </section>

        <section className="path-view">
          <PanelHead code="D2" title="Path evidence" subtitle="Four-day reference sequence"/>
          <div className="path-date"><b>{labels[step]}</b><span>STEP 0{step+1}</span></div>
          <div className="path-sequence">{pathSequence.map((name,index)=><button key={`${name}-${index}`} className={`${index<=step?'reached':''} ${name===selectedProvince?'selected':''}`} onClick={()=>{setStep(index);setSelectedProvince(name);setLens('flow')}}><small>0{index+1}</small><b>{name}</b>{index<pathSequence.length-1&&<i>→</i>}</button>)}</div>
          <div className="path-explanation"><span>Current evidence</span><p>{flowEdges.length} directed regional links are visible for this case window. Select a province or step to trace the supporting route.</p></div>
        </section>
      </aside>
    </section>

    {paramsOpen&&<div className="drawer-backdrop" onClick={()=>setParamsOpen(false)}><aside className="parameter-drawer" onClick={event=>event.stopPropagation()}>
      <header><div><small>EXPERIMENT CONFIGURATION</small><h2>Parameter laboratory</h2><p>Visual controls update immediately. Geometry controls define the next reproducible backend rerun.</p></div><button onClick={()=>setParamsOpen(false)} aria-label="Close parameter panel">×</button></header>
      <section><h3>Reference topology</h3><label><span>Neighborhood model</span><div className="drawer-segment"><button className={neighborModel==='4'?'active':''} onClick={()=>setNeighborModel('4')}>4-neighbor</button><button className={neighborModel==='8'?'active':''} onClick={()=>setNeighborModel('8')}>8-neighbor</button></div></label><label><span>Contact tolerance <b>ε = {toleranceValues[toleranceIndex]}</b></span><input type="range" min="0" max="4" value={toleranceIndex} onChange={event=>setToleranceIndex(Number(event.target.value))}/><small>Declared sensitivity range: 1e-6 → 5e-4</small></label><label className="drawer-check"><input type="checkbox" checked={weightedEdges} onChange={event=>setWeightedEdges(event.target.checked)}/><span>Shared-boundary-length weighting</span></label></section>
      <section><h3>Final Power refinement</h3><label><span>Radial layers <b>{layers}</b></span><input type="range" min="4" max="6" value={layers} onChange={event=>setLayers(Number(event.target.value))}/></label><label><span>Area-CV penalty <b>{areaPenalty.toFixed(3)}</b></span><input type="range" min="0" max="0.1" step="0.005" value={areaPenalty} onChange={event=>setAreaPenalty(Number(event.target.value))}/></label><div className="objective-preview"><span>Candidate objective</span><code>F1 + 0.18 NP@2 − direction − angle − radial − {areaPenalty.toFixed(3)} CV</code></div></section>
      <section className="drawer-note"><h3>Recommended next run</h3><p>Report {neighborModel}-neighbor results at ε={toleranceValues[toleranceIndex]}, with {layers} radial layers and {weightedEdges?'weighted':'binary'} adjacency. Keep the current fixed candidate schedule for every dataset.</p></section>
    </aside></div>}
  </main>;
}

function PanelHead({code,title,subtitle}:{code:string;title:string;subtitle:string}){return <header className="panel-head"><b>{code}</b><span><strong>{title}</strong><small>{subtitle}</small></span></header>}
