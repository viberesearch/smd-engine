
const s=[...document.querySelectorAll('section')],c=document.getElementById('count');
const hid=document.getElementById('hid'),D=JSON.parse(document.getElementById('smd-data').textContent);
let i=Math.max(0,s.findIndex(x=>'#'+x.id===location.hash));
function count(){const n=+(s[i].dataset.hidden||0);hid.textContent=n?hid.dataset.word+': '+n:''}
function go(n){i=Math.min(s.length-1,Math.max(0,n));s.forEach((x,k)=>x.classList.toggle('on',k===i));
c.textContent=(i+1)+' / '+s.length;history.replaceState(null,'','#'+s[i].id);window.scrollTo(0,0);count();}
window.addEventListener('hashchange',()=>{const k=s.findIndex(x=>'#'+x.id===location.hash);if(k>=0)go(k)});
const t=document.getElementById('toggle');
function quiet(q){document.body.classList.toggle('quiet',q);t.setAttribute('aria-pressed',String(!q));
try{localStorage.setItem('smd-quiet',q?'1':'0')}catch(e){}}
let q0=false;try{q0=localStorage.getItem('smd-quiet')==='1'}catch(e){}
quiet(q0);t.onclick=()=>quiet(!document.body.classList.contains('quiet'));
const L=[...document.querySelectorAll('button.layer')];let off=new Set();
try{off=new Set(JSON.parse(localStorage.getItem('smd-off')||'[]'))}catch(e){}
function gone(g){const o=g.dataset.origin,k=g.dataset.kind;return(off.has('ai')&&o==='ai')||
(off.has('clean-room')&&o==='clean-room')||(off.has('function')&&k==='function')||
(off.has('places')&&(k==='place_for_others'||k==='gap'))}
function show(g,on){g.style.display=on?'':'none'}
function layers(){L.forEach(b=>b.setAttribute('aria-pressed',String(!off.has(b.dataset.layer))));
s.forEach(x=>{const h=new Set();x.querySelectorAll('g.el').forEach(g=>{const o=gone(g);show(g,!o);if(o)h.add(g.dataset.id)});
x.querySelectorAll('g.rel').forEach(g=>show(g,!h.has(g.dataset.from)&&!h.has(g.dataset.to)));
x.querySelectorAll('g.tr').forEach(g=>show(g,!off.has('transitions')&&!h.has(g.dataset.from)&&!h.has(g.dataset.to)));
x.querySelectorAll('g.k').forEach(g=>show(g,!off.has('k')&&!h.has(g.dataset.target)));
x.dataset.hidden=h.size});count();try{localStorage.setItem('smd-off',JSON.stringify([...off]))}catch(e){}}
L.forEach(b=>b.onclick=()=>{const l=b.dataset.layer;off.has(l)?off.delete(l):off.add(l);layers()});
const P=document.getElementById('detail'),B=document.getElementById('dbody');
function e(x){const d=document.createElement('div');d.textContent=x;return d.innerHTML}
function list(a){return a&&a.length?'<ul>'+a.map(x=>'<li>'+e(x)+'</li>').join('')+'</ul>':''}
function grid(t){if(!t)return'';const r=(c,x)=>'<tr>'+x.map(v=>'<'+c+'>'+e(v)+'</'+c+'>').join('')+'</tr>';
return(t.title?'<p><b>'+e(t.title)+'</b></p>':'')+'<table>'+r('th',t.columns)+t.rows.map(x=>r('td',x)).join('')+'</table>'}
document.querySelector('main').addEventListener('click',ev=>{const g=ev.target.closest('g.el,g.k');if(!g)return;
const r=D[g.closest('section').dataset.record];let h;
if(g.matches('g.k')){h='<p>'+e(r.k[g.dataset.k]||g.dataset.k)+'</p>'}
else{const d=r.el[g.dataset.id];if(!d)return;h='<p class="meta">'+e(d.meta)+'</p><p><b>'+e(d.label)+'</b></p>'+
(d.note?'<p>'+e(d.note)+'</p>':'')+(d.fillers?'<p>'+e(P.dataset.fillers)+': '+e(d.fillers)+'</p>':'')+
grid(d.detail)+list(d.folded)+list(d.k)+(d.cites?'<p class="meta">'+e(d.cites)+'</p>':'')}
B.innerHTML=h;P.hidden=false});
document.getElementById('close').onclick=()=>{P.hidden=true};
document.getElementById('prev').onclick=()=>go(i-1);
document.getElementById('next').onclick=()=>go(i+1);
document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();go(i+1)}
else if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(i-1)}
else if(e.key==='Escape'){P.hidden=true}
else if(e.key==='t'||e.key==='T'){quiet(!document.body.classList.contains('quiet'))}});
layers();go(i);
