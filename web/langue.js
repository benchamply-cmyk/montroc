/* La langue dépend uniquement de l'URL : aucun stockage ni service de traduction tiers. */
(()=>{
  const languages={fr:{prefix:'',label:'Français'},en:{prefix:'/english',label:'English'},es:{prefix:'/espanol',label:'Español'}};
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
      const href=a.getAttribute('href');
      if(/^\/(?:#|$|pros\/|collectivites\/|faq\/|mentions-legales\/|cgu\/|confidentialite\/|regles\/)/.test(href))a.setAttribute('href',localPath(href));
    });
  }
  function menu(){
    const label=lang==='es'?'Idioma':lang==='en'?'Language':'Langue';
    return `<li class="langue"><label><span class="sr-only">${label}</span><select aria-label="${label}" id="langue-site">${Object.entries(languages).map(([code,l])=>`<option value="${code}"${code===lang?' selected':''}>${l.label}</option>`).join('')}</select></label></li>`;
  }
  window.TT_I18N={lang,prefix,t,count,pending,completed,available,summary,error,localPath,switchUrl,links,menu};
  document.addEventListener('change',e=>{if(e.target.id==='langue-site')location.assign(switchUrl(e.target.value))});
})();
