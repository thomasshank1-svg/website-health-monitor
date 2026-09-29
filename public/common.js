const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = n => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
let toastTimer;
function toast(message){ $('#status').textContent=message; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#status').textContent='',6500); }
async function api(path, data, method='POST'){
 const response=await fetch(path.startsWith('/api/') ? path : '/api/'+path, data===undefined ? {} : {method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const result=await response.json();if(!response.ok) throw new Error(result.error||'Request failed.');return result;
}
async function action(button, fn){button.disabled=true;try{await fn();}catch(e){toast(e.message);}finally{button.disabled=false;}}
