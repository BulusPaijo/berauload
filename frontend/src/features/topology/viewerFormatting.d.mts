import type {TopologySeries} from './types';
export function formatMetric(value:number|null|undefined,decimals?:number):string;
export function hourLabel(hour:number):string;
export function dayStatus(status:string|null):string;
export function trendPoints(result:TopologySeries|null,metric:string):{jam:string;nilai:number|null}[];
