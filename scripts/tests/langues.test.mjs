import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {parse} from 'acorn';
import {build,translator,pages,root} from '../localize.mjs';
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const catalogue=JSON.parse(read('web/i18n/messages.json'));
function runtime(lang,pathname='/',search='',hash=''){
 const events={};
 const context=vm.createContext({window:{TT_MESSAGES:Object.fromEntries(Object.entries(catalogue).map(([k,v])=>[k,v[lang]??k]))},document:{documentElement:{lang},addEventListener:(name,fn)=>events[name]=fn},location:{pathname,search,hash,assign:value=>events.destination=value}});
 vm.runInContext(read('web/langue.js'),context);context.TT_I18N=context.window.TT_I18N;
 return {i:context.TT_I18N,context,events};
}
function scripts(html){return [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(Boolean)}
function texts(html){
 return html.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/g,'').replace(/<!--[\s\S]*?-->/g,'').split(/<[^>]*>/g).map(s=>s.trim()).filter(Boolean);
}
const neutral=new Set(['.','·','1','2','Sophie','Loïc','Match','Troc','Vinted','Leboncoin','contact@troctroc.fr','SIREN :']);
const attributes=html=>[...html.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/g,'').matchAll(/\b(?:placeholder|alt|aria-label|title)="([^"]+)"/g)].map(m=>m[1]);
build();
test('chaque entrée du catalogue existe dans les deux langues',()=>{
 for(const [source,languages] of Object.entries(catalogue))for(const lang of ['en','es'])assert.ok(typeof languages[lang]==='string'&&languages[lang].trim(),`${lang}: ${source}`);
});
test('toutes les pages françaises sont couvertes',()=>{
 const actual=['index.html',...fs.readdirSync(path.join(root,'web'),{withFileTypes:true}).filter(e=>e.isDirectory()&&!['i18n','english','espanol'].includes(e.name)&&fs.existsSync(path.join(root,'web',e.name,'index.html'))).map(e=>`${e.name}/index.html`)];
 assert.deepEqual(actual.sort(),[...pages].sort());
 for(const page of pages){const html=read(`web/${page}`);for(const text of texts(html))assert.ok(catalogue[text]||neutral.has(text),`Traduction manquante ${page}: ${text}`);}
});
test('attributs accessibles et métadonnées traduits',()=>{
 const allowed=new Set(['Marseille','06 12 34 56 78']);
 for(const page of pages)for(const value of attributes(read(`web/${page}`)))assert.ok(catalogue[value]||allowed.has(value),`Attribut non traduit ${page}: ${value}`);
});
for(const [lang,prefix] of [['en','english'],['es','espanol']]){
 test(`${lang}: génération, arborescence et liens internes`,()=>{
  for(const page of pages){
   const html=read(`web/${prefix}/${page}`);
   assert.match(html,new RegExp(`<html lang="${lang}">`));
   assert.equal((html.match(/rel="canonical"/g)||[]).length,1);
   assert.equal((html.match(/rel="alternate"/g)||[]).length,4);
   assert.match(html,new RegExp(`rel="canonical" href="https://troctroc.fr/${prefix}/${page.replace('index.html','')}"`));
   assert.match(html,new RegExp(`src="/${prefix}/site.js"`));
   assert.ok(html.indexOf(`src="/${prefix}/messages.js"`)<html.indexOf('src="/langue.js"'));
   for(const [,url] of html.matchAll(/(?:src|href)="(\/[^"#]*)/g)){
    const file=url.split('?')[0];assert.ok(fs.existsSync(path.join(root,'web',file)),`Lien cassé: ${page} ${url}`);
    if(file.endsWith('/')||file==='')assert.ok(file.startsWith(`/${prefix}/`),`Lien dans la mauvaise langue: ${url}`);
   }
   for(const js of scripts(html))parse(js,{ecmaVersion:'latest'});
  }
  for(const js of ['site','match','messages'])parse(read(`web/${prefix}/${js}.js`),{ecmaVersion:'latest'});
 });
 test(`${lang}: le code, les routes API et les identifiants gardent leur sens`,()=>{
  const t=translator(lang);
  const source=`const objet={categorie_slug:'mode',etat:'neuf',mode_recherche:'precise'}; const selector='input[name=mode]:checked'; const route='/moi/objets'; const view='objet'; const label='Se connecter'; const title=user.titre; const html=\`<input name="donne-\${id}" value="neuf"><b>Vous donnez</b>\${user.description}\`;`;
  const result=t.js(source);
  for(const literal of ["categorie_slug:'mode'","etat:'neuf'","mode_recherche:'precise'","'input[name=mode]:checked'","'/moi/objets'","view='objet'",'user.titre','user.description','name="donne-${id}"','value="neuf"'])assert.ok(result.includes(literal),literal);
  assert.ok(!result.includes("label='Se connecter'"));
  const data={titre:'Vous donnez',description:'Un objet vous plaît ?'};
  const context=vm.createContext({user:data,id:3});vm.runInContext(result+';globalThis.result={title,html};',context);
  assert.equal(context.result.title,data.titre);assert.ok(context.result.html.includes(data.description));
 });
 test(`${lang}: catégories traduites, valeurs et contenu des membres préservés`,async()=>{
  const {context,i}=runtime(lang);
  const html=read(`web/${prefix}/index.html`),source=scripts(html).join('\n');
  const ast=parse(source,{ecmaVersion:'latest'});const api=ast.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='api');
  const cats=[{slug:'mode',libelle:'Mode & Accessoires',sous_categories:[{slug:'mode-vetements-femme',libelle:'Vêtements femme'}],caracteristiques:[{cle:'couleur',libelle:'Couleur',options:['Blanc','Noir']}]}];
  context.jeton=null;context.fetch=async()=>({ok:true,status:200,json:async()=>cats});
  vm.runInContext(source.slice(api.start,api.end),context);context.API='https://example.invalid';
  const result=await context.api('/categories');assert.equal(result[0].slug,'mode');assert.equal(result[0].libelle,i.t(cats[0].libelle));assert.equal(result[0].caracteristiques[0].cle,'couleur');assert.deepEqual(result[0].caracteristiques[0].options,['Blanc','Noir']);
  context.fetch=async()=>({ok:true,status:200,json:async()=>[{titre:'Vous donnez',description:'Bon état',caracteristiques:{marque:'Neuf'}}]});
  const items=await context.api('/objets');assert.equal(items[0].titre,'Vous donnez');assert.equal(items[0].description,'Bon état');assert.equal(items[0].caracteristiques.marque,'Neuf');
  assert.match(source,/option value="\$\{esc\(o\)\}">\$\{esc\(TT_I18N.t\(o\)\)\}/);
 });
}
test('changer de langue conserve page, recherche et ancre',()=>{
 for(const lang of ['fr','en','es'])for(const pathname of ['/faq/','/english/faq/','/espanol/faq/']){
  const {i}=runtime(lang,pathname,'?q=velo','#contact');
  assert.equal(i.switchUrl('fr'),'/faq/?q=velo#contact');assert.equal(i.switchUrl('en'),'/english/faq/?q=velo#contact');assert.equal(i.switchUrl('es'),'/espanol/faq/?q=velo#contact');
 }
 for(const pathname of ['/','/english','/espanol/'])assert.equal(runtime('fr',pathname).i.switchUrl('en'),'/english/');
});
test('drapeau et code actifs, seulement les deux autres langues dans le menu',()=>{
 for(const lang of ['fr','en','es']){
  const {i}=runtime(lang,'/english/pros/');const html=i.menu();
  for(const name of ['Français','English','Español'])assert.ok(html.includes(name));
  assert.match(html,/<button[^>]+aria-expanded="false"/);
  assert.match(html,new RegExp(`</svg><span>${lang.toUpperCase()}</span>`));
  assert.equal((html.match(/data-language=/g)||[]).length,2);
  assert.ok(!html.includes(`data-language="${lang}"`));
  assert.equal((html.match(/class="langue-drapeau"/g)||[]).length,3);
 }
});
test('ouverture au survol, clic tactile, fermeture extérieure et clavier',()=>{
 const {i,context,events}=runtime('fr');
 const handlers={},buttonHandlers={},attributes={'aria-expanded':'false'};
 const button={setAttribute:(k,v)=>attributes[k]=v,addEventListener:(k,f)=>buttonHandlers[k]=f,focus:()=>context.document.activeElement=button};
 const anchor={dataset:{language:'en'},setAttribute:(k,v)=>anchor[k]=v,focus:()=>context.document.activeElement=anchor};
 const list={hidden:true,querySelector:()=>anchor};
 const root={querySelector:s=>s==='ul'?list:button,querySelectorAll:()=>[anchor],contains:x=>[root,button,list,anchor].includes(x),addEventListener:(k,f)=>handlers[k]=f};
 i.bindMenu(root);
 handlers.pointerover({pointerType:'mouse',relatedTarget:null});assert.equal(list.hidden,false);assert.equal(attributes['aria-expanded'],'true');
 handlers.pointerout({pointerType:'mouse',relatedTarget:null});assert.equal(list.hidden,true);
 buttonHandlers.click();assert.equal(list.hidden,false);handlers.pointerout({pointerType:'mouse',relatedTarget:null});assert.equal(list.hidden,false);
 events.click({target:{}});assert.equal(list.hidden,true);
 handlers.pointerover({pointerType:'touch',relatedTarget:null});assert.equal(list.hidden,true);buttonHandlers.click();assert.equal(list.hidden,false);
 handlers.keydown({key:'Escape',preventDefault(){},stopPropagation(){}});assert.equal(list.hidden,true);assert.equal(context.document.activeElement,button);
 handlers.keydown({key:'ArrowDown',target:button,preventDefault(){}});assert.equal(list.hidden,false);assert.equal(context.document.activeElement,anchor);
 context.location.hash='#objet-2';handlers.pointerover({pointerType:'mouse',relatedTarget:null});assert.equal(anchor.href,'/english/#objet-2');
});
test('pluriels et messages complets dans la langue choisie',()=>{
 const en=runtime('en').i,es=runtime('es').i,fr=runtime('fr').i;
 assert.equal(en.count(1,'objet'),'1 item');assert.equal(en.count(0,'objet'),'0 items');assert.equal(en.count(2,'match'),'2 matches');
 assert.equal(es.count(2,'demande'),'2 solicitudes');assert.equal(fr.count(1,'objet'),'1 objet');
 assert.equal(en.available(200),'More than 200 items available');assert.equal(es.available(1),'1 objeto disponible');
 assert.match(en.pending(2),/2 swaps awaiting/);assert.match(es.summary('26 octubre',1,3,3),/1 cadena/);
 assert.equal(en.error('E-mail ou mot de passe incorrect.'),'Incorrect email or password.');assert.equal(fr.error('message inconnu'),'message inconnu');
 assert.ok(!en.error('Une erreur interne inattendue').includes('erreur'));
});
test('génération déterministe',()=>{
 const before=read('web/english/index.html');build();assert.equal(read('web/english/index.html'),before);
});
test('les attributs métier du HTML et des gabarits JavaScript ne sont pas traduits',()=>{
 const protectedAttributes=/\b(class|id|name|value|type|role|data-[a-z-]+|aria-controls|aria-hidden|aria-expanded|autocomplete)=("[^"]*"|'[^']*')/g;
 const attrs=s=>[...s.matchAll(protectedAttributes)].map(m=>[m[1],m[2]]);
 const tokens=source=>{const out=[];parse(source,{ecmaVersion:'latest',onToken(t){if(['string','template'].includes(t.type.label))out.push(t.value)}});return out};
 for(const lang of ['en','es']){
  const t=translator(lang);
  for(const page of pages){
   const source=read(`web/${page}`),translated=t.html(source);
   const withoutCode=s=>s.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/g,'');
   assert.deepEqual(attrs(withoutCode(translated)),attrs(withoutCode(source)),`${lang}: ${page}`);
   for(const script of scripts(source)){const before=tokens(script),after=tokens(t.js(script));assert.equal(before.length,after.length);for(let j=0;j<before.length;j++)assert.deepEqual(attrs(after[j]),attrs(before[j]),`${lang}: ${page} token ${j}`);}
  }
  for(const file of ['site','match']){const source=read(`web/${file}.js`),before=tokens(source),after=tokens(t.js(source));assert.equal(before.length,after.length);for(let j=0;j<before.length;j++)assert.deepEqual(attrs(after[j]),attrs(before[j]),`${lang}: ${file} token ${j}`);}
 }
});
