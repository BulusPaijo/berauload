export const TEXT:string[];export const NUMBER:string[];export const OPTIONAL_NUMBER:string[];
export function formFromRow(blank:Record<string,string>,row:object):Record<string,string>;
export function editableBody(form:Record<string,string>,creating:boolean,withUnit:boolean):Record<string,unknown>;
