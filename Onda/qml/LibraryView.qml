import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: page
    property string mode: workspace.currentPage
    property bool catalog: mode === "catalog"
    property bool history: mode === "history"
    readonly property string cardSizeKey: history ? "history_card_size" : catalog ? "catalog_card_size" : "playlist_card_size"
    readonly property string cardSize: workspace.preferences[cardSizeKey] || "Grande"
    readonly property bool smallCards: cardSize === "Pequeno"
    spacing: Math.round(14*bridge.spacing)
    RowLayout { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate(page.history ? "Buscar no histórico" : page.catalog ? "Pesquise uma música ou cole um link" : "Link do álbum ou playlist"); text: page.history ? workspace.values.historyQuery : page.catalog ? workspace.values.query : workspace.values.playlistUrl
            onTextEdited: workspace.setOption(page.history ? "historyQuery" : page.catalog ? "query" : "playlistUrl",text)
            onAccepted: if (!page.history && workspace.activity.busy.indexOf(page.catalog ? "search" : "collection") < 0) workspace.invoke(page.catalog ? "search" : "load_playlist",{})
        }
        ChoiceBox { visible: page.catalog; model: ["Deezer","Apple / iTunes","Spotify","Todos"]; currentIndex: Math.max(0,model.indexOf(workspace.values.provider)); onActivated: workspace.setOption("provider",currentText) }
        TaskButton { objectName: "libraryLoadButton"; visible: !page.history; primary: true; idleText: bridge.translate(page.catalog ? "Pesquisar" : "Carregar"); operation: page.catalog ? "search" : "load_playlist"; taskNames: [page.catalog ? "search" : "collection"] }
        TaskButton { visible: page.catalog; idleText: bridge.translate("Atualizar busca"); operation: "search"; parameters: ({refresh:true}) }
    }
    RowLayout {
        objectName: "spotifySetupNotice"
        visible: page.catalog && workspace.values.provider === "Spotify" && !workspace.activity.spotifySearchReady
        Layout.fillWidth: true
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.muted; text: bridge.translate("Configure a API em Configurações → Contas para pesquisar músicas no Spotify.") }
        ActionButton { text: bridge.translate("Configurar Spotify"); onClicked: workspace.invoke("configure_spotify",{}) }
    }
    RowLayout { visible: page.catalog; Layout.fillWidth: true
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Artista"); onTextEdited: workspace.setOption("filterArtist",text) }
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Álbum"); onTextEdited: workspace.setOption("filterAlbum",text) }
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Versão"); onTextEdited: workspace.setOption("filterVersion",text) }
    }
    Flow { visible: !page.catalog; Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
        ActionButton { visible: !page.history; text: bridge.translate("Importar lista"); onClicked: workspace.invoke("import_playlist",{}) }
        ActionButton { text: bridge.translate("Exportar"); onClicked: workspace.invoke(page.history ? "export_history" : "export_playlist",{}) }
        ActionButton { visible: !page.history; text: bridge.translate("Selecionar todas"); onClicked: workspace.invoke("check_all",{model:"playlists",checked:true}) }
        ActionButton { visible: !page.history; text: bridge.translate("Desmarcar todas"); onClicked: workspace.invoke("check_all",{model:"playlists",checked:false}) }
        TaskButton { visible: !page.history; idleText: bridge.translate("Conferir versões"); operation: "check_matches"; taskNames: ["check_matches"] }
        TaskButton { visible: !page.history; idleText: bridge.translate("Atualizar playlist"); operation: "update_playlist"; taskNames: ["collection", "compare_collection"] }
        TaskButton { visible: !page.history; idleText: bridge.translate("Conferir arquivos locais"); operation: "compare_playlist"; taskNames: ["compare_collection"] }
        ActionButton { visible: !page.history; text: bridge.translate("Selecionar ausentes"); onClicked: workspace.invoke("playlist_missing",{}) }
        ActionButton { visible: !page.history; primary: true; text: bridge.translate("Adicionar à fila"); onClicked: workspace.invoke("playlist_add",{}) }
        ActionButton { visible: page.history; text: bridge.translate("Limpar histórico"); onClicked: workspace.invoke("history_clear",{}) }
    }
    Label { visible: !page.catalog && !page.history; text: workspace.values.playlistTitle || ""; color: bridge.palette.text; font.pixelSize: Math.round(20*bridge.fontScale) }
    CardSizeControl { Layout.alignment: Qt.AlignRight; settingKey: page.cardSizeKey }
    ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: Math.round(10*bridge.spacing); reuseItems: true; model: page.catalog ? workspace.catalogModel : page.history ? workspace.historyModel : workspace.playlistModel
        EmptyState {
            objectName: "libraryEmptyState"
            anchors.fill: parent; visible: parent.count === 0
            heading: bridge.translate(page.history ? (workspace.values.historyQuery ? "Nenhum arquivo encontrado" : "Seu histórico está vazio") : page.catalog ? (workspace.activity.busy.indexOf("search")>=0 ? "Pesquisando músicas…" : workspace.values.catalogSearched ? "Nenhuma música encontrada" : "Encontre sua próxima música") : (workspace.activity.busy.indexOf("collection")>=0 ? "Carregando álbum ou playlist…" : "Nenhuma faixa para mostrar"))
            description: bridge.translate(page.history ? (workspace.values.historyQuery ? "Tente outro termo para buscar no histórico." : "Seus downloads e arquivos exportados aparecerão aqui.") : page.catalog ? (workspace.activity.busy.indexOf("search")>=0 ? "Aguarde os resultados ou clique em Cancelar." : workspace.values.catalogSearched ? "Tente outra busca ou ajuste os filtros de artista, álbum e versão." : "Pesquise por música ou artista, ou cole um link de faixa.") : "Cole o link de um álbum ou playlist e clique em Carregar, ou importe uma lista.")
        }
        ScrollBar.vertical: ScrollBar {}
        delegate: Card { id: rowCard; objectName: "libraryTrackCard"; required property var entry; required property int index; width: ListView.view.width; height: Math.max(page.history ? (page.smallCards ? 76 : page.cardSize === "Médio" ? 104 : 132) : (page.smallCards ? 132 : page.cardSize === "Médio" ? 160 : 192),trackDetails.implicitHeight+24)
            Menu {
                id: historyContext
                OndaMenuItem { text: bridge.translate("Editar metadados"); onTriggered: workspace.invoke("history_edit",rowCard.entry.checked ? {} : {index:rowCard.index}) }
                OndaMenuItem { text: bridge.translate("Efeitos"); onTriggered: workspace.invoke("history_effects",{index:rowCard.index}) }
            }
            TapHandler { enabled: page.history; acceptedButtons: Qt.RightButton; onTapped: historyContext.popup() }
            RowLayout { id: trackBody; anchors.fill: parent; anchors.margins: 12; spacing: Math.round(18*bridge.spacing)
                CheckBox { visible: !page.catalog; checked: rowCard.entry.checked || false; onToggled: workspace.invoke("check",{model:page.history ? "history" : "playlists",index:rowCard.index,checked:checked}) }
                Image { objectName: "libraryArtwork"; readonly property bool artworkReady: status === Image.Ready; source: rowCard.entry.cover_url || ""; sourceSize.width: 440; sourceSize.height: 440; Layout.preferredWidth: Math.min(rowCard.height-24,page.smallCards ? 76 : page.cardSize === "Médio" ? 112 : 168,rowCard.width*0.25); Layout.preferredHeight: Layout.preferredWidth; fillMode: Image.PreserveAspectFit; asynchronous: true
                    Label { anchors.centerIn: parent; visible: parent.status !== Image.Ready; text: "♪"; font.pixelSize: Math.round(36*bridge.fontScale); color: bridge.palette.muted }
                }
                ColumnLayout { id: trackDetails; Layout.fillWidth: true; spacing: Math.round((page.smallCards ? 3 : 7)*bridge.spacing)
                    Label { text: rowCard.entry.title || rowCard.entry.name || ""; font.pixelSize: Math.round((page.smallCards ? 14 : page.cardSize === "Médio" ? 16 : 17)*bridge.fontScale); font.weight: Font.DemiBold; color: bridge.palette.text; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: page.history ? (rowCard.entry.date_display || rowCard.entry.date)+" · "+rowCard.entry.mode : (rowCard.entry.artist || "")+" · "+(rowCard.entry.album || ""); color: bridge.palette.muted; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { visible: page.history && (!!rowCard.entry.artist || !!rowCard.entry.album); text: [rowCard.entry.artist || "",rowCard.entry.album || ""].filter(Boolean).join(" · "); color: bridge.palette.muted; Layout.fillWidth: true; elide: Text.ElideRight }
                    RowLayout { visible: !page.history; Image { objectName: "platformIcon"; source: rowCard.entry.platform_key ? "image://platform/"+rowCard.entry.platform_key+"/"+bridge.palette.text.replace("#","") : ""; Layout.preferredWidth: 20; Layout.preferredHeight: 20; fillMode: Image.PreserveAspectFit } Label { text: rowCard.entry.platform || ""; color: bridge.palette.muted } }
                    Label { visible: !page.history && (!!rowCard.entry.release_date || !!rowCard.entry.comparison || (!!rowCard.entry.service && rowCard.entry.service !== rowCard.entry.platform)); text: rowCard.entry.release_date ? bridge.translate("Data de lançamento")+": "+rowCard.entry.release_date : (rowCard.entry.comparison || rowCard.entry.service || rowCard.entry.platform || ""); color: bridge.palette.muted }
                    Flow { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                        ActionButton { primary: true; text: bridge.translate(page.history ? "Abrir arquivo" : "Baixar agora"); onClicked: workspace.invoke(page.history ? "open_file" : "catalog_download",page.history ? {path:rowCard.entry.path} : {index:rowCard.index}) }
                        ActionButton { visible: page.catalog; text: bridge.translate("Adicionar à fila"); onClicked: destinations.popup(); QueueDestinationMenu { id: destinations; recordIndex: rowCard.index } }
                        ActionButton { visible: page.catalog; text: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "catalog" && workspace.values.previewSource === rowCard.entry.source_url ? "Parar prévia" : "Ouvir prévia"); onClicked: workspace.invoke("preview_catalog",{index:rowCard.index}) }
                        ActionButton { visible: !page.history; text: bridge.translate("Ver no catálogo"); onClicked: workspace.invoke("open_url",{url:rowCard.entry.source_url}) }
                        ActionButton { visible: page.catalog; text: bridge.translate("Comparar resultados"); onClicked: workspace.invoke("compare_results",{index:rowCard.index}) }
                        ActionButton { visible: page.history; text: bridge.translate("Editar metadados"); onClicked: workspace.invoke("history_edit",{index:rowCard.index}) }
                        ActionButton { visible: page.history; text: bridge.translate("Efeitos"); onClicked: workspace.invoke("history_effects",{index:rowCard.index}) }
                        ActionButton { visible: page.history; text: bridge.translate("Baixar novamente"); enabled: !!rowCard.entry.source; onClicked: workspace.invoke("history_retry",{index:rowCard.index}) }
                    }
                }
            }
        }
    }
}
