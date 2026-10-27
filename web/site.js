/* Menu du haut et pied de page, communs à toutes les pages.
   Sur l'accueil, index.html intercepte les liens « /#… » pour changer de vue sans recharger,
   et appelle TT.compte() quand la session change. */
(()=>{
  const VERSION='6.200'; // version de prod (V5.100, V5.200…), changée par la livraison : voir docs/05-git-et-branches.md
  const LOGO='<svg viewBox="0 0 32 32" aria-hidden="true"><path fill="#F2F3F6" d="M3 4h18v5h-6.5v11h-5V9H3z"/><path fill="#E6C23A" d="M29 28H11v-5h6.5V12h5v11H29z"/></svg>'; // deux T tête-bêche : deux membres, un échange
  const PERSO='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>';

  const haut=document.querySelector('header.site');
  if(haut)haut.innerHTML=`<div class="site-in">
  <a class="logo" href="/" aria-label="TopTroc, retour à l'accueil">${LOGO}<span>Top<span class="logo-2">Troc</span></span></a>
  <nav class="menu" id="menu" aria-label="Menu principal">
    <ul>
      <li><a href="/#objets">Voir les objets</a></li>
      <li class="sous"><button type="button" aria-expanded="false" aria-controls="decouvrir">Le concept<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
        <ul id="decouvrir" hidden>
          <li><a href="/concept/">Le concept</a></li>
          <li><a href="/comment-ca-marche/">Comment ça marche</a></li>
          <li><a href="/grand-troc/">Le Grand Troc</a></li>
        </ul>
      </li>
      <li class="sous"><button type="button" aria-expanded="false" aria-controls="pour-qui">Pour qui ?<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
        <ul id="pour-qui" hidden>
          <li><a href="/particuliers/">Particuliers <small>Gratuit</small></a></li>
          <li><a href="/pros/">Professionnels</a></li>
          <li><a href="/collectivites/">Collectivités</a></li>
        </ul>
      </li>
      <li><a href="/faq/">FAQ</a></li>
      ${TT_I18N.menu()}
    </ul>
  </nav>
  <div class="compte-zone">
    <a class="compte" id="compte" href="/#se-connecter" aria-controls="pop-cnx">${PERSO}<span>Se connecter</span></a>
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
  <button class="burger" type="button" aria-expanded="false" aria-controls="menu" aria-label="Ouvrir le menu"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="b1" d="M4 7h16"/><path class="b2" d="M4 12h16"/><path class="b3" d="M4 17h16"/></svg></button>
</div>`;

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
  <p class="pilote" style="margin:0">Pilote : <b>Département (13) Bouches-du-Rhône</b> · <a class="version" href="https://github.com/benchamply-cmyk/montroc/blob/prod/CHANGELOG.md">V${VERSION}</a></p>
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
  const mobile=matchMedia('(max-width:1199px)');
  function ouvrirSous(item,oui){
    item.querySelector('button').setAttribute('aria-expanded',oui);
    item.querySelector('ul').hidden=!oui;
  }
  function ouvrirMenu(oui){
    menu.classList.toggle('ouvert',oui); burger.setAttribute('aria-expanded',oui);
    burger.setAttribute('aria-label',oui?'Fermer le menu':'Ouvrir le menu');
    document.body.classList.toggle('menu-ouvert',oui);
    if(mobile.matches)sous.forEach(item=>ouvrirSous(item,oui));
  }
  function fermer(){ouvrirMenu(false);sous.forEach(item=>ouvrirSous(item,false))}
  burger.onclick=()=>ouvrirMenu(!menu.classList.contains('ouvert'));
  sous.forEach(item=>item.querySelector('button').onclick=()=>{
    const ouvrir=item.querySelector('button').getAttribute('aria-expanded')!=='true';
    if(!mobile.matches)sous.forEach(other=>ouvrirSous(other,false));
    ouvrirSous(item,ouvrir);
  });
  menu.addEventListener('click',e=>{if(e.target.closest('a'))fermer()});
  document.addEventListener('click',e=>{if(!mobile.matches)sous.forEach(item=>{if(!item.contains(e.target))ouvrirSous(item,false)})});
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape')return;
    const ouvert=sous.find(item=>item.querySelector('button').getAttribute('aria-expanded')==='true');
    if(menu.classList.contains('ouvert')||ouvert){const mobileOuvert=menu.classList.contains('ouvert');fermer();(mobileOuvert?burger:ouvert.querySelector('button')).focus()}
  });
  mobile.addEventListener('change',fermer);
  addEventListener('scroll',()=>haut.classList.toggle('colle',scrollY>4),{passive:true});

  // Page en cours : soulignée dans le menu.
  const ici=location.pathname;
  haut.querySelectorAll('a[href^="/"]').forEach(a=>{if(ici!=='/'&&a.getAttribute('href')===ici)a.setAttribute('aria-current','page')});
  sous.forEach(item=>{if(item.querySelector('[aria-current]'))item.classList.add('actif')});

  /* « Mon espace » : connecté, le bouton mène à l'espace. Sinon, il ouvre juste en dessous la connexion par
     mot de passe (sans e-mail à attendre), avec le lien magique en secours. C'est la seule entrée du site :
     « Créer un compte » passe la même fenêtre en mode e-mail seul (le lien reçu ouvre l'inscription). Le bouton s'appelle « Mon espace »
     dès qu'un compte a déjà servi sur cet appareil, « Se connecter » sinon. */
  // Pré-production (déploiement de la branche preprod sur Netlify) : son API à elle, sur une copie de la base.
  const API=['localhost','127.0.0.1'].includes(location.hostname)?'http://localhost:8001'
    :/^preprod(--|\.)/.test(location.hostname)?'https://montroc-api-preprod.onrender.com':'https://api.toptroc.com';
  const memo={get(k){try{return localStorage.getItem(k)}catch{return null}},set(k,v){try{v==null?localStorage.removeItem(k):localStorage.setItem(k,v)}catch{}}};
  const c=$('#compte'), pop=$('#pop-cnx'), msg=pop.querySelector('.pop-msg');
  let connecte=!!memo.get('troc.jeton'), ouvertLe=-1;
  function compte(oui){
    connecte=oui;
    c.querySelector('span').textContent=oui||memo.get('troc.email')?'Mon espace':'Se connecter';
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
  c.addEventListener('click',e=>{
    if(connecte||e.metaKey||e.ctrlKey||e.shiftKey||e.button)return;
    e.preventDefault(); e.stopImmediatePropagation(); ouvrirConnexion(pop.hidden);
  },true);
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

  compte(connecte);
  window.TT={compte,fermer,ouvrirConnexion};
})();
