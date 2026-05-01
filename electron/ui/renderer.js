const API='http://127.0.0.1:8765';
const $=id=>document.getElementById(id);
const log=(m)=>{$('logs').textContent += `[${new Date().toLocaleTimeString()}] ${m}\n`; $('logs').scrollTop=$('logs').scrollHeight;};
let conn={};
const setLoading=(v)=>['connectBtn','backupBtn','restoreBtn','pickBakBtn'].forEach(id=>$(id).disabled=v);

(function initTheme(){const t=localStorage.getItem('theme')||'dark';document.body.className=t;})();
$('themeBtn').onclick=()=>{const n=document.body.className==='dark'?'light':'dark';document.body.className=n;localStorage.setItem('theme',n);};
$('pickBakBtn').onclick=async()=>{const p=await window.bridge.pickBakFile(); if(p) $('bakPath').value=p;};

$('connectBtn').onclick=async()=>{try{setLoading(true);log('Conectando...');conn={server:$('server').value,username:$('user').value,password:$('pass').value,use_windows_auth:$('winAuth').checked};const r=await fetch(API+'/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(conn)});const d=await r.json();if(!r.ok) throw new Error(d.detail||'Error');$('dbSelect').innerHTML=d.databases.map(x=>`<option>${x}</option>`).join('');$('backupDir').value=d.default_backup_path;$('login').classList.add('hidden');$('main').classList.remove('hidden');log('Conexión exitosa');}catch(e){alert(e.message);log('Error: '+e.message);}finally{setLoading(false);}};

$('backupBtn').onclick=async()=>{try{setLoading(true);$('bar').style.width='35%';log('Iniciando backup + validación...');const payload={...conn,database_name:$('dbSelect').value,backup_directory:$('backupDir').value};const r=await fetch(API+'/backup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();$('bar').style.width='100%';log('Estado final: '+d.status);if(d.error_message) log(d.error_message);}catch(e){log('Error: '+e.message);}finally{setLoading(false);setTimeout(()=>$('bar').style.width='0%',500);}};

$('restoreBtn').onclick=async()=>{try{setLoading(true);$('bar').style.width='45%';log('Iniciando restauración...');const payload={...conn,backup_file:$('bakPath').value,target_database:$('targetDb').value||null,force:false};const r=await fetch(API+'/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();$('bar').style.width='100%';log('Restauración: '+d.status+' => '+d.sandbox_database);}catch(e){log('Error: '+e.message);}finally{setLoading(false);setTimeout(()=>$('bar').style.width='0%',500);}};
