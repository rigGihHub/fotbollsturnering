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
