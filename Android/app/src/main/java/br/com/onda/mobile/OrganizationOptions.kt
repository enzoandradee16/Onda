package br.com.onda.mobile

import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import org.json.JSONObject

internal val organizationOptions=listOf("Pasta de destino","Artista","Artista / Álbum","Álbum","Artista / Ano - Álbum","Gênero / Artista / Álbum","Formato / Artista / Álbum")
internal val filenameTemplates=listOf("Original","Artista - Música","Faixa - Música","Faixa - Artista - Música","Disco-Faixa - Música")

@Composable internal fun OrganizationOptions(settings:JSONObject,put:(String,Any)->Unit) {
    Select("Organizar músicas em",settings.optString("organization","Pasta de destino"),organizationOptions){put("organization",it)}
    SettingsDivider()
    Select("Nome dos arquivos",settings.optString("filename_template","Original"),filenameTemplates){put("filename_template",it)}
    val language=LocalUiLanguage.current
    val artist=translateUi("Artista",language);val album=translateUi("Álbum",language);val title=translateUi("Música",language);val genre=translateUi("Gênero",language)
    val folder=when(settings.optString("organization")) {
        "Artista"->"$artist/";"Artista / Álbum"->"$artist/$album/";"Álbum"->"$album/"
        "Artista / Ano - Álbum"->"$artist/2026 - $album/";"Gênero / Artista / Álbum"->"$genre/$artist/$album/"
        "Formato / Artista / Álbum"->"MP3/$artist/$album/";else->""
    }
    val name=when(settings.optString("filename_template")) {
        "Faixa - Música"->"01 - $title";"Faixa - Artista - Música"->"01 - $artist - $title"
        "Disco-Faixa - Música"->"1-01 - $title";else->"$artist - $title"
    }
    UiText("Prévia de organização",style=MaterialTheme.typography.labelMedium)
    androidx.compose.material3.Text(folder+name+".mp3",style=MaterialTheme.typography.bodySmall)
    UiText("As pastas de playlists são preservadas. Números de faixa ausentes são omitidos.",style=MaterialTheme.typography.bodySmall)
}
