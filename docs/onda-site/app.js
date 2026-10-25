const repo = "https://github.com/enzoandradee16/Onda";
const latest = `${repo}/releases/latest`;
const copy = {
  pt: {
    emulator: "Android para emulador",
    emulatorBody: "Android 8 ou superior · x86_64. Para emuladores compatíveis, como BlueStacks.",
    visualTitle: "Reprodução, com outra cara.",
    visualIntro: "Jukebox infinito, efeitos, letras sincronizadas e um player que acompanha sua música.",
    galleryTitle: "Seu player. Em cada tela.",
    galleryIntro: "Da barra compacta à letra em tela cheia, com a capa do álbum sempre por perto.",
    playerLabel: "Player no Android",
    lyricsLabel: "Letras em tela cheia",
    miniLabel: "Miniplayer no Windows",
    emulatorDownload: "Baixar APK x86_64 (emulador)",
    visualAlt: "Captura do ONDA no Windows: pesquisa de músicas no tema preto puro",
    androidSearchAlt: "Pesquisa de músicas no ONDA para Android, no tema preto puro",
    closeImage: "Fechar imagem",
    moreTitle: "Conheça mais do ONDA.",
    moreIntro: "Organize seus downloads, edite suas músicas e cuide das suas imagens. Clique nas capturas para ver os detalhes.",
    moreLabels: ["Editar metadados no Windows", "Fila de downloads no Windows", "Efeitos de áudio no Windows", "Conversão de imagens no Windows", "Álbuns e playlists no Android", "Downloads no Android"],

    lang: "pt-BR",
    nav: ["Início", "Downloads", "Recursos", "Guia", "Novidades", "Sobre"],
    skip: "Ir para o conteúdo",
    source: "Código-fonte",
    privacy: "Privacidade",
    feedback: "Relatar problema ↗",
    language: "Idioma",
    title: "Sua mídia,<br><span>do seu jeito.</span>",
    description: "Baixe, organize e edite músicas, vídeos e imagens.",
    win: "Baixar para Windows",
    android: "Baixar para Android",
    facts: "Gratuito · Código aberto · Sem anúncios",
    alt: "ONDA no Windows: Links e fila, no tema escuro",
    enlarge: "Ampliar captura do ONDA",
    downloadTitle: "Escolha seu ONDA.",
    downloadIntro: "Os arquivos vêm das Releases oficiais no GitHub.",
    installer: "Instalador",
    portable: "Portátil",
    apk: "Android",
    installerBody: "Windows 10 ou superior · x64. Instale com atalhos e desinstalador.",
    portableBody: "Windows 10 ou superior · x64. Extraia o ZIP inteiro e abra Onda.exe.",
    apkBody: "Android 8 ou superior · ARM64. Instale o APK no seu aparelho.",
    get: "Baixar",
    releaseFiles: "Todos os arquivos e verificações SHA-256 ↗",
    downloadNote:
      "Windows: o FFmpeg é preparado no primeiro uso e precisa de internet. Os executáveis não têm assinatura digital; o Windows pode mostrar um aviso de reputação.",
    featuresTitle: "Tudo no mesmo lugar.",
    featuresIntro: "Ferramentas para cuidar da sua biblioteca, no PC e no celular.",
    features: [
      [
        "Pesquisar e baixar",
        "Encontre músicas e metadados no Deezer, Apple Music e Spotify. Adicione links à fila e escolha formato e qualidade.",
      ],
      [
        "Organizar sua biblioteca",
        "Importe álbuns e playlists, acompanhe a fila e encontre seus arquivos no histórico, em lista ou cards.",
      ],
      [
        "Editar do seu jeito",
        "Edite metadados e capas, converta imagens e aplique Slowed, Sped Up e Reverb com prévia.",
      ],
    ],
    featureNote:
      "Português, espanhol e inglês. Temas claro, escuro e preto puro, cores de destaque e recursos de acessibilidade.",
    guideTitle: "Comece por aqui.",
    guideIntro: "O essencial para baixar e usar o ONDA.",
    guide: [
      [
        "Como abrir no Windows?",
        "Use o instalador ou extraia todo o pacote portátil. Na versão portátil, mantenha Onda.exe junto das pastas Onda e _runtime. O FFmpeg é baixado automaticamente no primeiro uso.",
      ],
      [
        "Como instalar no Android?",
        "Baixe o APK e abra o arquivo. Se o Android pedir, permita a instalação pela origem utilizada. Nas próximas atualizações, o ONDA pode baixar o pacote dentro do aplicativo; a instalação depende da sua confirmação no Android.",
      ],
      [
        "Como baixar uma música?",
        "Pesquise por artista ou música, selecione o resultado e escolha o formato. Você também pode colar um link em Links e fila e adicionar à fila.",
      ],
      [
        "De onde vem o áudio?",
        "MP3 e M4A usam uma versão equivalente do YouTube. FLAC usa o acervo Monochrome quando há correspondência compatível. A disponibilidade varia conforme a fonte.",
      ],
    ],
    fullGuide: "Documentação completa ↗",
    newsTitle: "O que há de novo.",
    newsIntro: "Veja a versão pública mais recente e o histórico do projeto.",
    releaseLink: "Ler notas da última versão ↗",
    history: "Ver todas as versões ↗",
    loading: "Consultando a versão mais recente…",
    unavailable: "Consulte a versão mais recente no GitHub.",
    aboutTitle: "Feito para ser útil.",
    aboutIntro:
      "Um projeto pessoal, compartilhado com quem também quer suas ferramentas de mídia no mesmo lugar.",
    aboutBody:
      "O ONDA é gratuito, de código aberto e sem anúncios. Está em desenvolvimento para Windows e Android, com sugestões e contribuições da comunidade.",
    contribute: "Contribuir com o projeto ↗",
    license: "Distribuído sob a licença GPL-2.0.",
    privacyTitle: "Privacidade do site.",
    privacyBody:
      "Este site não usa cookies de rastreamento, anúncios ou ferramentas de análise. As preferências de idioma e tema são salvas apenas neste navegador. Para mostrar a versão atual e os downloads, o site consulta a API pública do GitHub; a hospedagem e os downloads também usam os serviços do GitHub.",
    privacyMore: "Declaração de privacidade do GitHub ↗",
    localNote:
      "A preferência de idioma pode não ser salva se o armazenamento do navegador estiver bloqueado.",
  },
  es: {
    emulator: "Android para emulador",
    emulatorBody: "Android 8 o superior · x86_64. Para emuladores compatibles, como BlueStacks.",
    visualTitle: "La reproducción tiene nueva cara.",
    visualIntro: "Jukebox infinito, efectos, letras sincronizadas y un reproductor que acompaña tu música.",
    galleryTitle: "Tu reproductor. En cada pantalla.",
    galleryIntro: "Desde la barra compacta hasta las letras a pantalla completa, con la portada del álbum siempre cerca.",
    playerLabel: "Reproductor en Android",
    lyricsLabel: "Letras a pantalla completa",
    miniLabel: "Minirreproductor en Windows",
    emulatorDownload: "Descargar APK x86_64 (emulador)",
    visualAlt: "Captura de ONDA en Windows: búsqueda de música con tema negro puro",
    androidSearchAlt: "Búsqueda de música en ONDA para Android, con tema negro puro",
    closeImage: "Cerrar imagen",
    moreTitle: "Descubre más de ONDA.",
    moreIntro: "Organiza tus descargas, edita tu música y trabaja con tus imágenes. Haz clic en las capturas para ver los detalles.",
    moreLabels: ["Editar metadatos en Windows", "Cola de descargas en Windows", "Efectos de audio en Windows", "Conversión de imágenes en Windows", "Álbumes y playlists en Android", "Descargas en Android"],

    lang: "es",
    nav: ["Inicio", "Descargas", "Funciones", "Guía", "Novedades", "Acerca de"],
    skip: "Ir al contenido",
    source: "Código fuente",
    privacy: "Privacidad",
    feedback: "Informar de un problema ↗",
    language: "Idioma",
    title: "Tus medios,<br><span>a tu manera.</span>",
    description: "Descarga, organiza y edita música, vídeos e imágenes.",
    win: "Descargar para Windows",
    android: "Descargar para Android",
    facts: "Gratis · Código abierto · Sin anuncios",
    alt: "ONDA en Windows: Enlaces y cola, con tema oscuro",
    enlarge: "Ampliar captura de ONDA",
    downloadTitle: "Elige tu ONDA.",
    downloadIntro: "Los archivos provienen de las versiones oficiales en GitHub.",
    installer: "Instalador",
    portable: "Portátil",
    apk: "Android",
    installerBody:
      "Windows 10 o superior · x64. Instala con accesos directos y desinstalador.",
    portableBody: "Windows 10 o superior · x64. Extrae todo el ZIP y abre Onda.exe.",
    apkBody: "Android 8 o superior · ARM64. Instala el APK en tu dispositivo.",
    get: "Descargar",
    releaseFiles: "Todos los archivos y verificaciones SHA-256 ↗",
    downloadNote:
      "Windows: FFmpeg se prepara en el primer uso y necesita internet. Los ejecutables no tienen firma digital; Windows puede mostrar un aviso de reputación.",
    featuresTitle: "Todo en el mismo lugar.",
    featuresIntro: "Herramientas para cuidar tu biblioteca, en el PC y el móvil.",
    features: [
      [
        "Buscar y descargar",
        "Encuentra música y metadatos en Deezer, Apple Music y Spotify. Añade enlaces a la cola y elige formato y calidad.",
      ],
      [
        "Organizar tu biblioteca",
        "Importa álbumes y listas de reproducción, sigue la cola y encuentra tus archivos en el historial, en lista o tarjetas.",
      ],
      [
        "Editar a tu manera",
        "Edita metadatos y portadas, convierte imágenes y aplica Slowed, Sped Up y Reverb con vista previa.",
      ],
    ],
    featureNote:
      "Portugués, español e inglés. Temas claro, oscuro y negro puro, colores de acento y funciones de accesibilidad.",
    guideTitle: "Empieza aquí.",
    guideIntro: "Lo esencial para descargar y usar ONDA.",
    guide: [
      [
        "¿Cómo abrirlo en Windows?",
        "Usa el instalador o extrae todo el paquete portátil. En la versión portátil, mantén Onda.exe junto a las carpetas Onda y _runtime. FFmpeg se descarga automáticamente en el primer uso.",
      ],
      [
        "¿Cómo instalarlo en Android?",
        "Descarga el APK y abre el archivo. Si Android lo solicita, permite la instalación desde el origen utilizado. Para próximas actualizaciones, ONDA puede descargar el paquete dentro de la aplicación; la instalación requiere tu confirmación en Android.",
      ],
      [
        "¿Cómo descargar una canción?",
        "Busca un artista o canción, selecciona el resultado y elige el formato. También puedes pegar un enlace en Enlaces y cola y añadirlo a la cola.",
      ],
      [
        "¿De dónde viene el audio?",
        "MP3 y M4A usan una versión equivalente de YouTube. FLAC usa el catálogo de Monochrome cuando hay una coincidencia compatible. La disponibilidad varía según la fuente.",
      ],
    ],
    fullGuide: "Documentación completa ↗",
    newsTitle: "Qué hay de nuevo.",
    newsIntro: "Consulta la versión pública más reciente y el historial del proyecto.",
    releaseLink: "Leer las notas de la última versión ↗",
    history: "Ver todas las versiones ↗",
    loading: "Consultando la última versión…",
    unavailable: "Consulta la última versión en GitHub.",
    aboutTitle: "Hecho para ser útil.",
    aboutIntro:
      "Un proyecto personal, compartido con quienes también quieren sus herramientas multimedia en el mismo lugar.",
    aboutBody:
      "ONDA es gratis, de código abierto y sin anuncios. Está en desarrollo para Windows y Android, con sugerencias y contribuciones de la comunidad.",
    contribute: "Contribuir al proyecto ↗",
    license: "Distribuido bajo la licencia GPL-2.0.",
    privacyTitle: "Privacidad del sitio.",
    privacyBody:
      "Este sitio no usa cookies de seguimiento, anuncios ni herramientas de análisis. Las preferencias de idioma y tema se guardan solo en este navegador. Para mostrar la versión actual y las descargas, consulta la API pública de GitHub; el alojamiento y las descargas también utilizan los servicios de GitHub.",
    privacyMore: "Declaración de privacidad de GitHub ↗",
  },
  en: {
    emulator: "Android for emulators",
    emulatorBody: "Android 8 or later · x86_64. For compatible emulators, such as BlueStacks.",
    visualTitle: "A fresh look for playback.",
    visualIntro: "Infinite Jukebox, effects, synced lyrics and a player that follows your music.",
    galleryTitle: "Your player. On every screen.",
    galleryIntro: "From the compact bar to full-screen lyrics, with album artwork close at hand.",
    playerLabel: "Android player",
    lyricsLabel: "Full-screen lyrics",
    miniLabel: "Windows miniplayer",
    emulatorDownload: "Download x86_64 APK (emulator)",
    visualAlt: "ONDA screenshot on Windows: music search with the pure black theme",
    androidSearchAlt: "Music search in ONDA for Android, with the pure black theme",
    closeImage: "Close image",
    moreTitle: "Discover more of ONDA.",
    moreIntro: "Organize downloads, edit your music and work with your images. Click the screenshots for a closer look.",
    moreLabels: ["Edit metadata on Windows", "Download queue on Windows", "Audio effects on Windows", "Image conversion on Windows", "Albums and playlists on Android", "Downloads on Android"],

    lang: "en",
    nav: ["Home", "Downloads", "Features", "Guide", "News", "About"],
    skip: "Skip to content",
    source: "Source code",
    privacy: "Privacy",
    feedback: "Report an issue ↗",
    language: "Language",
    title: "Your media,<br><span>your way.</span>",
    description: "Download, organize and edit music, videos and images.",
    win: "Download for Windows",
    android: "Download for Android",
    facts: "Free · Open source · No ads",
    alt: "ONDA on Windows: Links and queue, with the pure black theme",
    enlarge: "Enlarge ONDA screenshot",
    downloadTitle: "Choose your ONDA.",
    downloadIntro: "Files come from official GitHub Releases.",
    installer: "Installer",
    portable: "Portable",
    apk: "Android",
    installerBody:
      "Windows 10 or later · x64. Install with shortcuts and an uninstaller.",
    portableBody: "Windows 10 or later · x64. Extract the entire ZIP and open Onda.exe.",
    apkBody: "Android 8 or later · ARM64. Install the APK on your device.",
    get: "Download",
    releaseFiles: "All files and SHA-256 checksums ↗",
    downloadNote:
      "Windows: FFmpeg is prepared on first use and requires internet access. The executables are not digitally signed; Windows may display a reputation warning.",
    featuresTitle: "Everything in one place.",
    featuresIntro: "Tools to look after your library, on your PC and phone.",
    features: [
      [
        "Search and download",
        "Find music and metadata on Deezer, Apple Music and Spotify. Add links to the queue and choose a format and quality.",
      ],
      [
        "Organize your library",
        "Import albums and playlists, follow the queue and find your files in history, as a list or cards.",
      ],
      [
        "Edit your way",
        "Edit metadata and covers, convert images and apply Slowed, Sped Up and Reverb with a preview.",
      ],
    ],
    featureNote:
      "Portuguese, Spanish and English. Light, dark and pure black themes, accent colors and accessibility features.",
    guideTitle: "Start here.",
    guideIntro: "The essentials for downloading and using ONDA.",
    guide: [
      [
        "How do I open it on Windows?",
        "Use the installer or extract the entire portable package. For the portable version, keep Onda.exe alongside the Onda and _runtime folders. FFmpeg is downloaded automatically on first use.",
      ],
      [
        "How do I install it on Android?",
        "Download the APK and open the file. If Android asks, allow installation from the source you used. For future updates, ONDA can download the package within the app; installation requires your confirmation in Android.",
      ],
      [
        "How do I download a track?",
        "Search for an artist or track, select a result and choose a format. You can also paste a link into Links and queue and add it to the queue.",
      ],
      [
        "Where does the audio come from?",
        "MP3 and M4A use an equivalent version from YouTube. FLAC uses the Monochrome catalog when a compatible match is available. Availability varies by source.",
      ],
    ],
    fullGuide: "Full documentation ↗",
    newsTitle: "What’s new.",
    newsIntro: "Find the latest public release and the project history.",
    releaseLink: "Read the latest release notes ↗",
    history: "View all releases ↗",
    loading: "Checking the latest release…",
    unavailable: "Find the latest release on GitHub.",
    aboutTitle: "Made to be useful.",
    aboutIntro:
      "A personal project, shared with anyone who also wants their media tools in one place.",
    aboutBody:
      "ONDA is free, open source and ad-free. It is in development for Windows and Android, with suggestions and contributions from the community.",
    contribute: "Contribute to the project ↗",
    license: "Distributed under the GPL-2.0 license.",
    privacyTitle: "Website privacy.",
    privacyBody:
      "This website uses no tracking cookies, ads or analytics tools. Your language and theme preferences are saved only in this browser. To show the current version and downloads, the site queries the public GitHub API; hosting and downloads also use GitHub services.",
    privacyMore: "GitHub privacy statement ↗",
  },
};
const routes = ["home", "downloads", "features", "guide", "news", "about", "privacy"];
let language = "pt";
try {
  const saved = localStorage.getItem("onda-site-language");
  if (Object.hasOwn(copy, saved)) language = saved;
} catch {}
let release = null;
let releaseDone = false;
const main = document.querySelector("main");
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
function assetUrl(kind) {
  const patterns = {
    installer: /Setup-Windows-x64\.exe$/i,
    portable: /(?:Portable|Portatil)-Windows-x64\.zip$/i,
    apk: /Android-.*arm64-v8a\.apk$/i,
    emulator: /Android-.*x86_64\.apk$/i,
  };
  const asset = release?.assets?.find((a) => patterns[kind].test(a.name));
  const url = asset?.browser_download_url;
  return url?.startsWith(`${repo}/releases/download/`) ? url : latest;
}
function releaseLabel(t) {
  if (!release)
    return /* HTML */ `
      <p class="release" role="status">${releaseDone ? t.unavailable : t.loading}</p>
    `;
  return /* HTML */ `
    <p class="release" role="status">
      <span class="badge">${esc(release.tag_name)}</span>
      <time datetime="${esc(release.published_at)}">
        ${esc(
          new Intl.DateTimeFormat(t.lang, { dateStyle: "long" }).format(
            new Date(release.published_at),
          ),
        )}
      </time>
    </p>
  `;
}
function platformIcon(platform) {
  if (platform === "windows") {
    return /* HTML */ `
      <svg class="platform-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M2 4.5 10.5 3.3v8H2zm10-1.5L22 1.6v9.7h-10zM2 12.8h8.5v8L2 19.6zm10 0h10v9.6L12 21z" />
      </svg>
    `;
  }

  if (platform === "android") {
    return /* HTML */ `
      <svg class="platform-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path fill-rule="evenodd" d="M6 8a6 6 0 0 1 12 0zm3-2h1V5H9zm5 0h1V5h-1z" />
        <path d="M6 9h12v9a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1z" />
        <path d="m8 3-1.4-2m9.4 2 1.4-2" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
        <rect x="2.5" y="9" width="2.5" height="8" rx="1.25" />
        <rect x="19" y="9" width="2.5" height="8" rx="1.25" />
        <rect x="8" y="17" width="2.5" height="6" rx="1.25" />
        <rect x="13.5" y="17" width="2.5" height="6" rx="1.25" />
      </svg>
    `;
  }

  return "";
}

const themeButton = document.querySelector("#theme-toggle");
const themeLabels = {
  pt: ["Modo claro", "Modo escuro", "Pesquisa de músicas no ONDA para Windows, no tema claro"],
  es: ["Modo claro", "Modo oscuro", "Búsqueda de música en ONDA para Windows, en tema claro"],
  en: ["Light mode", "Dark mode", "Music search in ONDA for Windows, in light mode"],
};
function updateTheme() {
  const light = document.documentElement.dataset.theme === "light";
  const themeLabel = themeLabels[language][light ? 1 : 0];
  themeButton.setAttribute("aria-label", themeLabel);
  themeButton.title = themeLabel;
  themeButton.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${light
    ? '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>'
    : '<path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z"/>'}</svg>`;
  themeButton.setAttribute("aria-pressed", String(light));
  document.querySelector('meta[name="theme-color"]').content = light ? "#f3f6fa" : "#0d1318";
  const desktop = main.querySelector(".hero-screens .shot, .feature-search .feature-desktop, .guide-search .feature-desktop");
  if (desktop) {
    const image = desktop.querySelector("img");
    const source = `assets/desktop-search${light ? "-light" : ""}.png`;
    desktop.href = source;
    image.src = source;
    image.alt = light ? themeLabels[language][2] : copy[language].visualAlt;
    desktop.setAttribute("aria-label", `${copy[language].enlarge}: ${image.alt}`);
    image.height = 1015;
  }
  const phone = main.querySelector(".hero-screens .phone-shot, .feature-search .feature-phone, .guide-search .feature-phone");
  if (phone) {
    const image = phone.querySelector("img");
    const source = `assets/android-search${light ? "-light" : ""}-cropped.png`;
    const alt = light ? themeLabels[language][2].replace("Windows", "Android") : copy[language].androidSearchAlt;
    phone.href = source;
    phone.setAttribute("aria-label", `${copy[language].enlarge}: ${alt}`);
    image.src = source;
    image.alt = alt;
  }
}
themeButton.addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem("onda-site-theme", theme); } catch {}
  updateTheme();
});

function render() {
  const t = copy[language];
  const route = routes.includes(location.hash.slice(1)) ? location.hash.slice(1) : "home";
  document.documentElement.lang = t.lang;
  document.querySelector("#language").value = language;
  document.querySelector("#language").setAttribute("aria-label", t.language);
  document.querySelector("nav").setAttribute("aria-label", t.nav[0]);
  document
    .querySelectorAll("[data-text]")
    .forEach((el) => (el.textContent = t[el.dataset.text]));
  document.querySelectorAll("[data-nav]").forEach((el, i) => {
    el.textContent = t.nav[i];
    if (el.dataset.nav === route) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  document.title = `ONDA — ${route === "home" ? t.description : t.nav[routes.indexOf(route)] || t.privacy}`;
  document.querySelector("meta[name=description]").content =
    `ONDA. ${t.description} ${t.facts}.`;
  const link = (href, text, cls = "text-link", platform = "") => /* HTML */ `
    <a class="${cls}" href="${esc(href)}">
      ${platformIcon(platform)}${esc(text)}
    </a>
  `;
  const doc = `${repo}/blob/master/README${language === "pt" ? "" : "." + language}.md`;
  const heading = (title, intro) => /* HTML */ `
    <h1>${title}</h1>
    <p class="intro">${intro}</p>
  `;
  let body = "";
  if (route === "home") {
    body = /* HTML */ `
      <section class="hero">
        <div>
          <p class="eyebrow"><span class="live-dot" aria-hidden="true"></span> Windows & Android</p>
          <h1>${t.title}</h1>
          <p class="intro">${t.description}</p>
          <div class="actions">
            ${link("#downloads", t.win, "button", "windows")}${link(
              assetUrl("apk"),
              t.android,
              "button outline",
              "android",
            )}
          </div>
          <p class="facts">${t.facts}</p>
          ${link(assetUrl("emulator"), t.emulatorDownload, "emulator-link")}
        </div>
        <div class="hero-screens">
        <a
          class="shot"
          href="assets/desktop-search.png"
          target="_blank"
          rel="noopener"
          aria-label="${t.enlarge}"
        >
          <img
            src="assets/desktop-search.png"
            alt="${t.visualAlt}"
            width="1920"
            height="1015"
            fetchpriority="high"
          />
        </a>
        <a class="phone-shot" href="assets/android-search-cropped.png" target="_blank" rel="noopener" aria-label="${t.enlarge}: ${t.androidSearchAlt}">
          <img src="assets/android-search-cropped.png" alt="${t.androidSearchAlt}" width="576" height="1184" />
        </a>
        </div>
      </section>
      <section class="showcase playback-showcase" aria-labelledby="visual-title">
        <div class="section-heading"><p class="eyebrow">ONDA</p><h2 id="visual-title">${t.visualTitle}</h2><p>${t.visualIntro}</p></div>
        <div class="gallery">
          <figure class="gallery-player"><a href="assets/android-player.png" target="_blank" rel="noopener"><img src="assets/android-player.png" alt="${t.playerLabel}" width="576" height="1193" loading="lazy"></a><figcaption>${t.playerLabel}</figcaption></figure>
          <figure class="gallery-lyrics"><a href="assets/android-lyrics.png" target="_blank" rel="noopener"><img src="assets/android-lyrics.png" alt="${t.lyricsLabel}" loading="lazy"></a><figcaption>${t.lyricsLabel}</figcaption></figure>
          <div class="gallery-detail"><h3>${t.galleryTitle}</h3><p>${t.galleryIntro}</p><figure><a href="assets/desktop-miniplayer.png" target="_blank" rel="noopener"><img src="assets/desktop-miniplayer.png" alt="${t.miniLabel}" width="557" height="454" loading="lazy"></a><figcaption>${t.miniLabel}</figcaption></figure></div>
        </div>
      </section>
    `;
    body += /* HTML */ `
      <section class="showcase" aria-labelledby="more-screens-title">
        <div class="section-heading"><p class="eyebrow">Windows & Android</p><h2 id="more-screens-title">${t.moreTitle}</h2><p>${t.moreIntro}</p></div>
        <div class="gallery more-desktop">
          ${[['desktop-metadata.png',1005],['desktop-downloads.png',1014],['desktop-effects.png',1016],['desktop-images.png',1015]].map(([file,height],index) => `
            <figure><a href="assets/${file}" aria-label="${t.enlarge}: ${t.moreLabels[index]}"><img src="assets/${file}" alt="${t.moreLabels[index]}" width="1920" height="${height}" loading="lazy" decoding="async"></a><figcaption>${t.moreLabels[index]}</figcaption></figure>
          `).join('')}
        </div>
        <div class="gallery more-mobile">
          ${['android-library.png','android-downloads.png'].map((file,index) => `
            <figure><a href="assets/${file}" aria-label="${t.enlarge}: ${t.moreLabels[index+4]}"><img src="assets/${file}" alt="${t.moreLabels[index+4]}" width="576" height="1193" loading="lazy" decoding="async"></a><figcaption>${t.moreLabels[index+4]}</figcaption></figure>
          `).join('')}
        </div>
      </section>
    `;
  } else if (route === "downloads") {
    body =
      heading(t.downloadTitle, t.downloadIntro) +
      releaseLabel(t) +
      /* HTML */ `
        <div class="grid downloads-grid">
          ${["installer", "portable", "apk", "emulator"]
            .map(
              (k) => /* HTML */ `
                <article class="card">
                  <h2>${t[k]}</h2>
                  <p>${t[k + "Body"]}</p>
                  ${link(
                    assetUrl(k),
                    t.get,
                    "button" + (k === "installer" ? "" : " outline"),
                    ["apk", "emulator"].includes(k) ? "android" : "windows",
                  )}
                </article>
              `,
            )
            .join("")}
        </div>
        <p>${link(latest, t.releaseFiles)}</p>
        <p class="prose small">${t.downloadNote}</p>
      `;
  } else if (route === "features") {
    const preview = (file, alt, cls = "", width = 1920, height = 1015) => `
      <a data-preview class="${cls}" href="assets/${file}" aria-label="${t.enlarge}: ${alt}">
        <img src="assets/${file}" alt="${alt}" width="${width}" height="${height}" loading="lazy" decoding="async">
      </a>`;
    body = heading(t.featuresTitle, t.featuresIntro) + `
      <div class="features-showcase">
        <article class="feature-story">
          <div class="feature-copy"><span class="feature-number">01 / Windows & Android</span>
            <h2>${t.features[0][0]}</h2><p>${t.features[0][1]}</p>
            <div class="feature-tags"><span>Deezer</span><span>Apple Music</span><span>Spotify</span></div>
          </div>
          <div class="feature-media feature-search">
            ${preview(document.documentElement.dataset.theme === "light" ? "desktop-search-light.png" : "desktop-search.png", t.visualAlt, "feature-desktop")}
            ${preview(document.documentElement.dataset.theme === "light" ? "android-search-light-cropped.png" : "android-search-cropped.png", t.androidSearchAlt, "feature-phone", 576, 1184)}
          </div>
        </article>
        <article class="feature-story feature-reverse">
          <div class="feature-copy"><span class="feature-number">02 / Windows & Android</span>
            <h2>${t.features[1][0]}</h2><p>${t.features[1][1]}</p>
          </div>
          <div class="feature-media">
            ${preview("desktop-downloads.png", t.moreLabels[1], "feature-desktop", 1920, 1014)}
            ${preview("android-library.png", t.moreLabels[4], "feature-phone", 576, 1193)}
          </div>
        </article>
        <article class="feature-editor">
          <div class="feature-copy"><span class="feature-number">03 / ONDA</span>
            <h2>${t.features[2][0]}</h2><p>${t.features[2][1]}</p>
          </div>
          <div class="feature-tools">
            ${[["desktop-metadata.png", 0, 1005], ["desktop-effects.png", 2, 1016], ["desktop-images.png", 3, 1015]].map(([file, index, height]) => `
              <figure>${preview(file, t.moreLabels[index], "", 1920, height)}<figcaption>${t.moreLabels[index]}</figcaption></figure>`).join("")}
          </div>
        </article>
        <aside class="feature-personal"><span class="feature-number">ONDA</span><p>${t.featureNote}</p></aside>
      </div>`;
  } else if (route === "guide") {
    const light = document.documentElement.dataset.theme === "light";
    const guideImage = (file, alt, cls = "", width = 1920, height = 1015) => `
      <a data-preview class="${cls}" href="assets/${file}" aria-label="${t.enlarge}: ${alt}">
        <img src="assets/${file}" alt="${alt}" width="${width}" height="${height}" loading="lazy" decoding="async">
      </a>`;
    body = heading(t.guideTitle, t.guideIntro) + `
      <div class="features-showcase guide-showcase">
        <div class="guide-platforms">
          <article class="guide-platform">
            <div class="guide-platform-heading">${platformIcon("windows")}<span class="feature-number">01 / Windows</span></div>
            <div class="feature-copy"><h2>${t.guide[0][0]}</h2><p>${t.guide[0][1]}</p></div>
            ${guideImage("desktop-downloads.png", t.moreLabels[1], "guide-windows", 1920, 1014)}
            ${link(assetUrl("installer"), t.win, "button", "windows")}
          </article>
          <article class="guide-platform">
            <div class="guide-platform-heading">${platformIcon("android")}<span class="feature-number">02 / Android</span></div>
            <div class="feature-copy"><h2>${t.guide[1][0]}</h2><p>${t.guide[1][1]}</p></div>
            ${guideImage("android-downloads.png", t.moreLabels[5], "guide-android", 576, 1193)}
            ${link(assetUrl("apk"), t.android, "button outline", "android")}
          </article>
        </div>
        <article class="feature-story guide-search">
          <div class="feature-copy"><span class="feature-number">03 / ONDA</span>
            <h2>${t.guide[2][0]}</h2><p>${t.guide[2][1]}</p>
          </div>
          <div class="feature-media">
            ${guideImage(light ? "desktop-search-light.png" : "desktop-search.png", light ? themeLabels[language][2] : t.visualAlt, "feature-desktop")}
            ${guideImage(light ? "android-search-light-cropped.png" : "android-search-cropped.png", t.androidSearchAlt, "feature-phone", 576, 1184)}
          </div>
        </article>
        <aside class="guide-source">
          <span class="feature-number">04 / ONDA</span><h2>${t.guide[3][0]}</h2><p>${t.guide[3][1]}</p>
        </aside>
        <div class="guide-documentation">${link(doc, t.fullGuide, "button outline")}</div>
      </div>`;
  } else if (route === "news") {
    body =
      heading(t.newsTitle, t.newsIntro) +
      releaseLabel(t) +
      /* HTML */ `
        <div class="actions">
          ${link(latest, t.releaseLink, "button")}${link(
            repo + "/releases",
            t.history,
            "button outline",
          )}
        </div>
      `;
  } else if (route === "about") {
    body =
      heading(t.aboutTitle, t.aboutIntro) +
      /* HTML */ `
        <div class="prose">
          <p>${t.aboutBody}</p>
          <p>${t.license}</p>
        </div>
        <div class="actions">
          ${link(repo + "/blob/master/CONTRIBUTING.md", t.contribute, "button outline")}
        </div>
      `;
  } else
    body =
      heading(t.privacyTitle, "") +
      /* HTML */ `
        <div class="prose">
          <p>${t.privacyBody}</p>
          ${link(
            "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement",
            t.privacyMore,
          )}
        </div>
      `;
  main.innerHTML =
    route === "home"
      ? body
      : /* HTML */ `
          <section class="page">${body}</section>
        `;
  updateTheme();
  main.querySelectorAll('.hero-screens a, .gallery a, .features-showcase a[data-preview]').forEach((anchor) => {
    anchor.removeAttribute('target');
    anchor.setAttribute('aria-haspopup', 'dialog');
  });
}
const imageViewer = document.querySelector('#image-viewer');
const viewerImage = imageViewer.querySelector('img');
const viewerClose = imageViewer.querySelector('button');
let imageTrigger = null;
main.addEventListener('click', (event) => {
  const anchor = event.target.closest('.hero-screens a, .gallery a, .features-showcase a[data-preview]');
  if (!anchor) return;
  const image = anchor.querySelector('img');
  if (!image) return;
  event.preventDefault();
  imageTrigger = anchor;
  viewerImage.src = anchor.href;
  viewerImage.alt = image.alt;
  imageViewer.setAttribute('aria-label', image.alt);
  viewerClose.textContent = copy[language].closeImage + ' ×';
  imageViewer.showModal();
  document.body.classList.add('viewing-image');
});
viewerClose.addEventListener('click', () => imageViewer.close());
imageViewer.addEventListener('click', (event) => {
  if (event.target === imageViewer) imageViewer.close();
});
imageViewer.addEventListener('close', () => {
  document.body.classList.remove('viewing-image');
  const trigger = imageTrigger?.isConnected ? imageTrigger :
    [...main.querySelectorAll('.hero-screens a, .gallery a, .features-showcase a[data-preview]')].find((anchor) => anchor.href === viewerImage.src);
  (trigger || main).focus({preventScroll: true});
  viewerImage.removeAttribute('src');
});
document.querySelector("#language").addEventListener("change", (e) => {
  language = e.target.value;
  try {
    localStorage.setItem("onda-site-language", language);
  } catch {}
  render();
});
document.querySelector(".skip").addEventListener("click", (e) => {
  e.preventDefault();
  main.focus();
});
let pageAnimation;
window.addEventListener("hashchange", (event) => {
  const routeIndex = (url) => {
    const index = routes.indexOf(new URL(url).hash.slice(1));
    return index < 0 ? 0 : index;
  };
  const direction = routeIndex(event.newURL) >= routeIndex(event.oldURL) ? 1 : -1;
  render();
  pageAnimation?.cancel();
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    pageAnimation = main.animate([
      { opacity: 0, transform: `translateX(${direction * 56}px)` },
      { opacity: 1, transform: "translateX(0)" },
    ], { duration: 340, easing: "cubic-bezier(0.22, 1, 0.36, 1)" });
  }
  main.focus({ preventScroll: true });
  window.scrollTo(0, 0);
});
render();
fetch("https://api.github.com/repos/enzoandradee16/Onda/releases/latest", {
  headers: { Accept: "application/vnd.github+json" },
  signal: AbortSignal.timeout(10000),
})
  .then((r) => {
    if (!r.ok) throw Error("Release unavailable");
    return r.json();
  })
  .then((data) => {
    if (
      !data.draft &&
      !data.prerelease &&
      data.published_at &&
      Array.isArray(data.assets)
    )
      release = data;
  })
  .catch(() => {})
  .finally(() => {
    releaseDone = true;
    render();
  });
