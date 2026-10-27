/* Menu du haut et pied de page, communs à toutes les pages.
   Sur l'accueil, index.html intercepte les liens « /#… » pour changer de vue sans recharger,
   et appelle TT.compte() quand la session change. */
(()=>{
  const VERSION='6.200'; // version de prod (V5.100, V5.200…), changée par la livraison : voir docs/05-git-et-branches.md
  const LOGO='<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="#F2F3F6" d="M3 4h18v5h-6.5v11h-5V9H3z"/><path fill="#E6C23A" d="M29 28H11v-5h6.5V12h5v11H29z"/></svg>'; // deux T tête-bêche : deux membres, un échange
  const GRILLE='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="5" r="1.6"/><circle cx="12" cy="5" r="1.6"/><circle cx="19" cy="5" r="1.6"/><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/><circle cx="5" cy="19" r="1.6"/><circle cx="12" cy="19" r="1.6"/><circle cx="19" cy="19" r="1.6"/></svg>'; // « Voir tout »
  const ETOILE='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>'; // Favoris (le cœur est le « J'aime » du Match)
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
  <a class="favoris" href="/#favoris" aria-label="Favoris" title="Favoris">${ETOILE}<span class="favoris-nb" hidden></span></a>
  <div class="compte-zone">
    <a class="compte" id="compte" href="/#se-connecter" aria-haspopup="dialog" aria-expanded="false" aria-controls="pop-cnx">${PERSO}<span>Connexion</span></a>
    <div class="voile-cnx" id="voile-cnx" hidden></div>
    <div class="pop-cnx" id="pop-cnx" role="dialog" aria-labelledby="pop-titre" hidden></div>
    <div class="menu-compte" id="menu-compte" hidden>
      <p class="menu-compte-qui"><b id="menu-compte-pseudo"></b><span id="menu-compte-email"></span></p>
      <a href="/#monespace">Mon espace</a>
      <a href="/#echanges">Mes échanges</a>
      <a href="/#match">Le Match</a>
      <button type="button" class="menu-compte-sortir" id="menu-compte-sortir">Se déconnecter</button>
    </div>
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
  /* À la souris, le menu ☰ et ses sous-menus s'ouvrent au survol (Ben, 27/10) ; la connexion, au clic seulement. Un court délai
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
  const ouvertDansHaut=()=>haut.matches(':hover')||haut.contains(document.activeElement)||menu.classList.contains('ouvert')||haut.querySelector('[aria-expanded="true"],.categories-panneau:not([hidden]),.pop-cnx:not([hidden]),.menu-compte:not([hidden])');
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

  /* Compte, à droite du menu : « Connexion » ouvre au clic (jamais au survol) une fenêtre à deux onglets,
     Se connecter (mot de passe) et Créer un compte (e-mail, pseudo, mot de passe, ville). Un code à 6 chiffres,
     envoyé par e-mail avec un lien en secours, se tape dans la même fenêtre : inscription, mot de passe oublié,
     ancien compte sans mot de passe. Connecté, le bouton montre l'initiale et le pseudo et ouvre un petit menu.
     Tant que le serveur n'a pas confirmé la session gardée, l'initiale reste grisée. Sur téléphone, la fenêtre
     devient un panneau qui monte du bas de l'écran. */
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
  const c=$('#compte'), pop=$('#pop-cnx'), voile=$('#voile-cnx'), menuCompte=$('#menu-compte');
  const esc=t=>String(t??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const emailValide=e=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  // vue : connexion, inscription, code, nouveau-mdp, bravo. but : pourquoi le code a été envoyé (connexion ou inscription).
  const etat={moi:null,verif:false,vue:'connexion',email:'',but:'connexion',inscription:null,jeton:null};
  let ouvertLe=-1, minuteurRenvoi;

  /* Le bouton : visiteur (« Connexion »), session à confirmer (initiale grisée), membre (initiale et pseudo).
     compte(moi) : un objet membre, null pour un visiteur, undefined pour une session gardée pas encore confirmée. */
  function compte(m){
    if(m===true)m={pseudo:memo.get('troc.pseudo')||'',email:memo.get('troc.email')||''};
    etat.moi=m&&typeof m==='object'?m:null; etat.verif=m===undefined&&!!memo.get('troc.jeton');
    const membre=!!etat.moi||etat.verif;
    if(etat.moi?.pseudo)memo.set('troc.pseudo',etat.moi.pseudo);
    const pseudo=etat.moi?.pseudo||memo.get('troc.pseudo')||'';
    c.classList.toggle('membre',membre); c.classList.toggle('verif',etat.verif);
    c.innerHTML=membre?`<span class="compte-avatar" aria-hidden="true">${esc((pseudo[0]||'·').toUpperCase())}</span><span>${esc(pseudo||'Mon espace')}</span>`:`${PERSO}<span>Connexion</span>`;
    c.setAttribute('aria-label',etat.verif?'Vérification de votre session':etat.moi?'Mon compte : '+pseudo:'Connexion ou création de compte');
    c.setAttribute('aria-haspopup',membre?'menu':'dialog'); c.setAttribute('aria-controls',membre?'menu-compte':'pop-cnx');
    c.setAttribute('href',TT_I18N.localPath(membre?'/#monespace':'/#se-connecter'));
    haut.querySelectorAll('[data-membre]').forEach(el=>el.hidden=!etat.moi);
    haut.querySelectorAll('[data-visiteur]').forEach(el=>el.hidden=membre);
    if(!membre)ouvrirMenuCompte(false);
    else if(!['bravo','nouveau-mdp'].includes(etat.vue))ouvrirConnexion(false); // la fenêtre de bienvenue reste ouverte
  }
  // Hors de l'accueil (qui relit lui-même la session), on demande au serveur si la session gardée vaut toujours.
  function verifierSession(){
    const jeton=memo.get('troc.jeton');
    if(!jeton)return compte(null);
    compte(undefined);
    if(location.pathname===TT_I18N.localPath('/'))return;
    fetch(API+'/moi',{headers:{Authorization:'Bearer '+jeton}}).then(async r=>{
      if(r.status===401){memo.set('troc.jeton',null);compte(null);return}
      if(r.ok)compte(await r.json());
    }).catch(()=>{});
  }

  function ouvrirMenuCompte(oui){
    menuCompte.hidden=!oui; c.setAttribute('aria-expanded',!!oui||!pop.hidden);
    if(!oui){if(pop.hidden)voile.hidden=true;return}
    pop.hidden=true;
    $('#menu-compte-pseudo').textContent=etat.moi?.pseudo||memo.get('troc.pseudo')||'';
    $('#menu-compte-email').textContent=etat.moi?.email||memo.get('troc.email')||'';
    ouvertLe=performance.now(); fermer(); voile.hidden=false; menuCompte.querySelector('a').focus();
  }
  menuCompte.addEventListener('click',e=>{if(e.target.closest('a'))ouvrirMenuCompte(false)});
  $('#menu-compte-sortir').onclick=async()=>{
    const jeton=memo.get('troc.jeton'); ouvrirMenuCompte(false);
    try{await fetch(API+'/auth/deconnexion',{method:'POST',headers:{Authorization:'Bearer '+jeton}})}catch{}
    memo.set('troc.jeton',null); memo.set('troc.pseudo',null); compte(null);
    if(window.TT.surDeconnexion)window.TT.surDeconnexion(); else location.href=TT_I18N.localPath('/');
  };

  /* Le serveur gratuit s'endort : on le réveille dès l'ouverture de la fenêtre, pendant que la personne écrit.
     S'il tarde, un bandeau le dit, et la demande part toute seule dès qu'il répond. */
  let reveil=null, eveille=false, lent=false;
  function reveiller(){
    if(eveille)return Promise.resolve();
    if(!reveil){
      const lent=setTimeout(()=>{if(!eveille)afficherReveil(true)},1500);
      reveil=(async()=>{
        for(let essai=0;essai<8;essai++){
          try{const r=await fetch(API+'/sante');if(r.ok)break}catch{}
          await new Promise(ok=>setTimeout(ok,5000));
        }
        eveille=true; clearTimeout(lent); afficherReveil(false);
      })();
    }
    return reveil;
  }
  function afficherReveil(oui){lent=oui;const b=pop.querySelector('.pop-reveil');if(b)b.hidden=!oui}
  async function appeler(chemin,corps,methode='POST',jeton){
    await reveiller();
    const headers={'Content-Type':'application/json'}; if(jeton)headers.Authorization='Bearer '+jeton;
    let r;
    for(let essai=0;;essai++){
      try{r=await fetch(API+chemin,{method:methode,headers,body:corps===undefined?undefined:JSON.stringify(corps)})}catch{r=null}
      if(r&&![502,503,504].includes(r.status))break;
      if(essai>=6)throw new Error('Le serveur ne répond pas. Réessayez dans une minute.');
      afficherReveil(true);
      await new Promise(ok=>setTimeout(ok,10000));
    }
    afficherReveil(false);
    const d=await r.json().catch(()=>null);
    if(!r.ok){const x=d&&d.detail;const e=new Error(typeof x==='string'?TT_I18N.error(x):Array.isArray(x)?x.map(y=>TT_I18N.error(y.msg)).join(' · '):'Une erreur est survenue.');e.statut=r.status;throw e}
    return d;
  }

  /* La fenêtre */
  const REVEIL='<div class="pop-reveil" role="status" hidden><span>TopTroc se réveille après une pause, jusqu\'à une minute. Remplissez le formulaire : votre demande partira dès qu\'il répond.</span><span class="pop-barre"><i></i></span></div>';
  const tete=(titre,retour)=>`<div class="pop-tete">${retour?'<button type="button" class="pop-rond" data-retour aria-label="Retour">←</button>':''}<b class="pop-titre" id="pop-titre">${titre}</b><button type="button" class="pop-rond" data-fermer aria-label="Fermer">×</button></div>`;
  const onglets=()=>`<div class="pop-onglets" role="tablist" aria-label="Connexion ou inscription"><button type="button" role="tab" data-onglet="connexion" aria-selected="${etat.vue==='connexion'}">Se connecter</button><button type="button" role="tab" data-onglet="inscription" aria-selected="${etat.vue==='inscription'}">Créer un compte</button></div>`;
  const champMdp=(id,auto)=>`<span class="pop-mdp"><input type="password" id="${id}" name="mot_de_passe" autocomplete="${auto}" maxlength="200" required><button type="button" class="pop-voir" aria-pressed="false">Afficher</button></span>`;
  const jauge='<span class="pop-jauge" aria-hidden="true" data-n="0"><i></i><i></i><i></i><i></i></span><span class="pop-aide" data-aide-mdp>8 caractères minimum.</span>';
  const msg='<div class="pop-msg" aria-live="polite"></div>';

  function dessiner(){
    const v=etat.vue;
    if(v==='connexion')pop.innerHTML=`${tete('Bon retour sur TopTroc')}${onglets()}${REVEIL}
      <form class="pop-form" data-form="connexion" novalidate>
        <label class="pop-champ">E-mail<input type="email" name="email" autocomplete="username" inputmode="email" placeholder="vous@exemple.fr" maxlength="254" required value="${esc(etat.email)}"></label>
        <span class="pop-champ"><span class="pop-ligne"><label for="cnx-mdp">Mot de passe</label><button type="button" class="pop-lien" data-code>Mot de passe oublié ?</button></span>${champMdp('cnx-mdp','current-password')}</span>
        ${msg}
        <button class="pop-ok" type="submit">Se connecter</button>
      </form>
      <span class="pop-ou" aria-hidden="true"></span>
      <button type="button" class="pop-second" data-code>Recevoir un code de connexion par e-mail</button>`;
    else if(v==='inscription')pop.innerHTML=`${tete('Rejoindre TopTroc')}${onglets()}${REVEIL}
      <p class="pop-texte">Gratuit, sans engagement. Votre compte est prêt dès que votre e-mail est confirmé.</p>
      <form class="pop-form" data-form="inscription" novalidate>
        <label class="pop-champ">E-mail<input type="email" name="email" autocomplete="email" inputmode="email" placeholder="vous@exemple.fr" maxlength="254" required value="${esc(etat.email)}"></label>
        <label class="pop-champ">Pseudo<input name="pseudo" autocomplete="nickname" minlength="2" maxlength="40" required placeholder="Visible des autres membres"><span class="pop-aide" data-aide-pseudo>2 à 40 caractères. C'est le seul nom que voient les autres membres.</span></label>
        <span class="pop-champ"><label for="ins-mdp">Mot de passe</label>${champMdp('ins-mdp','new-password')}${jauge}</span>
        <label class="pop-champ">Ville <small>facultatif, pour les échanges en main propre</small><input name="zone" autocomplete="address-level2" maxlength="80" value="Marseille"></label>
        <label class="pop-coche"><input type="checkbox" name="cgu" required><span>J'accepte les <a href="/cgu/" target="_blank">conditions d'utilisation</a></span></label>
        ${msg}
        <button class="pop-ok" type="submit">Créer mon compte</button>
      </form>`;
    else if(v==='code'){
      const ins=etat.but==='inscription';
      pop.innerHTML=`${tete(ins?'Confirmez votre e-mail':'Votre code de connexion',true)}
      <p class="pop-texte">Un code à 6 chiffres vient de partir à <b>${esc(etat.email)}</b>. Tapez-le ici : pas besoin de quitter cette page.</p>
      <form class="pop-form" data-form="code" novalidate>
        <div class="pop-code" role="group" aria-label="Code à 6 chiffres">${[0,1,2,3,4,5].map(i=>`<input inputmode="numeric" pattern="[0-9]*" maxlength="1" autocomplete="${i?'off':'one-time-code'}" aria-label="Chiffre ${i+1}">`).join('')}</div>
        ${msg}
        <button class="pop-ok" type="submit">${ins?'Confirmer et entrer':'Me connecter'}</button>
      </form>
      <div class="pop-pied"><span data-renvoi></span><button type="button" class="pop-lien" data-retour>Changer d'e-mail</button></div>
      <p class="pop-aide">Le code marche 20 minutes. Vous pouvez aussi cliquer sur le lien de l'e-mail, depuis n'importe quel appareil. Rien reçu ? Regardez dans les spams ou l'onglet Promotions.</p>`;
      lancerRenvoi();
    }
    else if(v==='nouveau-mdp')pop.innerHTML=`${tete('Choisissez un mot de passe')}
      <p class="pop-texte">Vous êtes connecté. La prochaine fois, entrez en deux secondes avec votre e-mail et ce mot de passe, sans attendre d'e-mail.</p>
      <form class="pop-form" data-form="nouveau-mdp" novalidate>
        <input type="email" name="email" autocomplete="username" value="${esc(etat.email)}" hidden>
        <span class="pop-champ"><label for="n-mdp">Nouveau mot de passe</label>${champMdp('n-mdp','new-password')}${jauge}</span>
        ${msg}
        <button class="pop-ok" type="submit">Enregistrer</button>
      </form>
      <button type="button" class="pop-lien pop-centre" data-fermer>Plus tard</button>`;
    else if(v==='bravo')pop.innerHTML=`${tete('',false)}
      <div class="pop-bravo"><span class="compte-avatar" aria-hidden="true">${esc((etat.moi?.pseudo||'·')[0].toUpperCase())}</span>
        <b class="pop-titre" id="pop-titre">Bienvenue ${esc(etat.moi?.pseudo)} !</b>
        <p class="pop-texte">Votre compte est prêt. Proposez votre premier objet : c'est lui qui vous fera entrer dans les échanges.</p></div>
      <a class="pop-ok" href="${TT_I18N.localPath('/#proposer')}" data-fermer>Proposer un objet</a>
      <a class="pop-second" href="${TT_I18N.localPath('/#objets')}" data-fermer>Voir les objets d'abord</a>`;
    brancher();
  }

  function brancher(){
    pop.querySelectorAll('[data-onglet]').forEach(b=>b.onclick=()=>{garderEmail();etat.vue=b.dataset.onglet;dessiner();focusPremier()});
    pop.querySelectorAll('[data-fermer]').forEach(b=>b.addEventListener('click',()=>ouvrirConnexion(false)));
    pop.querySelectorAll('[data-retour]').forEach(b=>b.onclick=()=>{clearInterval(minuteurRenvoi);etat.vue=etat.but==='inscription'?'inscription':'connexion';dessiner();pop.querySelector('input[type=email]')?.select()});
    pop.querySelectorAll('.pop-voir').forEach(b=>b.onclick=()=>{const i=b.previousElementSibling,v=i.type==='password';i.type=v?'text':'password';b.textContent=v?'Masquer':'Afficher';b.setAttribute('aria-pressed',v)});
    pop.querySelectorAll('[data-code]').forEach(b=>b.onclick=()=>{garderEmail();envoyerCode()});
    const mdp=pop.querySelector('#ins-mdp,#n-mdp'); if(mdp)mdp.addEventListener('input',()=>jaugeMdp(mdp.value));
    const pseudo=pop.querySelector('[name=pseudo]'); if(pseudo)pseudo.addEventListener('input',()=>verifierPseudo(pseudo));
    const f=pop.querySelector('form'); if(f)f.onsubmit=e=>{e.preventDefault();ACTIONS[f.dataset.form](f)};
    if(etat.vue==='code')brancherCode();
    afficherReveil(lent&&!eveille);
  }
  function focusPremier(){([...pop.querySelectorAll('input:not([hidden]):not([type=checkbox])')].find(i=>!i.value)||pop.querySelector('input:not([hidden])'))?.focus()}
  function garderEmail(){const e=pop.querySelector('input[type=email]');if(e)etat.email=e.value.trim()}
  function dire(type,html){const m=pop.querySelector('.pop-msg');if(m)m.innerHTML=html?`<p class="pop-alerte ${type}">${html}</p>`:''}
  function attente(f,texte){const b=f.querySelector('.pop-ok'),avant=b.textContent;b.disabled=true;b.innerHTML=`<span class="pop-tourne" aria-hidden="true"></span>${esc(texte)}`;return()=>{b.disabled=false;b.textContent=avant}}
  function jaugeMdp(v){
    let n=0; if(v.length>=8)n++; if(v.length>=12)n++; if(/\d/.test(v)&&/[a-z]/i.test(v))n++; if(/[^a-z0-9]/i.test(v)||/[A-Z]/.test(v))n++;
    if(v&&v.length<8)n=1;
    pop.querySelector('.pop-jauge').dataset.n=v?Math.max(1,n):0;
    const a=pop.querySelector('[data-aide-mdp]');
    a.textContent=!v?'8 caractères minimum.':v.length<8?`Au moins 8 caractères (${v.length}/8)`:n>=3?'Solide.':'Correct. Plus long, c\'est encore mieux.';
    a.className='pop-aide'+(v.length>=8&&n>=3?' ok':'');
  }
  let minuteurPseudo;
  function verifierPseudo(i){
    clearTimeout(minuteurPseudo); i.removeAttribute('aria-invalid');
    const v=i.value.trim(), a=pop.querySelector('[data-aide-pseudo]');
    const aide=(texte,cls)=>{a.textContent=texte;a.className='pop-aide'+(cls?' '+cls:'')};
    if(v.length<2)return aide("2 à 40 caractères. C'est le seul nom que voient les autres membres.");
    minuteurPseudo=setTimeout(async()=>{
      try{const r=await fetch(API+'/auth/pseudo?pseudo='+encodeURIComponent(v));const d=await r.json();
        if(i.value.trim()!==v)return;
        if(d.libre)aide(`Pseudo libre : ${v}`,'ok'); else{i.setAttribute('aria-invalid','true');aide(`Pseudo déjà pris : ${v}. Essayez une variante.`,'ko')}
      }catch{}
    },450);
  }

  const ACTIONS={
    async connexion(f){
      const email=f.email.value.trim().toLowerCase(), mdp=f.mot_de_passe.value; etat.email=email; dire();
      f.email.removeAttribute('aria-invalid'); f.mot_de_passe.removeAttribute('aria-invalid');
      if(!emailValide(email)){f.email.setAttribute('aria-invalid','true');f.email.focus();return dire('ko','Indiquez votre e-mail, par exemple vous@exemple.fr.')}
      if(!mdp){f.mot_de_passe.focus();return dire('ko','Indiquez votre mot de passe, ou recevez un code par e-mail.')}
      const fin=attente(f,'Connexion…');
      try{const r=await appeler('/auth/connexion',{email,mot_de_passe:mdp}); fin(); entre(r)}
      catch(err){
        fin();
        if(err.statut===404)return dire('ko',`${esc(err.message)} <button type="button" class="pop-lien" data-vers="inscription">Créer un compte avec cet e-mail</button>`);
        if(err.statut===409)return dire('info',`${esc(err.message)} <button type="button" class="pop-lien" data-code>Recevoir un code</button>`);
        if(err.statut===401){f.mot_de_passe.setAttribute('aria-invalid','true');f.mot_de_passe.select()}
        dire('ko',`${esc(err.message)}${[401,429].includes(err.statut)?' <button type="button" class="pop-lien" data-code>Recevoir un code par e-mail à la place</button>':''}`);
      }
    },
    async inscription(f){
      const email=f.email.value.trim().toLowerCase(), pseudo=f.pseudo.value.trim(), mdp=f.mot_de_passe.value; etat.email=email; dire();
      const ko=(champ,texte)=>{champ.setAttribute('aria-invalid','true');champ.focus();dire('ko',texte)};
      if(!emailValide(email))return ko(f.email,'Indiquez un e-mail valide : le code de confirmation y sera envoyé.');
      if(pseudo.length<2)return ko(f.pseudo,"Choisissez un pseudo d'au moins 2 caractères.");
      if(mdp.length<8)return ko(f.mot_de_passe,'Le mot de passe doit faire au moins 8 caractères.');
      if(!f.cgu.checked)return dire('ko',"Cochez la case pour accepter les conditions d'utilisation.");
      const fin=attente(f,'Envoi du code…');
      try{
        await appeler('/auth/inscription',{email,pseudo,langue:TT_I18N.lang}); fin();
        etat.inscription={pseudo,mot_de_passe:mdp,zone:f.zone.value.trim()||null}; etat.but='inscription'; etat.vue='code'; dessiner(); focusPremier();
      }catch(err){
        fin();
        if(err.statut===409&&/e-mail/.test(err.message))return dire('ko',`${esc(err.message)} <button type="button" class="pop-lien" data-vers="connexion">Se connecter</button>`);
        if(err.statut===409)return ko(f.pseudo,esc(err.message));
        dire('ko',esc(err.message));
      }
    },
    async code(f){
      const code=[...f.querySelectorAll('.pop-code input')].map(i=>i.value).join(''); dire();
      if(code.length<6)return dire('ko','Tapez les 6 chiffres reçus par e-mail.');
      const fin=attente(f,'Vérification…');
      try{
        const r=await appeler('/auth/code',{email:etat.email,code,...(etat.but==='inscription'?etat.inscription:{})}); fin();
        if(r.inscription_requise){etat.vue='inscription';dessiner();return dire('info','Pas encore de compte avec cet e-mail : choisissez un pseudo et un mot de passe.')}
        clearInterval(minuteurRenvoi); entre(r,etat.but==='inscription');
      }catch(err){
        fin(); f.querySelector('.pop-code').classList.add('ko'); f.querySelectorAll('.pop-code input').forEach(i=>i.value='');
        f.querySelector('.pop-code input').focus(); dire('ko',esc(err.message));
      }
    },
    async ['nouveau-mdp'](f){
      const mdp=f.mot_de_passe.value; dire();
      if(mdp.length<8){f.mot_de_passe.setAttribute('aria-invalid','true');return dire('ko','Le mot de passe doit faire au moins 8 caractères.')}
      const fin=attente(f,'Enregistrement…');
      try{const m=await appeler('/auth/mot-de-passe',{mot_de_passe:mdp},'PUT',etat.jeton); fin(); compte(m);
        if(window.TT.apresMotDePasse)window.TT.apresMotDePasse(m); ouvrirConnexion(false)}
      catch(err){fin();dire('ko',esc(err.message))}
    },
  };
  pop.addEventListener('click',e=>{
    const vers=e.target.closest('[data-vers]'); if(!vers)return;
    garderEmail(); etat.vue=vers.dataset.vers; dessiner(); focusPremier();
  });
  // Le code n'est pas dans brancher() pour les boutons ajoutés dans un message d'erreur.
  pop.addEventListener('click',e=>{const b=e.target.closest('.pop-msg [data-code]');if(b){garderEmail();envoyerCode()}});

  async function envoyerCode(){
    const email=(etat.email||'').toLowerCase();
    if(!emailValide(email)){
      if(etat.vue!=='connexion'){etat.vue='connexion';dessiner()}
      const i=pop.querySelector('input[type=email]'); i.setAttribute('aria-invalid','true'); i.focus();
      return dire('ko',"Indiquez d'abord votre e-mail : le code y sera envoyé.");
    }
    pop.querySelectorAll('[data-code]').forEach(b=>{b.disabled=true});
    try{await appeler('/auth/lien',{email,langue:TT_I18N.lang}); etat.email=email; etat.but='connexion'; etat.vue='code'; dessiner(); focusPremier()}
    catch(err){pop.querySelectorAll('[data-code]').forEach(b=>{b.disabled=false});dire('ko',esc(err.message))}
  }
  function brancherCode(){
    const cases=[...pop.querySelectorAll('.pop-code input')], f=pop.querySelector('form');
    const complet=()=>{if(cases.every(i=>i.value))f.requestSubmit()};
    cases.forEach((i,n)=>{
      i.addEventListener('input',()=>{
        const chiffres=i.value.replace(/\D/g,'');
        if(chiffres.length>1){chiffres.slice(0,6-n).split('').forEach((d,k)=>{cases[n+k].value=d});(cases[Math.min(5,n+chiffres.length)]).focus();return complet()}
        i.value=chiffres; pop.querySelector('.pop-code').classList.remove('ko');
        if(chiffres&&cases[n+1])cases[n+1].focus();
        complet();
      });
      i.addEventListener('keydown',e=>{if(e.key==='Backspace'&&!i.value&&cases[n-1]){cases[n-1].value='';cases[n-1].focus()}});
      i.addEventListener('paste',e=>{
        const t=(e.clipboardData?.getData('text')||'').replace(/\D/g,'').slice(0,6); if(!t)return;
        e.preventDefault(); t.split('').forEach((d,k)=>{if(cases[k])cases[k].value=d}); (cases[t.length]||cases[5]).focus(); complet();
      });
    });
  }
  function lancerRenvoi(){
    clearInterval(minuteurRenvoi); let reste=30;
    const maj=()=>{
      const r=pop.querySelector('[data-renvoi]'); if(!r)return clearInterval(minuteurRenvoi);
      if(reste>0){r.textContent=`Renvoyer le code dans ${reste} s`;reste--;return}
      clearInterval(minuteurRenvoi); r.innerHTML='<button type="button" class="pop-lien">Renvoyer le code</button>';
      r.querySelector('button').onclick=async()=>{
        try{
          if(etat.but==='inscription')await appeler('/auth/inscription',{email:etat.email,pseudo:etat.inscription.pseudo,langue:TT_I18N.lang});
          else await appeler('/auth/lien',{email:etat.email,langue:TT_I18N.lang});
          lancerRenvoi(); dire('ok','Nouveau code envoyé. Seul le dernier reçu marche.');
        }catch(err){dire('ko',esc(err.message))}
      };
    };
    maj(); minuteurRenvoi=setInterval(maj,1000);
  }
  // Session ouverte : l'accueil la charge, les autres pages mènent à « Mon espace ».
  function entre(r,nouveau=false){
    etat.jeton=r.jeton; memo.set('troc.jeton',r.jeton); memo.set('troc.email',r.utilisateur.email);
    if(nouveau)etat.vue='bravo'; else if(!r.utilisateur.a_un_mot_de_passe)etat.vue='nouveau-mdp'; else etat.vue='connexion';
    compte(r.utilisateur);
    if(etat.vue!=='connexion'){pop.hidden=false;voile.hidden=false;dessiner();focusPremier()}
    if(window.TT.surConnexion)window.TT.surConnexion(r,nouveau);
    else if(!nouveau&&r.utilisateur.a_un_mot_de_passe)location.href=TT_I18N.localPath('/#monespace');
  }

  // ouvrirConnexion(false) ferme ; creer ouvre l'onglet « Créer un compte ».
  function ouvrirConnexion(oui=true,email,creer=false){
    if(!oui){pop.hidden=true;if(menuCompte.hidden)voile.hidden=true;c.setAttribute('aria-expanded',!menuCompte.hidden);clearInterval(minuteurRenvoi);etat.vue='connexion';return}
    if(etat.moi)return;
    if(email!==undefined)etat.email=email; else if(!etat.email)etat.email=memo.get('troc.email')||'';
    etat.vue=creer?'inscription':'connexion';
    menuCompte.hidden=true; pop.hidden=false; voile.hidden=false; c.setAttribute('aria-expanded','true');
    ouvertLe=performance.now(); fermer(); dessiner(); reveiller();
    if(etat.vue==='connexion'&&etat.email)pop.querySelector('#cnx-mdp').focus(); else focusPremier();
  }
  haut.querySelector('[data-devenir]').addEventListener('click',e=>{e.preventDefault();e.stopPropagation();ouvrirConnexion(true,undefined,true)});
  c.addEventListener('click',e=>{
    if(e.metaKey||e.ctrlKey||e.shiftKey||e.button)return;
    e.preventDefault(); e.stopImmediatePropagation();
    if(etat.moi||etat.verif)return ouvrirMenuCompte(menuCompte.hidden);
    ouvrirConnexion(pop.hidden);
  },true);
  voile.addEventListener('click',()=>{ouvrirConnexion(false);ouvrirMenuCompte(false)});
  // Un clic qui vient d'ouvrir la fenêtre (bouton d'une page, par exemple) ne la referme pas aussitôt. Un clic
  // dans la fenêtre qui la redessine (onglet, retour) laisse une cible détachée : ce n'est pas un clic dehors.
  document.addEventListener('click',e=>{
    if(e.timeStamp<=ouvertLe||!e.target.isConnected)return;
    if(!pop.hidden&&!pop.contains(e.target)&&!c.contains(e.target))ouvrirConnexion(false);
    if(!menuCompte.hidden&&!menuCompte.contains(e.target)&&!c.contains(e.target))ouvrirMenuCompte(false);
  });
  haut.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||(pop.hidden&&menuCompte.hidden))return;
    e.stopPropagation(); ouvrirConnexion(false); ouvrirMenuCompte(false); c.focus();
  });

  /* Compteur de l'étoile « Favoris ». Sur les pages sans le script du mode visiteur (visiteur.js), celui des favoris
     de 24 h gardés dans le navigateur ; un membre voit le sien une fois sur l'accueil. */
  const nbFavoris=haut.querySelector('.favoris-nb');
  function favoris(n){nbFavoris.textContent=n>99?'99+':n;nbFavoris.hidden=!n;haut.querySelector('.favoris').setAttribute('aria-label',n?`Favoris (${n})`:'Favoris')}
  try{favoris(JSON.parse(memo.get('troc.favoris')||'[]').filter(f=>Date.now()-new Date(f.ajoute_le)<864e5).length)}catch{}

  window.TT={compte,fermer,ouvrirConnexion,favoris};
  verifierSession();
})();
