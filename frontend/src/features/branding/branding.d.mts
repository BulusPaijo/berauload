export type Brand = {
 app_name:string;app_short_name:string;tagline:string;login_eyebrow:string;
 login_welcome:string;login_description:string;login_button_text:string;
 login_footnote:string;organization_name:string;footer_text:string;
 color_primary:string;color_accent:string;logo_version:number;favicon_version:number;
 has_logo:boolean;has_favicon:boolean;
};
export const BRAND_DEFAULTS:Readonly<Omit<Brand,'logo_version'|'favicon_version'|'has_logo'|'has_favicon'>>;
export const BRAND_FIELDS:readonly string[];
export const BRAND_LIMITS:Readonly<Record<string,number>>;
export const STORAGE_KEY:string;
export function normalizeBrand(data:Partial<Brand>|null|unknown):Brand;
export function readCachedBrand(storage:Storage|null|undefined):Brand;
export function cacheBrand(storage:Storage|null|undefined,value:Brand):boolean;
export function safeBrandSlug(input:string):string;
export function contrastWhite(color:string):number;
export function metadataFor(branding:Brand):{title:string;description:string;favicon:string;theme:string};
