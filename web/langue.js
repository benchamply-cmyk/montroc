/* La langue dépend uniquement de l'URL : aucun stockage ni service de traduction tiers. */
(()=>{
  const languages={
    fr:{prefix:'',label:'Français'},
    en:{prefix:'/english',label:'English'},
    es:{prefix:'/espanol',label:'Español'}
  };
  const lang=document.documentElement.lang in languages?document.documentElement.lang:'fr';
  const prefix=languages[lang].prefix;
  const messages=window.TT_MESSAGES||{};
  const t=value=>messages[value]??value;
  const nouns={
    fr:{objet:['objet','objets'],demande:['demande','demandes'],echange:['échange','échanges'],boucle:['boucle','boucles'],depot:['dépôt','dépôts'],match:['match','matchs']},
    en:{objet:['item','items'],demande:['request','requests'],echange:['swap','swaps'],boucle:['loop','loops'],depot:['drop-off','drop-offs'],match:['match','matches']},
    es:{objet:['objeto','objetos'],demande:['solicitud','solicitudes'],echange:['intercambio','intercambios'],boucle:['cadena','cadenas'],depot:['entrega','entregas'],match:['match','matches']}
  };
  const count=(n,key)=>`${n} ${nouns[lang][key][(lang==='fr'?n>1:n!==1)?1:0]}`;
  const pending=n=>lang==='en'?`${count(n,'echange')} awaiting your reply`:lang==='es'?`${count(n,'echange')} esperando tu respuesta`:`${count(n,'echange')} attend${n>1?'ent':''} votre réponse`;
  const completed=n=>lang==='en'?`${count(n,'echange')} completed`:lang==='es'?`${count(n,'echange')} completados`:`${count(n,'echange')} mené${n>1?'s':''} au bout`;
  const available=n=>lang==='en'?`${n>=200?'More than 200':count(n,'objet')} ${n>=200?'items ':''}available`:lang==='es'?`${n>=200?'Más de 200 objetos':count(n,'objet')} disponible${n===1?'':'s'}`:`${n>=200?'Plus de 200 objets':count(n,'objet')} disponible${n>1?'s':''}`;
  const summary=(date,loops,items,people)=>lang==='en'?`On ${date}: ${count(loops,'boucle')}, ${items} items swapped between ${people} people.`:lang==='es'?`El ${date}: ${count(loops,'boucle')}, ${items} objetos intercambiados entre ${people} personas.`:`Le ${date} : ${count(loops,'boucle')}, ${items} objets échangés entre ${people} personnes.`;
  function error(message){
    if(lang==='fr')return message;
    if(messages[message])return messages[message];
    // Pydantic préfixe les erreurs des validateurs. Ne jamais traduire la donnée saisie.
    const clean=String(message).replace(/^Value error, /,'');
    if(messages[clean])return messages[clean];
    return lang==='en'?'The request could not be completed. Please check your information and try again.':'No se ha podido completar la solicitud. Comprueba tus datos e inténtalo de nuevo.';
  }
  const localPath=path=>prefix+(path==='/'?'/':path);
  function switchUrl(target){
    const path=location.pathname.replace(/^\/(english|espanol)(?=\/|$)/,'')||'/';
    return languages[target].prefix+path+location.search+location.hash;
  }
  function links(root){
    root.querySelectorAll('a[href]').forEach(a=>{
      if(a.dataset.language)return;
      const href=a.getAttribute('href');
      if(/^\/(?:#|$|concept\/|comment-ca-marche\/|grand-troc\/|particuliers\/|pros\/|collectivites\/|faq\/|mentions-legales\/|cgu\/|confidentialite\/|regles\/)/.test(href))a.setAttribute('href',localPath(href));
    });
  }
  function menu(){
    const label=lang==='es'?'Idioma':lang==='en'?'Language':'Langue';
    const current=languages[lang];
    return `<li class="langue" id="langue-site">
      <button type="button" class="langue-bouton" aria-label="${label} : ${current.label}" aria-expanded="false" aria-controls="langue-choix"><span>${lang.toUpperCase()}</span><svg class="langue-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></button>
      <ul id="langue-choix" hidden>${Object.entries(languages).filter(([code])=>code!==lang).map(([code,l])=>`<li><a href="${switchUrl(code)}" data-language="${code}" lang="${code}" hreflang="${code}" aria-label="${l.label}"><span>${code.toUpperCase()}</span></a></li>`).join('')}</ul>
    </li>`;
  }
  function bindMenu(root){
    if(!root)return;
    const button=root.querySelector('.langue-bouton'),list=root.querySelector('ul');
    let pinned=false;
    function open(yes){
      button.setAttribute('aria-expanded',String(yes));list.hidden=!yes;
      if(yes)root.querySelectorAll('[data-language]').forEach(a=>a.setAttribute('href',switchUrl(a.dataset.language)));
      else pinned=false;
    }
    root.addEventListener('pointerover',e=>{if(e.pointerType==='mouse'&&!root.contains(e.relatedTarget))open(true)});
    root.addEventListener('pointerout',e=>{if(e.pointerType==='mouse'&&!root.contains(e.relatedTarget)&&!pinned)open(false)});
    button.addEventListener('click',()=>{pinned=!pinned;open(pinned)});
    root.addEventListener('click',e=>{const a=e.target.closest('[data-language]');if(a)a.setAttribute('href',switchUrl(a.dataset.language))});
    root.addEventListener('keydown',e=>{
      if(e.key==='Escape'){e.preventDefault();e.stopPropagation();open(false);button.focus()}
      else if(e.key==='ArrowDown'&&e.target===button){e.preventDefault();open(true);list.querySelector('a')?.focus()}
    });
    root.addEventListener('focusout',e=>{if(!root.contains(e.relatedTarget))open(false)});
    document.addEventListener('click',e=>{if(!root.contains(e.target))open(false)});
  }
  window.TT_I18N={lang,prefix,t,count,pending,completed,available,summary,error,localPath,switchUrl,links,menu,bindMenu};
})();
