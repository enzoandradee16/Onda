package br.com.onda.mobile

import org.junit.Assert.*
import org.junit.Test

class NoticeNavigationTest {
    @Test fun updateAndExplicitGuidanceOpenMentionedCategory() {
        assertEquals("Ferramentas",noticeDestination("ONDA 1.1.3 disponível · Configurações → Ferramentas"))
        assertEquals("Aparência",noticeDestination("Ajuste em Configurações → Aparência."))
    }
    @Test fun spotifyPrerequisitesAndExpiredSessionsOpenAccounts() {
        assertEquals("Contas",noticeDestination("Conecte sua conta Spotify primeiro."))
        assertEquals("Contas",noticeDestination("0 resultado(s). Spotify: use Conectar Spotify ou configure Client ID e Client Secret em Metadados."))
        assertEquals("Contas",noticeDestination("Não foi possível pesquisar no Spotify. Reconecte sua conta e tente novamente."))
    }
    @Test fun ordinaryMessagesDoNotBecomeSettingsLinks() {
        for(message in listOf("Concluído","Spotify conectado","Spotify: 10 resultados","Falha HTTP 403","Baixando atualização do ONDA"))assertNull(message,noticeDestination(message))
    }
    @Test fun youtubeSessionCookiesAndToolsHaveExplicitDestinations() {
        assertEquals("Sessão do YouTube",noticeDestination("O YouTube exigiu uma verificação. Abra Menu → Sessão do YouTube. Também é possível importar cookies.txt em Configurações → Contas e redes."))
        assertEquals("Sessão do YouTube",noticeDestination("O YouTube não aceitou a sessão. Atualize a sessão ou use Importar cookies do YouTube em Configurações."))
        assertEquals("Contas",noticeDestination("Não foi possível ler cookies.txt no formato Netscape."))
        assertEquals("Contas",noticeDestination("Tente cookies.txt da própria sessão em Configurações → Redes sociais."))
        assertEquals("Ferramentas",noticeDestination("O YouTube recusou o acesso (HTTP 403). Se persistir, atualize o yt-dlp."))
        assertNull(noticeDestination("Cookies salvos no armazenamento privado do ONDA"))
        assertNull(noticeDestination("Atualização preparada. Use Forçar parada nas configurações Android."))
    }
}
