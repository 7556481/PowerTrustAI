/* Opt-in, current-origin local connection only. No logs, URL or remote keys. */
'use strict';
(() => {
 const KEY='powertrust.localConnection.v1';
 function create(getStorage=()=>window.localStorage){
  return {
   load(){try{const raw=getStorage().getItem(KEY);if(!raw)return null;const saved=JSON.parse(raw);if(saved.version!==1||typeof saved.token!=='string'||saved.token.length<32||/\s/.test(saved.token)){this.forget();return null;}return saved.token;}catch(_){this.forget();return null;}},
   save(value){try{if(typeof value!=='string'||value.length<32||/\s/.test(value))return false;getStorage().setItem(KEY,JSON.stringify({version:1,token:value}));return true;}catch(_){return false;}},
   forget(){try{getStorage().removeItem(KEY);return true;}catch(_){return false;}}
  };
 }
 window.PowerTrustConnectionMemory={create,KEY};
})();
