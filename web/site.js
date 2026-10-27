/* Menu du haut et pied de page, communs à toutes les pages.
   Sur l'accueil, index.html intercepte les liens « /#… » pour changer de vue sans recharger,
   et appelle TT.compte() quand la session change. */
(()=>{
  const VERSION='6.200'; // version de prod (V5.100, V5.200…), changée par la livraison : voir docs/05-git-et-branches.md
  const LOGO='<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="#F2F3F6" d="M3 4h18v5h-6.5v11h-5V9H3z"/><path fill="#E6C23A" d="M29 28H11v-5h6.5V12h5v11H29z"/></svg>'; // deux T tête-bêche : deux membres, un échange
  const GRILLE='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="5" r="1.6"/><circle cx="12" cy="5" r="1.6"/><circle cx="19" cy="5" r="1.6"/><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/><circle cx="5" cy="19" r="1.6"/><circle cx="12" cy="19" r="1.6"/><circle cx="19" cy="19" r="1.6"/></svg>'; // « Voir tout »
  const COEUR='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>';
  const PERSO='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>';

  const haut=document.querySelector('header.site');
  if(haut)haut.innerHTML=`<div class="site-in">
  <a class="logo" href="/" aria-label="TopTroc, retour à l'accueil">${LOGO}<span>Top<span class="logo-2">Troc</span></span></a>
  <form class="recherche-entete" id="recherche-entete" role="search">
    <label class="sr-only" for="recherche-entete-champ">Rechercher sur TopTroc</label>
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 4 4"/></svg>
    <input id="recherche-entete-champ" type="search" name="q" maxlength="100" placeholder="Rechercher sur TopTroc">
    <button type="submit">Rechercher</button>
  </form>
  <button class="burger" type="button" aria-expanded="false" aria-controls="menu" aria-label="Ouvrir le menu"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="b1" d="M4 7h16"/><path class="b2" d="M4 12h16"/><path class="b3" d="M4 17h16"/></svg></button>
  <nav class="menu" id="menu" aria-label="Menu principal">
    <ul>
      <li><a href="/concept/">Le concept</a></li>
      <li class="sous"><button type="button" aria-expanded="false" aria-controls="pour-qui">Les offres<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
        <ul id="pour-qui" hidden>
          <li><a href="/particuliers/">Particuliers <small>Gratuit</small></a></li>
          <li><a href="/pros/">Professionnels</a></li>
          <li><a href="/collectivites/">Collectivités</a></li>
        </ul>
      </li>
      <li class="sous"><button type="button" aria-expanded="false" aria-controls="nav-catalogue">Le catalogue<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
        <ul id="nav-catalogue" hidden>
          <li><a href="/#objets">Voir les objets</a></li>
          <li data-membre hidden><a href="/#monespace">Recherches personnalisées</a></li>
          <li data-membre hidden><a href="/#monespace">Mes listes</a></li>
          <li data-visiteur><a href="/#se-connecter" data-devenir>Devenir membre</a></li>
        </ul>
      </li>
      <li><a href="/grand-troc/">Le Grand Troc</a></li>
    </ul>
  </nav>
  <a class="favoris" href="/#favoris" aria-label="Favoris" title="Favoris">${COEUR}<span class="favoris-nb" hidden></span></a>
  <div class="compte-zone">
    <a class="compte" id="compte" href="/#se-connecter" aria-controls="pop-cnx">${PERSO}<span>Se connecter / S'inscrire</span></a>
    <form class="pop-cnx" id="pop-cnx" hidden aria-label="Connexion à Mon espace">
      <b class="pop-titre">Connexion à Mon espace</b>
      <p class="pop-aide" hidden>Indiquez votre e-mail : un lien valable 20 minutes y arrive et ouvre votre compte.</p>
      <label><span>Votre e-mail</span><input type="email" name="email" required autocomplete="username" placeholder="vous@exemple.fr"></label>
      <label class="pop-champ-mdp"><span>Votre mot de passe</span>
        <span class="pop-mdp"><input type="password" name="mot_de_passe" required autocomplete="current-password"><button type="button" class="pop-voir" aria-pressed="false">Afficher</button></span></label>
      <button class="pop-ok" type="submit">Se connecter</button>
      <p class="pop-msg" role="status" hidden></p>
      <button class="pop-lien" type="button" data-lien>Mot de passe oublié ou pas encore choisi ? Recevoir un lien par e-mail</button>
      <button class="pop-lien" type="button" data-creer>Nouveau sur TopTroc ? Créer un compte</button>
      <button class="pop-lien" type="button" data-retour hidden>Déjà un compte ? Se connecter avec un mot de passe</button>
    </form>
  </div>
  <nav class="menu menu-actions" aria-label="Langue et aide">
    <ul>
      ${TT_I18N.menu()}
      <li><a class="aide" href="/faq/" aria-label="FAQ" title="FAQ">?</a></li>
    </ul>
  </nav>
</div>
  <nav class="categories-barre" aria-label="Catégories d'objets"><div class="categories-defile" id="categories-entete"></div><div class="categories-panneau" id="categories-panneau" hidden></div></nav>`;

  const pied=document.querySelector('footer.site');
  if(pied)pied.innerHTML=`<div class="in">
  <nav aria-label="Informations"><ul>
    <li><a href="/faq/#contact">Contact</a></li>
    <li><a href="/faq/">FAQ</a></li>
    <li><a href="/mentions-legales/">Mentions légales</a></li>
    <li><a href="/cgu/">CGU</a></li>
    <li><a href="/confidentialite/">Confidentialité</a></li>
    <li><a href="/regles/">Règles et signalements</a></li>
  </ul></nav>
  <p class="pied-version" style="margin:0"><a class="version" href="https://github.com/benchamply-cmyk/montroc/blob/prod/CHANGELOG.md">V${VERSION}</a></p>
</div>`;
  // En pré-production, la version (V5.2000, V5.3000…) est la dernière étiquette preprod-V… posée par le workflow Versions.
  const lienVersion=document.querySelector('a.version');
  if(lienVersion&&/^preprod(--|\.)/.test(location.hostname)){
    lienVersion.textContent='preprod';
    lienVersion.href='https://github.com/benchamply-cmyk/montroc/tree/preprod';
    fetch('https://api.github.com/repos/benchamply-cmyk/montroc/git/matching-refs/tags/preprod-V').then(r=>r.json()).then(refs=>{
      const v=refs.map(r=>r.ref.slice('refs/tags/preprod-V'.length).split('.').map(Number)).filter(x=>x.length===2&&!x.some(isNaN))
        .sort((a,b)=>a[0]-b[0]||a[1]-b[1]).pop();
      if(v)lienVersion.textContent=`V${v.join('.')} · preprod`;
    }).catch(()=>{});
  }
  if(haut){TT_I18N.links(haut);TT_I18N.bindMenu(haut.querySelector('#langue-site'))}
  if(pied)TT_I18N.links(pied);
  if(!haut)return;

  const $=s=>haut.querySelector(s);
  const menu=$('#menu'), burger=$('.burger'), sous=[...haut.querySelectorAll('.sous')];
  $('#recherche-entete').addEventListener('submit',e=>{
    e.preventDefault();
    const q=$('#recherche-entete-champ').value.trim();
    const destination=TT_I18N.localPath('/')+(q?'#site='+encodeURIComponent(q):'#recherche-site');
    fermer();
    if(location.pathname===TT_I18N.localPath('/')){
      history.pushState({tt:1},'',destination);
      dispatchEvent(new PopStateEvent('popstate'));
    }else location.href=destination;
  });
  const mobile=matchMedia('(max-width:1199px)');
  function ouvrirSous(item,oui){
    item.querySelector('button').setAttribute('aria-expanded',oui);
    item.querySelector('ul').hidden=!oui;
  }
  function ouvrirMenu(oui){
    menu.classList.toggle('ouvert',oui); burger.setAttribute('aria-expanded',oui);
    burger.setAttribute('aria-label',oui?'Fermer le menu':'Ouvrir le menu');
    if(!oui)sous.forEach(item=>ouvrirSous(item,false));
  }
  function fermer(){ouvrirMenu(false);sous.forEach(item=>ouvrirSous(item,false))}
  /* À la souris, tout s'ouvre au survol (Ben, 27/10) : le menu ☰, ses sous-menus et la connexion. Un court délai
     avant de refermer laisse passer la souris du bouton au panneau. Au doigt et au clavier, le clic reste nécessaire. */
  let survolLe=-1;
  const recent=()=>performance.now()-survolLe<600; // le clic qui suit un survol ne referme pas ce qui vient de s'ouvrir
  function survol(zones,ouvrir,refermer){
    let minuteur;
    zones.forEach(z=>{
      z.addEventListener('pointerenter',e=>{if(e.pointerType!=='mouse')return;clearTimeout(minuteur);if(ouvrir())survolLe=performance.now()});
      z.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse')minuteur=setTimeout(refermer,250)});
    });
  }
  survol([burger,menu],()=>{if(menu.classList.contains('ouvert'))return false;ouvrirMenu(true);return true},()=>{if(!menu.contains(document.activeElement))fermer()});
  sous.forEach(item=>item.addEventListener('pointerenter',e=>{if(e.pointerType!=='mouse')return;sous.forEach(other=>ouvrirSous(other,other===item));survolLe=performance.now()}));
  burger.onclick=()=>{if(!recent())ouvrirMenu(!menu.classList.contains('ouvert'))};
  sous.forEach(item=>item.querySelector('button').onclick=()=>{
    if(recent())return;
    const ouvrir=item.querySelector('button').getAttribute('aria-expanded')!=='true';
    sous.forEach(other=>ouvrirSous(other,false));
    ouvrirSous(item,ouvrir);
  });
  menu.addEventListener('click',e=>{if(e.target.closest('a'))fermer()});
  document.addEventListener('click',e=>{if(!menu.contains(e.target)&&!burger.contains(e.target))fermer()});
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape')return;
    const ouvert=sous.find(item=>item.querySelector('button').getAttribute('aria-expanded')==='true');
    if(menu.classList.contains('ouvert')||ouvert){const mobileOuvert=menu.classList.contains('ouvert');fermer();(mobileOuvert?burger:ouvert.querySelector('button')).focus()}
  });
  mobile.addEventListener('change',fermer);
  addEventListener('scroll',()=>haut.classList.toggle('colle',scrollY>4),{passive:true});
  // Le logo suit le défilement : les deux T s'inversent en descendant, reviennent en remontant.
  const logo=haut.querySelector('.logo');let dernierY=scrollY;
  // En descendant, l'en-tête se réduit à une mini barre (sans la bande des catégories) ;
  // il revient en entier au survol, au clavier, ou tout en haut de la page.
  const ouvertDansHaut=()=>haut.matches(':hover')||haut.contains(document.activeElement)||menu.classList.contains('ouvert')||haut.querySelector('[aria-expanded="true"],.categories-panneau:not([hidden]),.pop-cnx:not([hidden])');
  const deplier=()=>haut.classList.remove('reduit');
  addEventListener('scroll',()=>{const y=scrollY,d=y-dernierY;
    if(y<=4){deplier();logo.classList.remove('inverse');dernierY=y;return}
    if(Math.abs(d)<8)return;
    logo.classList.toggle('inverse',d>0);
    if(d>0&&y>120&&!ouvertDansHaut())haut.classList.add('reduit');
    dernierY=y},{passive:true});
  haut.addEventListener('pointerenter',deplier);haut.addEventListener('focusin',deplier);

  // Page en cours : soulignée dans le menu.
  const ici=location.pathname;
  haut.querySelectorAll('a[href^="/"]').forEach(a=>{if(ici!=='/'&&a.getAttribute('href')===ici)a.setAttribute('aria-current','page')});
  sous.forEach(item=>{if(item.querySelector('[aria-current]'))item.classList.add('actif')});

  /* « Mon espace » : connecté, le bouton mène à l'espace. Sinon, il ouvre juste en dessous la connexion par
     mot de passe (sans e-mail à attendre), avec le lien magique en secours. C'est la seule entrée du site :
     « Créer un compte » passe la même fenêtre en mode e-mail seul (le lien reçu ouvre l'inscription). Le bouton s'appelle « Mon espace »
     une fois connecté, « Se connecter / S'inscrire » sinon. */
  // Pré-production (déploiement de la branche preprod sur Netlify) : son API à elle, sur une copie de la base.
  const API=['localhost','127.0.0.1'].includes(location.hostname)?'http://localhost:8001'
    :/^preprod(--|\.)/.test(location.hostname)?'https://montroc-api-preprod.onrender.com':'https://api.toptroc.com';
  // Au survol ou au clic d'une catégorie : « Voir tout », puis ses sous-catégories, chacune menant à ses objets (comme Vinted).
  const categoriesEntete=$('#categories-entete'), panneau=$('#categories-panneau'), barre=haut.querySelector('.categories-barre');
  let actif=null, fermetureCategorie, ouvertureSurvol=false;
  // Bande seulement : noms courts, dans cet ordre (Ben, 27/10). Partout ailleurs, le nom complet de la catégorie.
  const COURTS={mode:'Mode',enfant:'Enfant',maison:'Maison','high-tech':'Multimédia',sport:'Loisirs',culture:'Culture',electromenager:'Électroménager',bricolage:'Bricolage','auto-moto':'Auto, Moto',divers:'Divers'};
  const traduire=texte=>TT_I18N.t(String(texte));
  const element=(tag,texte,classe)=>{const e=document.createElement(tag);if(texte)e.textContent=texte;if(classe)e.className=classe;return e};
  function fermerCategorie(){
    clearTimeout(fermetureCategorie);
    if(actif)actif.setAttribute('aria-expanded','false');
    actif=null;ouvertureSurvol=false;panneau.hidden=true;panneau.replaceChildren();
  }
  function ouvrirCategorie(c,bouton){
    clearTimeout(fermetureCategorie);
    if(actif&&actif!==bouton)actif.setAttribute('aria-expanded','false');
    actif=bouton;bouton.setAttribute('aria-expanded','true');panneau.replaceChildren();
    const lien=(texte,slug)=>{const a=element('a',texte);a.href=TT_I18N.localPath('/')+'#categorie='+encodeURIComponent(slug);return a};
    // La catégorie en gras, séparée de ses sous-catégories en graisse normale (Ben, 27/10).
    const tete=element('div',null,'categorie-tete'), a=lien(null,c.slug), ul=element('ul',null,'categorie-liste');
    a.insertAdjacentHTML('afterbegin',GRILLE);a.append(element('strong',traduire(c.libelle)),element('span',traduire('Voir tout'),'categorie-voir'));tete.append(a);
    (c.sous_categories||[]).forEach(x=>{const li=element('li');li.append(lien(traduire(x.libelle),c.slug+'/'+x.slug));ul.append(li)});
    panneau.append(tete,ul);panneau.hidden=false;
  }
  fetch(API+'/categories').then(r=>{if(!r.ok)throw Error();return r.json()}).then(categories=>{
    categoriesEntete.replaceChildren();
    const rang=c=>{const i=Object.keys(COURTS).indexOf(c.slug);return i<0?99:i};
    [...categories].sort((a,b)=>rang(a)-rang(b)).forEach(c=>{
      const bouton=element('button',traduire(COURTS[c.slug]||c.libelle));
      bouton.title=traduire(c.libelle);
      bouton.type='button';bouton.setAttribute('aria-expanded','false');bouton.setAttribute('aria-controls','categories-panneau');
      bouton.addEventListener('click',()=>{if(actif===bouton&&!panneau.hidden&&!ouvertureSurvol)fermerCategorie();else ouvrirCategorie(c,bouton);ouvertureSurvol=false});
      bouton.addEventListener('pointerenter',e=>{if(e.pointerType==='mouse'&&actif!==bouton){ouvrirCategorie(c,bouton);ouvertureSurvol=true}});
      categoriesEntete.append(bouton);
    });
  }).catch(()=>{
    const a=element('a',traduire('Voir les objets'));a.href=TT_I18N.localPath('/#objets');categoriesEntete.replaceChildren(a);
  });
  barre.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse')fermetureCategorie=setTimeout(fermerCategorie,180)});
  barre.addEventListener('pointerenter',()=>clearTimeout(fermetureCategorie));
  panneau.addEventListener('click',e=>{if(e.target.closest('a'))fermerCategorie()});
  document.addEventListener('click',e=>{if(!barre.contains(e.target))fermerCategorie()});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panneau.hidden){const cible=actif;fermerCategorie();cible?.focus()}});
  const memo={get(k){try{return localStorage.getItem(k)}catch{return null}},set(k,v){try{v==null?localStorage.removeItem(k):localStorage.setItem(k,v)}catch{}}};
  const c=$('#compte'), pop=$('#pop-cnx'), msg=pop.querySelector('.pop-msg');
  let connecte=!!memo.get('troc.jeton'), ouvertLe=-1;
  function compte(oui){
    connecte=oui;
    c.querySelector('span').textContent=oui?'Mon espace':"Se connecter / S'inscrire";
    haut.querySelectorAll('[data-membre]').forEach(el=>el.hidden=!oui);
    haut.querySelectorAll('[data-visiteur]').forEach(el=>el.hidden=oui);
    c.setAttribute('href',TT_I18N.localPath(oui?'/#monespace':'/#se-connecter'));
    if(oui)ouvrirConnexion(false);
  }
  function dire(texte,ok){msg.textContent=texte;msg.classList.toggle('ok',!!ok);msg.hidden=!texte}
  function modeCreer(oui){
    pop.classList.toggle('creer',oui);
    pop.querySelector('.pop-titre').textContent=oui?'Créer un compte':'Connexion à Mon espace';
    pop.querySelector('.pop-aide').hidden=!oui;
    pop.querySelector('.pop-champ-mdp').hidden=oui; pop.mot_de_passe.required=!oui;
    pop.querySelector('.pop-ok').textContent=oui?'Recevoir mon lien':'Se connecter';
    pop.querySelector('[data-lien]').hidden=oui; pop.querySelector('[data-creer]').hidden=oui; pop.querySelector('[data-retour]').hidden=!oui;
  }
  function ouvrirConnexion(oui=true,email,creer=false){
    pop.hidden=!oui; c.setAttribute('aria-expanded',oui);
    if(!oui)return;
    ouvertLe=performance.now(); fermer(); dire(''); modeCreer(creer);
    if(email||!pop.email.value)pop.email.value=email||memo.get('troc.email')||'';
    (pop.email.value&&!creer?pop.mot_de_passe:pop.email).focus();
  }
  // Le serveur gratuit s'endort : la première requête peut échouer le temps qu'il redémarre (jusqu'à une minute).
  // On réessaie tout seul plutôt que de laisser la personne face à une erreur.
  async function appeler(chemin,corps){
    let r;
    for(let essai=0;;essai++){
      try{r=await fetch(API+chemin,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(corps)})}catch{r=null}
      if(r&&![502,503,504].includes(r.status))break;
      if(essai>=6)throw new Error('Le serveur ne répond pas. Réessayez dans une minute.');
      dire('Le serveur se réveille, encore quelques secondes…',true);
      await new Promise(ok=>setTimeout(ok,10000));
    }
    const d=await r.json().catch(()=>null);
    if(!r.ok){const x=d&&d.detail;throw new Error(typeof x==='string'?TT_I18N.error(x):'Vérifiez votre e-mail et votre mot de passe.')}
    return d;
  }
  haut.querySelector('[data-devenir]').addEventListener('click',e=>{e.preventDefault();e.stopPropagation();ouvrirConnexion(true,undefined,true)});
  c.addEventListener('click',e=>{
    if(connecte||e.metaKey||e.ctrlKey||e.shiftKey||e.button)return;
    e.preventDefault(); e.stopImmediatePropagation(); if(!recent())ouvrirConnexion(pop.hidden);
  },true);
  // Survol de « Se connecter / S'inscrire » : la fenêtre s'ouvre, et se referme en partant tant que rien n'y a été saisi.
  let emailOuvert='';
  survol([c.parentElement],()=>{if(connecte||!pop.hidden)return false;ouvrirConnexion(true);emailOuvert=pop.email.value;return true},
    ()=>{if(!pop.hidden&&!pop.mot_de_passe.value&&pop.email.value===emailOuvert)ouvrirConnexion(false)});
  pop.querySelector('.pop-voir').onclick=e=>{
    const v=pop.mot_de_passe.type==='password'; pop.mot_de_passe.type=v?'text':'password';
    e.target.textContent=v?'Masquer':'Afficher'; e.target.setAttribute('aria-pressed',v);
  };
  pop.onsubmit=async e=>{
    e.preventDefault(); if(pop.classList.contains('creer'))return envoyerLien();
    const b=pop.querySelector('.pop-ok'); b.disabled=true; b.textContent='Connexion…'; dire('');
    try{
      const r=await appeler('/auth/connexion',{email:pop.email.value.trim(),mot_de_passe:pop.mot_de_passe.value});
      memo.set('troc.jeton',r.jeton); memo.set('troc.email',r.utilisateur.email); pop.reset(); compte(true);
      if(window.TT.surConnexion)window.TT.surConnexion(r); else location.href=TT_I18N.localPath('/#monespace');
    }catch(err){dire(err.message);pop.mot_de_passe.select()}
    finally{b.disabled=false;b.textContent='Se connecter'}
  };
  async function envoyerLien(){
    const email=pop.email.value.trim();
    if(!pop.email.checkValidity()||!email){dire('Indiquez votre e-mail : le lien y sera envoyé.');pop.email.focus();return}
    try{await appeler('/auth/lien',{email,langue:TT_I18N.lang});dire(`Lien envoyé à ${email} : ouvrez l'e-mail sur cet appareil et cliquez dessus. Vous pourrez ensuite choisir un mot de passe.`,true)}
    catch(err){dire(err.message)}
  }
  pop.querySelector('[data-lien]').onclick=envoyerLien;
  pop.querySelector('[data-creer]').onclick=()=>{modeCreer(true);dire('');pop.email.focus()};
  pop.querySelector('[data-retour]').onclick=()=>{modeCreer(false);dire('');(pop.email.value?pop.mot_de_passe:pop.email).focus()};
  // Un clic qui vient d'ouvrir la fenêtre (bouton d'une page, par exemple) ne la referme pas aussitôt.
  document.addEventListener('click',e=>{if(!pop.hidden&&e.timeStamp>ouvertLe&&!pop.contains(e.target)&&!c.contains(e.target))ouvrirConnexion(false)});
  pop.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();ouvrirConnexion(false);c.focus()}});

  /* Compteur du cœur « Favoris ». Sur les pages sans le script du mode visiteur (visiteur.js), celui des favoris
     de 24 h gardés dans le navigateur ; un membre voit le sien une fois sur l'accueil. */
  const nbFavoris=haut.querySelector('.favoris-nb');
  function favoris(n){nbFavoris.textContent=n>99?'99+':n;nbFavoris.hidden=!n;haut.querySelector('.favoris').setAttribute('aria-label',n?`Favoris (${n})`:'Favoris')}
  try{favoris(JSON.parse(memo.get('troc.favoris')||'[]').filter(f=>Date.now()-new Date(f.ajoute_le)<864e5).length)}catch{}

  compte(connecte);
  window.TT={compte,fermer,ouvrirConnexion,favoris};
})();
