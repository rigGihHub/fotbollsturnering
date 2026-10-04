"use client";
import { Dispatch, SetStateAction, useCallback, useEffect, useRef, useState } from 'react';
import { ADMIN_DRAFT_PREFIX, readAdminDraft, writeAdminDraft } from './admin-draft';

export function useUnsavedWork(dirty:boolean) {
  useEffect(()=>{
    if(!dirty)return;
    const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',guard);
    return()=>window.removeEventListener('beforeunload',guard);
  },[dirty]);
}

export function usePendingAdminDrafts() {
  const [pending,setPending]=useState(false);
  useEffect(()=>{
    const sync=()=>{
      try {setPending(Object.keys(sessionStorage).some(key=>{
        if(!key.startsWith(ADMIN_DRAFT_PREFIX))return false;
        const draft=JSON.parse(sessionStorage.getItem(key)||'null');
        return draft&&Date.now()-draft.updatedAt<24*60*60*1000;
      }));} catch {}
    };
    sync();window.addEventListener('cupnavi:admin-draft-updated',sync);
    return()=>window.removeEventListener('cupnavi:admin-draft-updated',sync);
  },[]);
  useUnsavedWork(pending);
}

/** Drafts survive step unmounts. Only server-confirmed saves clear a draft. */
export function useAdminDraft<T extends object>(key:string) {
  const [data,updateData]=useState<T|null>(null);
  const [saved,updateSaved]=useState<T|null>(null);
  const dataRef=useRef<T|null>(null);
  const savedRef=useRef<T|null>(null);
  const accept=useCallback((server:T,restore=false)=>{
    const next=restore?readAdminDraft(key,server):server;
    savedRef.current=server;dataRef.current=next;
    updateSaved(server);updateData(next);
    writeAdminDraft(key,server,next);
  },[key]);
  const setData:Dispatch<SetStateAction<T|null>>=useCallback(action=>{
    const next=typeof action==='function'?action(dataRef.current):action;
    dataRef.current=next;updateData(next);
    if(next&&savedRef.current)writeAdminDraft(key,savedRef.current,next);
  },[key]);
  const dirty=Boolean(data&&saved&&JSON.stringify(data)!==JSON.stringify(saved));
  useUnsavedWork(dirty);
  const discard=useCallback(()=>{
    try {sessionStorage.removeItem(ADMIN_DRAFT_PREFIX+key);}catch{}
    if(savedRef.current)accept(savedRef.current);
  },[key,accept]);
  return {data,setData,saved,accept,dirty,discard};
}
