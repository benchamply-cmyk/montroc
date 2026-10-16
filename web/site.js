/* Menu du haut et pied de page, communs à toutes les pages.
   Sur l'accueil, index.html intercepte les liens « /#… » pour changer de vue sans recharger,
   et appelle TT.compte() quand la session change. */
(()=>{
  const LOGO='<svg viewBox="0 0 24 24" aria-hidden="true"><defs><linearGradient id="logo-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="var(--accent)"/><stop offset=".5" stop-color="var(--mark)"/><stop offset="1" stop-color="var(--ok)"/></linearGradient></defs><circle cx="12" cy="12" r="9" fill="none" stroke="url(#logo-g)" stroke-width="2"/><circle cx="12" cy="3" r="2.6" fill="var(--accent)"/><circle cx="19.8" cy="16.5" r="2.6" fill="var(--ok)"/><circle cx="4.2" cy="16.5" r="2.6" fill="var(--mark)"/></svg>';
  const PERSO='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>';

  const haut=document.querySelector('header.site');
  if(haut)haut.innerHTML=`<div class="site-in">
  <a class="logo" href="/" aria-label="TrocTroc, retour à l'accueil">${LOGO}<span>Troc<span class="logo-2">Troc</span></span></a>
  <nav class="menu" id="menu" aria-label="Menu principal">
    <ul>
      <li><a href="/#concept">Le concept</a></li>
      <li><a href="/#comment-ca-marche">Comment ça marche</a></li>
      <li><a href="/#grand-troc">Le Grand Troc</a></li>
      <li><a href="/#objets">Voir les objets</a></li>
      <li class="sous"><button type="button" aria-expanded="false" aria-controls="pour-qui">Pour qui ?<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
        <ul id="pour-qui" hidden>
          <li><a href="/#particuliers">Particuliers <small>Gratuit</small></a></li>
          <li><a href="/pros/">Professionnels</a></li>
          <li><a href="/collectivites/">Collectivités</a></li>
        </ul>
      </li>
    </ul>
  </nav>
  <a class="compte" id="compte" href="/#se-connecter">${PERSO}<span>Se connecter</span></a>
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
  <p class="pilote" style="margin:0">Pilote : <b>Département (13) Bouches-du-Rhône</b></p>
</div>`;
  if(!haut)return;

  const $=s=>haut.querySelector(s);
  const menu=$('#menu'), burger=$('.burger'), sous=$('.sous'), bSous=sous.querySelector('button'), liste=sous.querySelector('ul');
  const mobile=matchMedia('(max-width:959px)');

  function ouvrirSous(oui){bSous.setAttribute('aria-expanded',oui);liste.hidden=!oui}
  function ouvrirMenu(oui){
    menu.classList.toggle('ouvert',oui); burger.setAttribute('aria-expanded',oui);
    burger.setAttribute('aria-label',oui?'Fermer le menu':'Ouvrir le menu');
    document.body.classList.toggle('menu-ouvert',oui);
    if(mobile.matches)ouvrirSous(oui); // sur mobile, « Pour qui ? » est déplié d'office
  }
  function fermer(){ouvrirMenu(false);ouvrirSous(false)}
  burger.onclick=()=>ouvrirMenu(!menu.classList.contains('ouvert'));
  bSous.onclick=()=>ouvrirSous(bSous.getAttribute('aria-expanded')!=='true');
  menu.addEventListener('click',e=>{if(e.target.closest('a'))fermer()});
  document.addEventListener('click',e=>{if(!mobile.matches&&!sous.contains(e.target))ouvrirSous(false)});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&(menu.classList.contains('ouvert')||!liste.hidden)){const etait=menu.classList.contains('ouvert');fermer();(etait?burger:bSous).focus()}});
  mobile.addEventListener('change',fermer);
  addEventListener('scroll',()=>haut.classList.toggle('colle',scrollY>4),{passive:true});

  // Page en cours : soulignée dans le menu.
  const ici=location.pathname;
  haut.querySelectorAll('a[href^="/"]').forEach(a=>{if(ici!=='/'&&a.getAttribute('href')===ici)a.setAttribute('aria-current','page')});
  if(liste.querySelector('[aria-current]'))sous.classList.add('actif');

  // « Se connecter » devient « Mon espace » une fois connecté.
  function compte(connecte){
    const c=$('#compte'); c.querySelector('span').textContent=connecte?'Mon espace':'Se connecter';
    c.setAttribute('href',connecte?'/#mon-espace':'/#se-connecter');
  }
  let jeton=null; try{jeton=localStorage.getItem('troc.jeton')}catch{}
  compte(!!jeton);
  window.TT={compte,fermer};
})();
