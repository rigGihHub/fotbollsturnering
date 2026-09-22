export function playoffImportRules(rules: Record<string, unknown> = {}) {
  const result: { label: string; value: string }[] = [];
  const number = (key: string) => typeof rules[key] === "number" && Number.isFinite(rules[key]) && Number(rules[key]) >= 0 ? Number(rules[key]) : null;
  const halves = number("halves");
  const minutes = number("minutes_per_half");
  if (halves && minutes) result.push({label:"Matchtid",value:`${halves} × ${minutes} min`});
  else {
    if (halves) result.push({label:"Antal halvlekar",value:String(halves)});
    if (minutes) result.push({label:"Tid per halvlek",value:`${minutes} min`});
  }
  for (const [key,label] of [["halftime_minutes","Halvtidspaus"],["pitch_break_minutes","Paus mellan matcher"],["extra_time_minutes","Förlängning"]]) {
    const value = number(key);
    if (value !== null) result.push({label,value:`${value} min`});
  }
  if (typeof rules.tie_rule === "string" && rules.tie_rule.trim()) result.push({label:"Vid oavgjort",value:rules.tie_rule.trim()});
  return result;
}
