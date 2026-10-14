export async function api<T>(path:string,init?:RequestInit):Promise<T>{
  const response=await fetch(path,{...init,credentials:'same-origin',cache:'no-store'});
  if(!response.ok){let message=`Le serveur répond ${response.status}.`;try{const body=await response.json();message=typeof body.error==='string'?body.error:typeof body.detail==='string'?body.detail:message;}catch{/* Non-JSON error */}throw new ApiError(message,response.status);}
  return response.json() as Promise<T>;
}
export class ApiError extends Error {status:number;constructor(message:string,status:number){super(message);this.status=status;}}
export function download(name:string,value:string,type='application/json'){const a=document.createElement('a');const url=URL.createObjectURL(new Blob([value],{type}));a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
