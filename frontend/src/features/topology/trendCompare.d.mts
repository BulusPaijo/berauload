import type {TopologySeries} from './types';
export function comparisonAllowed(codes:string[],units:Record<string,string>):boolean;
export function combinedTrendPoints(series:TopologySeries|null,codes:string[]):Array<{jam:string;[code:string]:string|number|null}>;
