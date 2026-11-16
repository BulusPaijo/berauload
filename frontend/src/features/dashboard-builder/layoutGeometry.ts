/** Pure snap-to-grid math for pointer resizing (12 columns, four height steps). */
export function clamp(value:number,min:number,max:number){
  return Math.max(min,Math.min(max,value));
}
export function snapSize(width:number,height:number,deltaX:number,deltaY:number,
                         cellWidth:number,rowHeight:number){
  const cols=cellWidth>0?Math.round(deltaX/cellWidth):0;
  const rows=rowHeight>0?Math.round(deltaY/rowHeight):0;
  return {w:clamp(width+cols,3,12),h:clamp(height+rows,1,4)};
}
