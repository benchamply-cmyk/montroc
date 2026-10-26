/** Génère les mêmes pages et scripts dans deux langues, sans réécrire le code métier.
 * Les traductions ne s'appliquent qu'aux littéraux : jamais aux données des membres.
 */
import {parse} from 'acorn';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const catalogue=JSON.parse(fs.readFileSync(path.join(root,'web/i18n/messages.json'),'utf8'));
const escapeRegex=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
export const pages=['index.html',...['pros','collectivites','faq','mentions-legales','cgu','confidentialite','regles'].map(p=>`${p}/index.html`)];
export function translator(lang){
 const dictionary=Object.fromEntries(Object.entries(catalogue).map(([k,v])=>[k,v[lang]]));
 const words=new RegExp(`(?<![\\p{L}\\p{N}_-])(?:${Object.keys(dictionary).sort((a,b)=>b.length-a.length).map(escapeRegex).join('|')})(?![\\p{L}\\p{N}_-])`,'gu');
 const exact=s=>{const trimmed=s.trim();return dictionary[trimmed]===undefined?s:s.replace(trimmed,dictionary[trimmed])};
 const fragment=s=>s.replace(words,m=>dictionary[m]);
 function js(source){
  const edits=[];
  parse(source,{ecmaVersion:'latest',onToken(token){
   if(token.type.label==='string'){
    const value=token.value==='fr-FR'?(lang==='en'?'en-GB':'es-ES'):dictionary[token.value]??(token.value.includes('<')?fragment(token.value):exact(token.value));
    if(value!==token.value)edits.push([token.start,token.end,JSON.stringify(value)]);
   }else if(token.type.label==='template'){
    const value=fragment(token.value);
    if(value!==token.value)edits.push([token.start,token.end,value.replace(/\\/g,'\\\\').replace(/`/g,'\\`').replace(/\$\{/g,'\\${')]);
   }
  }});
  for(const [start,end,value] of edits.reverse())source=source.slice(0,start)+value+source.slice(end);
  parse(source,{ecmaVersion:'latest'});
  return source;
 }
 function html(source){
  source=source.replace(/(mailto:[^"?]+\?subject=)([^"&]+)/g,(_,base,subject)=>base+encodeURIComponent(exact(decodeURIComponent(subject))));
  // Protéger les scripts/styles avant de traiter les nœuds texte HTML.
  const blocks=[];
  source=source.replace(/<(script|style)\b([^>]*)>([\s\S]*?)<\/\1>/g,(all,tag,attrs,body)=>{
   blocks.push(`<${tag}${attrs}>${tag==='script'&&!attrs.includes('src=')?js(body):body}</${tag}>`);return `TTBLOCK${blocks.length-1}END`;
  });
  source=source.split(/(<[^>]*>)/g).map(part=>{
   if(!part.startsWith('<'))return part.replace(/TTBLOCK\d+END/g,m=>`\u0000${m}\u0000`).split(/(\u0000[^\u0000]*\u0000)/).map(x=>x.startsWith('\u0000')?x.slice(1,-1):exact(x)).join('');
   return part.replace(/\b(aria-label|placeholder|alt|title)="([^"]*)"/g,(_,key,value)=>`${key}="${exact(value).replace(/"/g,'&quot;')}"`)
    .replace(/(<meta\b[^>]*name="description"[^>]*content=")([^"]*)"/g,(_,start,value)=>`${start}${exact(value).replace(/"/g,'&quot;')}"`);
  }).join('');
  return source.replace(/TTBLOCK(\d+)END/g,(_,i)=>blocks[i]);
 }
 return {exact,fragment,js,html};
}
export function build(){
 for(const [lang,prefix] of [['en','english'],['es','espanol']]){
  const t=translator(lang),out=path.join(root,'web',prefix);fs.mkdirSync(out,{recursive:true});
  for(const p of pages){
   let s=t.html(fs.readFileSync(path.join(root,'web',p),'utf8').replace(/<link rel="(?:canonical|alternate)"[^>]*>\n?/g,'')).replace('<html lang="fr">',`<html lang="${lang}">`);
   // Scripts communs aux pages de la même langue, assets visuels inchangés.
   s=s.replace(/src="(?:\/)?(site|match)\.js"/g,`src="/${prefix}/$1.js"`).replace('src="annonce.js"','src="/annonce.js"');
   s=s.replace('<script src="/langue.js">',`<script src="/${prefix}/messages.js"></script>\n<script src="/langue.js">`);
   s=s.replace(/href="(\/(?:#|$|pros\/|collectivites\/|faq\/|mentions-legales\/|cgu\/|confidentialite\/|regles\/)[^"]*)"/g,`href="/${prefix}$1"`);
   const canonical='/'+p.replace(/index\.html$/,'');
   const alternates=[['fr',''],['en','/english'],['es','/espanol'],['x-default','']].map(([code,base])=>`<link rel="alternate" hreflang="${code}" href="https://toptroc.com${base}${canonical}">`).join('\n');
   s=s.replace('</head>',`<link rel="canonical" href="https://toptroc.com/${prefix}${canonical}">\n${alternates}\n</head>`);
   const target=path.join(out,p);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,s);
  }
  for(const name of ['site','match'])fs.writeFileSync(path.join(out,`${name}.js`),t.js(fs.readFileSync(path.join(root,'web',`${name}.js`),'utf8')));
  fs.writeFileSync(path.join(out,'messages.js'),`window.TT_MESSAGES=${JSON.stringify(Object.fromEntries(Object.entries(catalogue).map(([k,v])=>[k,v[lang]])))};\n`);
 }
 console.log(`Generated ${pages.length} pages per language (English and Español).`);
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))build();
