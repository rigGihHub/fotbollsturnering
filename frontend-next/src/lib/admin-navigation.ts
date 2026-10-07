export const adminPhases=[
 {id:'create',label:'Skapa',step:'cupinfo'},
 {id:'plan',label:'Planera',step:'venues'},
 {id:'publish',label:'Publicera',step:'publish'},
 {id:'run',label:'Genomföra',step:'reporting'},
] as const;
export function adminPhase(step:string):string {
 if(['overview','cupinfo','teams','groups'].includes(step))return 'create';
 if(['venues','rules','schedule','playoffs','import'].includes(step))return 'plan';
 if(step==='publish')return 'publish';
 return 'run';
}
export const adminFlowSteps = [
 ['overview','Översikt'], ['cupinfo','Cupinfo'], ['teams','Lag'], ['groups','Grupper'],
 ['venues','Planer & tider'], ['rules','Regler'], ['schedule','Schema'],
 ['playoffs','Slutspel'], ['publish','Kontroll & publicering'],
] as const;
export const adminToolSteps = [
 ['partners','Sponsorer & erbjudanden'], ['access','Lokal admin'], ['referees','Domare'],
 ['reporting','Matchrapportering'], ['analytics','Statistik'], ['import','Uppdatera med ny PDF'], ['export','PDF & export'],
] as const;
export type AdminStep = (typeof adminFlowSteps)[number][0] | (typeof adminToolSteps)[number][0];
export function parseAdminStep(hash:string):AdminStep {
 const value=hash.replace(/^#/, '');
 return [...adminFlowSteps,...adminToolSteps].some(([id])=>id===value)?value as AdminStep:'overview';
}
