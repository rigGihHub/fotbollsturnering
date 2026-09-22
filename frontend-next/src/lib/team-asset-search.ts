export type KitMode = "none" | "home" | "both";
export type AssetSuggestion = {
  identity_status:string; home_verified:boolean; away_verified:boolean; logo_verified:boolean;
  home_color_1:string; home_color_2:string; home_pattern:string;
  away_color_1:string; away_color_2:string; away_pattern:string;
  logo_url:string; logo_source_url:string; reason?:string;
};
type Patch = Record<string,string>;
type SearchOptions = {
  kitMode:KitMode; showLogos:boolean; existingLogo?:string|null;
  lookup:(focus:"kit"|"logo",kitMode:"home"|"both")=>Promise<AssetSuggestion>;
  save:(patch:Patch)=>Promise<void>;
};

// Save independent verified parts. A missing crest must never redirect a shirt
// search or discard a verified shirt, and unverified defaults never overwrite data.
export async function searchAndSaveTeamAssets(options:SearchOptions){
  const {kitMode,showLogos,existingLogo,lookup,save}=options;
  const issues:string[]=[];
  let updated=false, failed=false, stop=false;
  const focuses:Array<"kit"|"logo">=[];
  if(kitMode!=="none")focuses.push("kit");
  if(showLogos&&!existingLogo)focuses.push("logo");
  for(const focus of focuses){
    try{
      const result=await lookup(focus,kitMode==="home"?"home":"both");
      if(result.identity_status!=="exact"){
        issues.push(`${focus==="kit"?"Matchställ":"Klubbmärke"}: klubbidentiteten behöver förtydligas.`);
        continue;
      }
      const patch:Patch={};
      if(focus==="kit"){
        if(result.home_verified)Object.assign(patch,{primary_color:result.home_color_1,home_color_2:result.home_color_2,home_pattern:result.home_pattern});
        else issues.push("Hemma: behöver kontrolleras.");
        if(kitMode==="both"){
          if(result.away_verified)Object.assign(patch,{secondary_color:result.away_color_1,away_color_2:result.away_color_2,away_pattern:result.away_pattern});
          else issues.push("Borta: behöver kontrolleras.");
        }
      }else{
        if(result.logo_verified&&result.logo_url)Object.assign(patch,{logo_url:result.logo_url,logo_source_url:result.logo_source_url});
        else issues.push("Klubbmärke: ingen verifierad bild hittades.");
      }
      if(Object.keys(patch).length){await save(patch);updated=true;}
      else if(result.reason)issues.push(result.reason);
    }catch(error){
      const detail=error instanceof Error?error.message:String(error);
      failed=true;
      issues.push(`${focus==="kit"?"Matchställ":"Klubbmärke"}: ${detail}`);
      if(/429|AI_RATE_LIMIT|kapacitetsgräns/i.test(detail)){stop=true;break;}
    }
  }
  return {updated,failed,stop,issues,skipped:focuses.length===0};
}
