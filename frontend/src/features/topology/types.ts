/** Topology read-only transport types. Values never live inside a saved layout. */
export type SymbolType = 'generator'|'incoming'|'busbar'|'breaker'|'transformer'|'feeder'|'load'|'capacitor';
export type BoxKind = 'metric'|'summary'|'ranking'|'legend'|'text';
export type WireLevel = '20kv'|'unspecified';
export type RuleStatus = 'normal'|'warning'|'critical'|null;

export type TopologySymbol = {
  id:string;type:SymbolType;x:number;y:number;w:number;h:number;
  asset_code:string|null;label:string;rotation:0|90|180|270;
  link?:{unit_id:number;diagram_id:number};
};
export type TopologyWire = {id:string;points:[number,number][];level:WireLevel};
export type TopologyBox = {
  id:string;kind:BoxKind;x:number;y:number;w:number;title:string;
  asset_code:string|null;metric_codes:string[];decimals:number;
  show_unit:boolean;leader:boolean;sparkline:boolean;locked:boolean;
  rule_id:number|null;anchor_symbol_id:string|null;
};
export type TopologyArea = {
  id:string;x:number;y:number;w:number;h:number;title:string;
  border:'solid'|'dashed'|'dotted';color:'teal'|'blue'|'amber'|'green'|'red'|'gray';
  opacity:number;locked:boolean;
};
export type TopologyLayout = {
  canvas:{w:number;h:number;grid:number};
  symbols:TopologySymbol[];wires:TopologyWire[];boxes:TopologyBox[];areas?:TopologyArea[];
};
export type TopologyDiagram = {
  id:number;name:string;description:string;layout:TopologyLayout;
  version:number;archived:boolean;updated_by:number|null;
  updated_at:string;created_at:string;
};
export type TopologyHour = {
  source_status?:import('../unit-references/SourceStatus').Status;
  day:string;hour:number;day_status:string;
  values:Record<string,number|null>;
  units:Record<string,string>;
  rules:Record<string,RuleStatus>;
};
export type TopologySeries = {
  source_status?:import('../unit-references/SourceStatus').Status;
  day:string;day_status:string;units:Record<string,string>;
  series:Record<string,{hour:number;value:number|null}[]>;
};
export type TopologyRevision={version:number;snapshot:{name:string;description:string;layout:TopologyLayout};updated_by:number|null;created_at:string};
export type TopologyRule={id:number;name:string;code:string;status:'draft'|'active'|'archived'};

export type DiagramUnit={unit_id:number;unit_code:string;unit_name:string;level:string;diagrams:{id:number;name:string}[]};
