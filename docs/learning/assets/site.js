(()=>{'use strict';const q=document.querySelector('#search'),results=document.querySelector('#search-results'),menu=document.querySelector('#menu'),nav=document.querySelector('#chapters');menu.addEventListener('click',()=>{const open=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));});q.addEventListener('input',()=>{const words=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);results.replaceChildren();results.hidden=!words.length;if(!words.length)return;const matches=window.learningSearch.filter(x=>words.every(w=>(x.title+' '+x.text).toLowerCase().includes(w))).slice(0,20);const count=document.createElement('p');count.textContent=`找到 ${matches.length} 个章节（最多显示20章）`;results.append(count);for(const x of matches){const a=document.createElement('a');a.href=x.url;a.textContent=x.title;results.append(a);const p=document.createElement('p');const pos=x.text.toLowerCase().indexOf(words[0]);p.textContent=x.text.slice(Math.max(0,pos-45),pos+160).replace(/[#`|]/g,'');results.append(p);}});document.addEventListener('keydown',e=>{if(e.key==='Escape'){results.hidden=true;q.blur();}});})();

// A historical fragment inside a folded locator must become readable.
(() => {
  function revealFragment() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = id && document.getElementById(id);
    if (!target) return;
    for (let parent = target.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    target.scrollIntoView({block: 'start'});
  }
  window.addEventListener('hashchange', revealFragment);
  revealFragment();
})();
