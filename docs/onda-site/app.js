const repo = 'https://github.com/enzoandradee16/Onda';
const latest = `${repo}/releases/latest`;
const copy = {
pt: {
 lang:'pt-BR', nav:['Início','Downloads','Recursos','Guia','Novidades','Sobre'], skip:'Ir para o conteúdo', source:'Código-fonte', privacy:'Privacidade', feedback:'Relatar problema ↗', language:'Idioma',
 title:'Sua mídia,<br><span>do seu jeito.</span>', description:'Baixe, organize e edite músicas, vídeos e imagens.', win:'Baixar para Windows', android:'Baixar para Android', facts:'Gratuito · Código aberto · Sem anúncios', alt:'ONDA no Windows: Links e fila, no tema escuro', enlarge:'Ampliar captura do ONDA',
 downloadTitle:'Escolha seu ONDA.', downloadIntro:'Os arquivos vêm das Releases oficiais no GitHub.', installer:'Instalador', portable:'Portátil', apk:'Android', installerBody:'Windows 10 ou superior · x64. Instale com atalhos e desinstalador.', portableBody:'Windows 10 ou superior · x64. Extraia o ZIP inteiro e abra Onda.exe.', apkBody:'Android 8 ou superior · ARM64. Instale o APK no seu aparelho.', get:'Baixar', releaseFiles:'Todos os arquivos e verificações SHA-256 ↗', downloadNote:'Windows: o FFmpeg é preparado no primeiro uso e precisa de internet. Os executáveis não têm assinatura digital; o Windows pode mostrar um aviso de reputação.',
 featuresTitle:'Tudo no mesmo lugar.', featuresIntro:'Ferramentas para cuidar da sua biblioteca, no PC e no celular.', features:[['Pesquisar e baixar','Encontre músicas e metadados no Deezer, Apple Music e Spotify. Adicione links à fila e escolha formato e qualidade.'],['Organizar sua biblioteca','Importe álbuns e playlists, acompanhe a fila e encontre seus arquivos no histórico, em lista ou cards.'],['Editar do seu jeito','Edite metadados e capas, converta imagens e aplique Slowed, Sped Up e Reverb com prévia.']], featureNote:'Português, espanhol e inglês. Temas claro, escuro e preto puro, cores de destaque e recursos de acessibilidade.',
 guideTitle:'Comece por aqui.', guideIntro:'O essencial para baixar e usar o ONDA.', guide:[['Como abrir no Windows?','Use o instalador ou extraia todo o pacote portátil. Na versão portátil, mantenha Onda.exe junto das pastas Onda e _runtime. O FFmpeg é baixado automaticamente no primeiro uso.'],['Como instalar no Android?','Baixe o APK e abra o arquivo. Se o Android pedir, permita a instalação pela origem utilizada. Nas próximas atualizações, o ONDA pode baixar o pacote dentro do aplicativo; a instalação depende da sua confirmação no Android.'],['Como baixar uma música?','Pesquise por artista ou música, selecione o resultado e escolha o formato. Você também pode colar um link em Links e fila e adicionar à fila.'],['De onde vem o áudio?','MP3 e M4A usam uma versão equivalente do YouTube. FLAC usa o acervo Monochrome quando há correspondência compatível. A disponibilidade varia conforme a fonte.']], fullGuide:'Documentação completa ↗',
 newsTitle:'O que há de novo.', newsIntro:'Veja a versão pública mais recente e o histórico do projeto.', releaseLink:'Ler notas da última versão ↗', history:'Ver todas as versões ↗', loading:'Consultando a versão mais recente…', unavailable:'Consulte a versão mais recente no GitHub.',
 aboutTitle:'Feito para ser útil.', aboutIntro:'Um projeto pessoal, compartilhado com quem também quer suas ferramentas de mídia no mesmo lugar.', aboutBody:'O ONDA é gratuito, de código aberto e sem anúncios. Está em desenvolvimento para Windows e Android, com sugestões e contribuições da comunidade.', contribute:'Contribuir com o projeto ↗', license:'Distribuído sob a licença GPL-2.0.',
 privacyTitle:'Privacidade do site.', privacyBody:'Este site não usa cookies de rastreamento, anúncios ou ferramentas de análise. A preferência de idioma é salva apenas neste navegador. Para mostrar a versão atual e os downloads, o site consulta a API pública do GitHub; a hospedagem e os downloads também usam os serviços do GitHub.', privacyMore:'Declaração de privacidade do GitHub ↗', localNote:'A preferência de idioma pode não ser salva se o armazenamento do navegador estiver bloqueado.'
},
es: {
 lang:'es',nav:['Inicio','Descargas','Funciones','Guía','Novedades','Acerca de'],skip:'Ir al contenido',source:'Código fuente',privacy:'Privacidad',feedback:'Informar de un problema ↗',language:'Idioma',
 title:'Tus medios,<br><span>a tu manera.</span>',description:'Descarga, organiza y edita música, vídeos e imágenes.',win:'Descargar para Windows',android:'Descargar para Android',facts:'Gratis · Código abierto · Sin anuncios',alt:'ONDA en Windows: Enlaces y cola, con tema oscuro',enlarge:'Ampliar captura de ONDA',
 downloadTitle:'Elige tu ONDA.',downloadIntro:'Los archivos provienen de las versiones oficiales en GitHub.',installer:'Instalador',portable:'Portátil',apk:'Android',installerBody:'Windows 10 o superior · x64. Instala con accesos directos y desinstalador.',portableBody:'Windows 10 o superior · x64. Extrae todo el ZIP y abre Onda.exe.',apkBody:'Android 8 o superior · ARM64. Instala el APK en tu dispositivo.',get:'Descargar',releaseFiles:'Todos los archivos y verificaciones SHA-256 ↗',downloadNote:'Windows: FFmpeg se prepara en el primer uso y necesita internet. Los ejecutables no tienen firma digital; Windows puede mostrar un aviso de reputación.',
 featuresTitle:'Todo en el mismo lugar.',featuresIntro:'Herramientas para cuidar tu biblioteca, en el PC y el móvil.',features:[['Buscar y descargar','Encuentra música y metadatos en Deezer, Apple Music y Spotify. Añade enlaces a la cola y elige formato y calidad.'],['Organizar tu biblioteca','Importa álbumes y listas de reproducción, sigue la cola y encuentra tus archivos en el historial, en lista o tarjetas.'],['Editar a tu manera','Edita metadatos y portadas, convierte imágenes y aplica Slowed, Sped Up y Reverb con vista previa.']],featureNote:'Portugués, español e inglés. Temas claro, oscuro y negro puro, colores de acento y funciones de accesibilidad.',
 guideTitle:'Empieza aquí.',guideIntro:'Lo esencial para descargar y usar ONDA.',guide:[['¿Cómo abrirlo en Windows?','Usa el instalador o extrae todo el paquete portátil. En la versión portátil, mantén Onda.exe junto a las carpetas Onda y _runtime. FFmpeg se descarga automáticamente en el primer uso.'],['¿Cómo instalarlo en Android?','Descarga el APK y abre el archivo. Si Android lo solicita, permite la instalación desde el origen utilizado. Para próximas actualizaciones, ONDA puede descargar el paquete dentro de la aplicación; la instalación requiere tu confirmación en Android.'],['¿Cómo descargar una canción?','Busca un artista o canción, selecciona el resultado y elige el formato. También puedes pegar un enlace en Enlaces y cola y añadirlo a la cola.'],['¿De dónde viene el audio?','MP3 y M4A usan una versión equivalente de YouTube. FLAC usa el catálogo de Monochrome cuando hay una coincidencia compatible. La disponibilidad varía según la fuente.']],fullGuide:'Documentación completa ↗',
 newsTitle:'Qué hay de nuevo.',newsIntro:'Consulta la versión pública más reciente y el historial del proyecto.',releaseLink:'Leer las notas de la última versión ↗',history:'Ver todas las versiones ↗',loading:'Consultando la última versión…',unavailable:'Consulta la última versión en GitHub.',
 aboutTitle:'Hecho para ser útil.',aboutIntro:'Un proyecto personal, compartido con quienes también quieren sus herramientas multimedia en el mismo lugar.',aboutBody:'ONDA es gratis, de código abierto y sin anuncios. Está en desarrollo para Windows y Android, con sugerencias y contribuciones de la comunidad.',contribute:'Contribuir al proyecto ↗',license:'Distribuido bajo la licencia GPL-2.0.',
 privacyTitle:'Privacidad del sitio.',privacyBody:'Este sitio no usa cookies de seguimiento, anuncios ni herramientas de análisis. La preferencia de idioma se guarda solo en este navegador. Para mostrar la versión actual y las descargas, consulta la API pública de GitHub; el alojamiento y las descargas también utilizan los servicios de GitHub.',privacyMore:'Declaración de privacidad de GitHub ↗'
},
en: {
 lang:'en',nav:['Home','Downloads','Features','Guide','News','About'],skip:'Skip to content',source:'Source code',privacy:'Privacy',feedback:'Report an issue ↗',language:'Language',
 title:'Your media,<br><span>your way.</span>',description:'Download, organize and edit music, videos and images.',win:'Download for Windows',android:'Download for Android',facts:'Free · Open source · No ads',alt:'ONDA on Windows: Links and queue, with the pure black theme',enlarge:'Enlarge ONDA screenshot',
 downloadTitle:'Choose your ONDA.',downloadIntro:'Files come from official GitHub Releases.',installer:'Installer',portable:'Portable',apk:'Android',installerBody:'Windows 10 or later · x64. Install with shortcuts and an uninstaller.',portableBody:'Windows 10 or later · x64. Extract the entire ZIP and open Onda.exe.',apkBody:'Android 8 or later · ARM64. Install the APK on your device.',get:'Download',releaseFiles:'All files and SHA-256 checksums ↗',downloadNote:'Windows: FFmpeg is prepared on first use and requires internet access. The executables are not digitally signed; Windows may display a reputation warning.',
 featuresTitle:'Everything in one place.',featuresIntro:'Tools to look after your library, on your PC and phone.',features:[['Search and download','Find music and metadata on Deezer, Apple Music and Spotify. Add links to the queue and choose a format and quality.'],['Organize your library','Import albums and playlists, follow the queue and find your files in history, as a list or cards.'],['Edit your way','Edit metadata and covers, convert images and apply Slowed, Sped Up and Reverb with a preview.']],featureNote:'Portuguese, Spanish and English. Light, dark and pure black themes, accent colors and accessibility features.',
 guideTitle:'Start here.',guideIntro:'The essentials for downloading and using ONDA.',guide:[['How do I open it on Windows?','Use the installer or extract the entire portable package. For the portable version, keep Onda.exe alongside the Onda and _runtime folders. FFmpeg is downloaded automatically on first use.'],['How do I install it on Android?','Download the APK and open the file. If Android asks, allow installation from the source you used. For future updates, ONDA can download the package within the app; installation requires your confirmation in Android.'],['How do I download a track?','Search for an artist or track, select a result and choose a format. You can also paste a link into Links and queue and add it to the queue.'],['Where does the audio come from?','MP3 and M4A use an equivalent version from YouTube. FLAC uses the Monochrome catalog when a compatible match is available. Availability varies by source.']],fullGuide:'Full documentation ↗',
 newsTitle:'What’s new.',newsIntro:'Find the latest public release and the project history.',releaseLink:'Read the latest release notes ↗',history:'View all releases ↗',loading:'Checking the latest release…',unavailable:'Find the latest release on GitHub.',
 aboutTitle:'Made to be useful.',aboutIntro:'A personal project, shared with anyone who also wants their media tools in one place.',aboutBody:'ONDA is free, open source and ad-free. It is in development for Windows and Android, with suggestions and contributions from the community.',contribute:'Contribute to the project ↗',license:'Distributed under the GPL-2.0 license.',
 privacyTitle:'Website privacy.',privacyBody:'This website uses no tracking cookies, ads or analytics tools. Your language preference is saved only in this browser. To show the current version and downloads, the site queries the public GitHub API; hosting and downloads also use GitHub services.',privacyMore:'GitHub privacy statement ↗'
}
};
const routes = ['home','downloads','features','guide','news','about','privacy'];
let language = 'pt';
try { const saved = localStorage.getItem('onda-site-language'); if (Object.hasOwn(copy,saved)) language=saved; } catch {}
let release = null;
let releaseDone = false;
const main = document.querySelector('main');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function assetUrl(kind) {
 const patterns = {installer:/Setup-Windows-x64\.exe$/i,portable:/(?:Portable|Portatil)-Windows-x64\.zip$/i,apk:/Android-.*arm64-v8a\.apk$/i};
 const asset=release?.assets?.find(a=>patterns[kind].test(a.name));
 const url=asset?.browser_download_url;
 return url?.startsWith(`${repo}/releases/download/`) ? url : latest;
}
function releaseLabel(t) {
 if (!release) return `<p class="release" role="status">${releaseDone?t.unavailable:t.loading}</p>`;
 return `<p class="release" role="status"><span class="badge">${esc(release.tag_name)}</span><time datetime="${esc(release.published_at)}">${esc(new Intl.DateTimeFormat(t.lang,{dateStyle:'long'}).format(new Date(release.published_at)))}</time></p>`;
}
function render() {
 const t=copy[language];
 const route=routes.includes(location.hash.slice(1))?location.hash.slice(1):'home';
 document.documentElement.lang=t.lang;
 document.querySelector('#language').value=language;
 document.querySelector('#language').setAttribute('aria-label',t.language);
 document.querySelector('nav').setAttribute('aria-label',t.nav[0]);
 document.querySelectorAll('[data-text]').forEach(el=>el.textContent=t[el.dataset.text]);
 document.querySelectorAll('[data-nav]').forEach((el,i)=>{el.textContent=t.nav[i];if(el.dataset.nav===route)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
 document.title=`ONDA — ${route==='home'?t.description:t.nav[routes.indexOf(route)]||t.privacy}`;
 document.querySelector('meta[name=description]').content=`ONDA. ${t.description} ${t.facts}.`;
 const link=(href,text,cls='text-link')=>`<a class="${cls}" href="${esc(href)}">${esc(text)}</a>`;
 const doc=`${repo}/blob/master/README${language==='pt'?'':'.'+language}.md`;
 const heading=(title,intro)=>`<h1>${title}</h1><p class="intro">${intro}</p>`;
 let body='';
 if(route==='home') {
  body=`<section class="hero"><div><p class="eyebrow">Windows & Android</p><h1>${t.title}</h1><p class="intro">${t.description}</p><div class="actions">${link('#downloads',`⊞ ${t.win}`,'button')}${link(assetUrl('apk'),`↓ ${t.android}`,'button outline')}</div><p class="facts">${t.facts}</p></div><a class="shot" href="assets/app-${language}.png" target="_blank" rel="noopener" aria-label="${t.enlarge}"><img src="assets/app-${language}.png" alt="${t.alt}" width="1919" height="1008" fetchpriority="high"></a></section>`;
 } else if(route==='downloads') {
  body=heading(t.downloadTitle,t.downloadIntro)+releaseLabel(t)+`<div class="grid">${['installer','portable','apk'].map(k=>`<article class="card"><h2>${t[k]}</h2><p>${t[k+'Body']}</p>${link(assetUrl(k),t.get,'button'+(k==='installer'?'':' outline'))}</article>`).join('')}</div><p>${link(latest,t.releaseFiles)}</p><p class="prose small">${t.downloadNote}</p>`;
 } else if(route==='features') {
  body=heading(t.featuresTitle,t.featuresIntro)+`<div class="grid">${t.features.map(([a,b])=>`<article class="card"><h2>${a}</h2><p>${b}</p></article>`).join('')}</div><div class="prose"><p>${t.featureNote}</p></div>`;
 } else if(route==='guide') {
  body=heading(t.guideTitle,t.guideIntro)+t.guide.map(([a,b])=>`<details><summary>${a}</summary><p>${b}</p></details>`).join('')+`<p>${link(doc,t.fullGuide)}</p>`;
 } else if(route==='news') {
  body=heading(t.newsTitle,t.newsIntro)+releaseLabel(t)+`<div class="actions">${link(latest,t.releaseLink,'button')}${link(repo+'/releases',t.history,'button outline')}</div>`;
 } else if(route==='about') {
  body=heading(t.aboutTitle,t.aboutIntro)+`<div class="prose"><p>${t.aboutBody}</p><p>${t.license}</p></div><div class="actions">${link(repo+'/blob/master/CONTRIBUTING.md',t.contribute,'button outline')}</div>`;
 } else body=heading(t.privacyTitle,'')+`<div class="prose"><p>${t.privacyBody}</p>${link('https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement',t.privacyMore)}</div>`;
 main.innerHTML=route==='home'?body:`<section class="page">${body}</section>`;
}
document.querySelector('#language').addEventListener('change',e=>{language=e.target.value;try{localStorage.setItem('onda-site-language',language);}catch{}render();});
document.querySelector('.skip').addEventListener('click',e=>{e.preventDefault();main.focus();});
window.addEventListener('hashchange',()=>{render();main.focus({preventScroll:true});window.scrollTo(0,0);});
render();
fetch('https://api.github.com/repos/enzoandradee16/Onda/releases/latest',{headers:{Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(10000)})
 .then(r=>{if(!r.ok)throw Error('Release unavailable');return r.json();})
 .then(data=>{if(!data.draft&&!data.prerelease&&data.published_at&&Array.isArray(data.assets))release=data;})
 .catch(()=>{})
 .finally(()=>{releaseDone=true;render();});

