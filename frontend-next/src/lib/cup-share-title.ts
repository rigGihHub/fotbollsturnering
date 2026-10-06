export function cupShareTitle(name?:string|null):string {
  const label=name?.replace(/\s+/g," ").trim();
  return label?`CupNavi - ${label}`:"CupNavi";
}
