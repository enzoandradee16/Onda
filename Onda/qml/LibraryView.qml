import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: page
    property string mode: workspace.currentPage
    property bool catalog: mode === "catalog"
    property bool history: mode === "history"
    readonly property bool spotifyBrowsing: !catalog && !history && !!workspace.optionValue(workspace.optionsRevision,"spotifyPlaylistsVisible")
    readonly property string cardSizeKey: history ? "history_card_size" : catalog ? "catalog_card_size" : "playlist_card_size"
    readonly property string cardSize: workspace.preferences[cardSizeKey] || "Grande"
    readonly property bool smallCards: cardSize === "Pequeno"
    spacing: Math.round(14*bridge.spacing)
    RowLayout { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate(page.history ? "Buscar no histórico" : page.catalog ? "Pesquise uma música ou cole um link" : "Link do álbum ou playlist"); text: page.history ? workspace.optionValue(workspace.optionsRevision,"historyQuery") : page.catalog ? workspace.optionValue(workspace.optionsRevision,"query") : workspace.optionValue(workspace.optionsRevision,"playlistUrl")
            onTextEdited: workspace.setOption(page.history ? "historyQuery" : page.catalog ? "query" : "playlistUrl",text)
            onAccepted: if (!page.history && workspace.activityValue(workspace.statusRevision,"busy").indexOf(page.catalog ? "search" : "collection") < 0) workspace.invoke(page.catalog ? "search" : "load_playlist",{})
        }
        ChoiceBox { visible: page.catalog; model: ["Deezer","Apple / iTunes","Spotify","Todos"]; currentIndex: Math.max(0,model.indexOf(workspace.optionValue(workspace.optionsRevision,"provider"))); onActivated: workspace.setOption("provider",currentText) }
        TaskButton { objectName: "libraryLoadButton"; visible: !page.history; primary: true; idleText: bridge.translate(page.catalog ? "Pesquisar" : workspace.optionValue(workspace.optionsRevision,"playlistTitle") && workspace.optionValue(workspace.optionsRevision,"loadedPlaylistUrl")===workspace.optionValue(workspace.optionsRevision,"playlistUrl") ? "Atualizar" : "Carregar"); operation: page.catalog ? "search" : "load_playlist"; taskNames: page.catalog ? ["search"] : ["collection","compare_collection","check_matches"] }
        TaskButton { visible: page.catalog; idleText: bridge.translate("Atualizar busca"); operation: "search"; parameters: ({refresh:true}) }
    }
    RowLayout {
        visible: !page.catalog && !page.history; Layout.fillWidth: true
        ActionButton {objectName:"spotifyPlaylistsButton";text:bridge.translate("Playlists do Spotify");primary:page.spotifyBrowsing;onClicked:{if(!workspace.activityValue(workspace.statusRevision,"spotifyConnected"))workspace.invoke("configure_spotify",{});else if(workspace.optionValue(workspace.optionsRevision,"spotifyPlaylistsLoaded"))workspace.setOption("spotifyPlaylistsVisible",!page.spotifyBrowsing);else workspace.invoke("spotify_playlists",{})}}
        TaskButton {visible:page.spotifyBrowsing;idleText:bridge.translate("Atualizar");operation:"spotify_playlists";taskNames:["spotify_playlists"]}
        Label {visible:!workspace.activityValue(workspace.statusRevision,"spotifyConnected");Layout.fillWidth:true;text:bridge.translate("Conecte sua conta Spotify para ver suas playlists.");color:bridge.palette.muted;wrapMode:Text.Wrap}
    }
    ColumnLayout {
        visible:page.spotifyBrowsing;Layout.fillWidth:true;Layout.fillHeight:visible
        ListView {
            id:spotifyLists;objectName:"spotifyAccountPlaylists";Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:10;reuseItems:true
            model:workspace.optionValue(workspace.optionsRevision,"spotifyPlaylists") || []
            ScrollBar.vertical:OndaScrollBar {}
            EmptyState {anchors.fill:parent;visible:spotifyLists.count===0;heading:bridge.translate(workspace.activityValue(workspace.statusRevision,"busy").indexOf("spotify_playlists")>=0?"Carregando playlists…":"Nenhuma playlist encontrada");description:bridge.translate("As playlists da conta conectada aparecerão aqui.")}
            delegate:Card {
                required property var modelData;width:ListView.view.width;height:108
                RowLayout {anchors.fill:parent;anchors.margins:12;spacing:12
                    RoundedArtwork {Layout.preferredWidth:80;Layout.preferredHeight:80;source:modelData.cover_url || "";fillMode:Image.PreserveAspectFit;asynchronous:true;sourceSize.width:160;sourceSize.height:160}
                    ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0
                        Label {Layout.fillWidth:true;text:modelData.title;textFormat:Text.PlainText;color:bridge.palette.text;font.bold:true;elide:Text.ElideRight}
                        Label {Layout.fillWidth:true;text:modelData.owner || "";textFormat:Text.PlainText;color:bridge.palette.muted;elide:Text.ElideRight}
                        Label {text:modelData.count===null?"":modelData.count+" "+bridge.translate("faixas");color:bridge.palette.muted}
                    }
                    ActionButton {text:bridge.translate("Abrir coleção");enabled:workspace.activityValue(workspace.statusRevision,"busy").indexOf("collection")<0;onClicked:workspace.invoke("spotify_playlist_open",{id:modelData.id})}
                    ActionButton {visible:spotifyLists.width>=760;text:bridge.translate("Usar em reprodução");enabled:workspace.activityValue(workspace.statusRevision,"busy").indexOf("collection")<0;onClicked:workspace.invoke("spotify_playlist_playback",{id:modelData.id})}
                    ActionButton {id:spotifyMore;text:bridge.translate("Mais ações");onClicked:spotifyActions.popup(spotifyMore,0,spotifyMore.height)}
                    OndaMenu {id:spotifyActions
                        OndaMenuItem {visible:spotifyLists.width<760;text:bridge.translate("Usar em reprodução");enabled:workspace.activityValue(workspace.statusRevision,"busy").indexOf("collection")<0;onTriggered:workspace.invoke("spotify_playlist_playback",{id:modelData.id})}
                        OndaMenuItem {text:bridge.translate("Baixar agora");enabled:workspace.activityValue(workspace.statusRevision,"busy").indexOf("collection")<0;onTriggered:workspace.invoke("spotify_playlist_download",{id:modelData.id})}
                        OndaMenuItem {text:bridge.translate("Adicionar à fila");enabled:workspace.activityValue(workspace.statusRevision,"busy").indexOf("collection")<0;onTriggered:workspace.invoke("spotify_playlist_add",{id:modelData.id})}
                    }
                }
            }
        }
        TaskButton {visible:Number(workspace.optionValue(workspace.optionsRevision,"spotifyPlaylistsNext"))>=0;idleText:bridge.translate("Carregar mais");operation:"spotify_playlists";parameters:({more:true});taskNames:["spotify_playlists"]}
    }
    RowLayout { visible: page.history; Layout.fillWidth: true; spacing: 8
        Repeater { model: ["Todos","Áudio","Vídeo","Imagens"]
            SegmentButton {required property string modelData;objectName: "historyFilter_"+modelData;text:bridge.translate(modelData);primary:workspace.optionValue(workspace.optionsRevision,"historyKind")===modelData;onClicked:workspace.setOption("historyKind",modelData)}
        }
    }
    RowLayout {
        objectName: "spotifySetupNotice"
        visible: page.catalog && workspace.optionValue(workspace.optionsRevision,"provider") === "Spotify" && !workspace.activityValue(workspace.statusRevision,"spotifySearchReady")
        Layout.fillWidth: true
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.muted; text: bridge.translate("Configure a API em Configurações → Contas para pesquisar músicas no Spotify.") }
        ActionButton { text: bridge.translate("Configurar Spotify"); onClicked: workspace.invoke("configure_spotify",{}) }
    }
    RowLayout { visible: page.catalog; Layout.fillWidth: true
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Artista"); onTextEdited: workspace.setOption("filterArtist",text) }
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Álbum"); onTextEdited: workspace.setOption("filterAlbum",text) }
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Versão"); onTextEdited: workspace.setOption("filterVersion",text) }
    }
    Flow { visible: !page.catalog && !page.spotifyBrowsing; Layout.fillWidth:true; spacing:10
        ActionButton {visible:!page.history;text:bridge.translate("Importar lista");onClicked:workspace.invoke("import_playlist",{})}
        ActionButton {visible:!page.history;primary:true;text:bridge.translate("Adicionar à fila");enabled:workspace.playlistModel.count>0;onClicked:workspace.invoke("playlist_add",{})}
        ActionButton {visible:!page.history;text:bridge.translate("Usar em reprodução");enabled:workspace.playlistModel.count>0;onClicked:workspace.invoke("playlist_playback",{})}
        ActionButton {visible:page.history && !!workspace.optionValue(workspace.optionsRevision,"historyUndo");text:bridge.translate("Desfazer remoção");onClicked:workspace.invoke("history_undo",{})}
        ActionButton {visible:page.history;text:bridge.translate("Limpar histórico");onClicked:workspace.invoke("history_clear",{})}
        ActionButton {id:collectionActionsButton;objectName:"openCollectionActions";text:bridge.translate(page.history ? "Exportar histórico" : "Mais ações");onClicked:if(page.history)workspace.invoke("export_history",{});else collectionActions.popup(collectionActionsButton,0,collectionActionsButton.height+6)}
        OndaMenu {id:collectionActions;objectName:"collectionActionsMenu"
            OndaMenuItem {text:bridge.translate("Exportar");onTriggered:workspace.invoke(page.history ? "export_history" : "export_playlist",{})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Selecionar todas");onTriggered:workspace.invoke("check_all",{model:"playlists",checked:true})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Desmarcar todas");onTriggered:workspace.invoke("check_all",{model:"playlists",checked:false})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Conferir versões");enabled:workspace.activityValue(workspace.statusRevision,"busy").length===0;onTriggered:workspace.invoke("check_matches",{})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Conferir arquivos locais");enabled:workspace.activityValue(workspace.statusRevision,"busy").length===0;onTriggered:workspace.invoke("compare_playlist",{})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Selecionar ausentes");onTriggered:workspace.invoke("playlist_missing",{})}
        }
    }
    Label { visible: !page.catalog && !page.history && !page.spotifyBrowsing; text: workspace.optionValue(workspace.optionsRevision,"playlistTitle") || ""; color: bridge.palette.text; font.pixelSize: Math.round(20*bridge.fontScale) }
    Label {objectName:"collectionCoverage";visible:!page.catalog && !page.history && !page.spotifyBrowsing && !!text;Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.text;text:bridge.translate(workspace.optionValue(workspace.optionsRevision,"collectionCoverage") || "")}
    ActionButton {visible:!page.catalog && !page.history && !page.spotifyBrowsing && workspace.playlistModel.count>0;text:bridge.translate("Conferir lista importada");enabled:workspace.activityValue(workspace.statusRevision,"busy").length===0;onClicked:workspace.invoke("compare_imported_collection",{})}
    Label {visible:!page.catalog && !page.history && !page.spotifyBrowsing && !!text;Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted;text:bridge.translate(workspace.optionValue(workspace.optionsRevision,"collectionReference") || "")}
    CardSizeControl { visible:!page.spotifyBrowsing; Layout.alignment: Qt.AlignRight; settingKey: page.cardSizeKey }
    ListView { id:libraryList;visible:!page.spotifyBrowsing; objectName:"libraryScrollList"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: Math.round(10*bridge.spacing); reuseItems: true; model: page.catalog ? workspace.catalogModel : page.history ? workspace.historyModel : workspace.playlistModel
        EmptyState {
            objectName: "libraryEmptyState"
            anchors.fill: parent; visible: parent.count === 0
            heading: bridge.translate(page.history ? (workspace.optionValue(workspace.optionsRevision,"historyQuery") || workspace.optionValue(workspace.optionsRevision,"historyKind")!=="Todos" ? "Nenhum arquivo encontrado" : "Seu histórico está vazio") : page.catalog ? (workspace.activityValue(workspace.statusRevision,"busy").indexOf("search")>=0 ? "Pesquisando músicas…" : workspace.optionValue(workspace.optionsRevision,"catalogSearched") ? "Nenhuma música encontrada" : "Encontre sua próxima música") : (workspace.activityValue(workspace.statusRevision,"busy").indexOf("collection")>=0 ? "Carregando álbum ou playlist…" : "Nenhuma faixa para mostrar"))
            description: bridge.translate(page.history ? (workspace.optionValue(workspace.optionsRevision,"historyQuery") || workspace.optionValue(workspace.optionsRevision,"historyKind")!=="Todos" ? "Tente outro termo para buscar no histórico." : "Seus downloads e arquivos exportados aparecerão aqui.") : page.catalog ? (workspace.activityValue(workspace.statusRevision,"busy").indexOf("search")>=0 ? "Aguarde os resultados ou clique em Cancelar." : workspace.optionValue(workspace.optionsRevision,"catalogSearched") ? "Tente outra busca ou ajuste os filtros de artista, álbum e versão." : "Pesquise por música ou artista, ou cole um link de faixa.") : "Cole o link de um álbum ou playlist e clique em Carregar, ou importe uma lista.")
        }
        ScrollBar.vertical: OndaScrollBar {}
        ScrollToTop { target: libraryList; viewport: libraryList }
        delegate: Card { id: rowCard; objectName: "libraryTrackCard"; required property var entry; required property int index; width: ListView.view.width; height: Math.max(page.history ? (page.smallCards ? 76 : page.cardSize === "Médio" ? 104 : 132) : (page.smallCards ? 132 : page.cardSize === "Médio" ? 160 : 192),trackDetails.implicitHeight+24)
            function requestDetails() {
                if(!page.visible || typeof entry==="undefined" || !entry)return
                if(page.history)workspace.invoke("request_history_details",{id:entry.id})
                else workspace.invoke("request_card_details",{model:page.catalog ? "catalog" : "playlists",source:entry.source_url || ""})
            }
            Component.onCompleted: requestDetails()
            ListView.onReused: requestDetails()
            onEntryChanged: if(page.history)requestDetails()
            Connections {target:page;function onVisibleChanged(){if(page.visible)rowCard.requestDetails()}}
            OndaMenu {id:historyContext;objectName:"libraryCardActions"
                OndaMenuItem {visible:!page.history;text:bridge.translate("Baixar agora");onTriggered:workspace.invoke("catalog_download",{model:page.catalog ? "catalog" : "playlists",index:rowCard.index})}
                OndaMenuItem {visible:!page.history;text:bridge.translate("Adicionar à fila");onTriggered:workspace.invoke("catalog_add",{model:page.catalog ? "catalog" : "playlists",index:rowCard.index})}
                OndaMenuItem {visible:!page.history;text:bridge.translate("Usar em reprodução");onTriggered:workspace.invoke("catalog_playback",{model:page.catalog ? "catalog" : "playlists",index:rowCard.index})}
                OndaMenuItem {visible:page.catalog;text:bridge.translate("Ouvir prévia");onTriggered:workspace.invoke("preview_catalog",{index:rowCard.index})}
                OndaMenuItem {visible:!page.history;text:bridge.translate("Ver no catálogo");onTriggered:workspace.invoke("open_url",{url:rowCard.entry.source_url})}
                OndaMenuItem {visible:!page.history;text:bridge.translate("Copiar link");onTriggered:workspace.invoke("copy_link",{url:rowCard.entry.source_url})}
                OndaMenuItem {visible:page.catalog;text:bridge.translate("Comparar resultados");onTriggered:workspace.invoke("compare_results",{index:rowCard.index})}
                OndaMenuItem {visible:page.history;text:bridge.translate("Abrir arquivo");onTriggered:workspace.invoke(rowCard.entry.is_image ? "history_preview" : "open_file",{path:rowCard.entry.path,id:rowCard.entry.id})}
                OndaMenuItem {visible:page.history;text:bridge.translate("Editar metadados");onTriggered:workspace.invoke("history_edit",rowCard.entry.checked ? {} : {index:rowCard.index})}
                OndaMenuItem {visible:page.history && !rowCard.entry.is_image;text:bridge.translate("Usar em reprodução");onTriggered:workspace.invoke("history_effects",{index:rowCard.index})}
                OndaMenuItem {visible:page.history;text:bridge.translate("Baixar novamente");enabled:!!rowCard.entry.source;onTriggered:workspace.invoke("history_retry",{index:rowCard.index})}
                OndaMenuItem {objectName:"removeHistoryContext";visible:page.history;text:bridge.translate("Remover");onTriggered:workspace.invoke("history_remove",{id:rowCard.entry.id})}
            }
            Keys.onPressed: function(event) {if(event.key===Qt.Key_Menu || (event.key===Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))){historyContext.popup();event.accepted=true}}
            TapHandler {acceptedButtons:Qt.RightButton;onTapped:historyContext.popup()}
            MouseArea {objectName:"openHistoryImages";anchors.fill:parent;acceptedButtons:Qt.LeftButton;enabled:page.history && !!rowCard.entry.is_image;cursorShape:enabled ? Qt.PointingHandCursor : Qt.ArrowCursor;onClicked:workspace.invoke("history_preview",{id:rowCard.entry.id})}
            RowLayout { id: trackBody; anchors.fill: parent; anchors.margins: 12; spacing: Math.round(18*bridge.spacing)
                CheckBox { visible: !page.catalog; checked: rowCard.entry.checked || false; onToggled: workspace.invoke("check",{model:page.history ? "history" : "playlists",index:rowCard.index,checked:checked}) }
                RoundedArtwork { objectName: "libraryArtwork"; readonly property bool artworkReady: status === Image.Ready; source: rowCard.entry.cover_url || ""; sourceSize.width: 440; sourceSize.height: 440; Layout.preferredWidth: Math.min(rowCard.height-24,page.smallCards ? 76 : page.cardSize === "Médio" ? 112 : 168,rowCard.width*0.25); Layout.preferredHeight: Layout.preferredWidth; fillMode: Image.PreserveAspectFit; asynchronous: true
                    TapHandler { enabled: page.history && !!rowCard.entry.is_image; onTapped: workspace.invoke("history_preview",{id:rowCard.entry.id}) }
                    LineIcon {anchors.centerIn:parent;visible:parent.status!==Image.Ready && !!rowCard.entry.is_image;glyph:"images";width:30;height:30;ink:bridge.palette.muted}
                    Label { anchors.centerIn: parent; visible: parent.status !== Image.Ready && !rowCard.entry.is_image; text: "♪"; font.pixelSize: Math.round(36*bridge.fontScale); color: bridge.palette.muted }
                }
                ColumnLayout { id: trackDetails; Layout.fillWidth: true; Layout.minimumWidth:0; spacing: Math.round((page.smallCards ? 3 : 7)*bridge.spacing)
                    Label { text: rowCard.entry.title || rowCard.entry.name || ""; font.pixelSize: Math.round((page.smallCards ? 14 : page.cardSize === "Médio" ? 16 : 17)*bridge.fontScale); font.weight: Font.DemiBold; color: bridge.palette.text; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: page.history ? (rowCard.entry.date_display || rowCard.entry.date)+" · "+rowCard.entry.mode : (rowCard.entry.artist || ""); color: bridge.palette.muted; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { visible: page.history && (!!rowCard.entry.artist || !!rowCard.entry.album); text: [rowCard.entry.artist || "",rowCard.entry.album || ""].filter(Boolean).join(" · "); color: bridge.palette.muted; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label {visible:!page.history&&!!text;text:workspace.albumReleaseText(rowCard.entry);color:bridge.palette.muted;Layout.fillWidth:true;elide:Text.ElideRight}
                    PlatformBadge {imageMedia:!!rowCard.entry.is_image;platformKey: rowCard.entry.platform_key || "";label: rowCard.entry.platform || ""}
                    Label { Layout.fillWidth:true;elide:Text.ElideRight;visible: !page.history && (!!rowCard.entry.comparison || (!!rowCard.entry.service && rowCard.entry.service !== rowCard.entry.platform)); text: (rowCard.entry.comparison || rowCard.entry.service || rowCard.entry.platform || ""); color: bridge.palette.muted }
                    Flow { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                        ActionButton { primary: true; text: bridge.translate(page.history ? "Abrir arquivo" : "Baixar agora"); onClicked: workspace.invoke(page.history ? (rowCard.entry.is_image ? "history_preview" : "open_file") : "catalog_download",page.history ? {path:rowCard.entry.path,id:rowCard.entry.id} : {model:page.catalog ? "catalog" : "playlists",index:rowCard.index}) }
                        ActionButton { visible: page.catalog; text: bridge.translate("Adicionar à fila"); onClicked: destinations.popup(); QueueDestinationMenu { id: destinations; recordIndex: rowCard.index } }
                        ActionButton { visible: false; text: bridge.translate(workspace.optionValue(workspace.optionsRevision,"previewActive") && workspace.optionValue(workspace.optionsRevision,"previewKind") === "catalog" && workspace.optionValue(workspace.optionsRevision,"previewSource") === rowCard.entry.source_url ? "Parar prévia" : "Ouvir prévia"); onClicked: workspace.invoke("preview_catalog",{index:rowCard.index}) }
                        ActionButton { visible: false; text: bridge.translate("Ver no catálogo"); onClicked: workspace.invoke("open_url",{url:rowCard.entry.source_url}) }
                        ActionButton { visible: false; text: bridge.translate("Comparar resultados"); onClicked: workspace.invoke("compare_results",{index:rowCard.index}) }
                        ActionButton { visible: false; text: bridge.translate("Editar metadados"); onClicked: workspace.invoke("history_edit",{index:rowCard.index}) }
                        ActionButton { visible: false; text: bridge.translate("Efeitos"); onClicked: workspace.invoke("history_effects",{index:rowCard.index}) }
                        ActionButton {objectName:"removeHistoryButton";visible:page.history;text:bridge.translate("Remover");onClicked:workspace.invoke("history_remove",{id:rowCard.entry.id})}
                        ActionButton { visible: false; text: bridge.translate("Baixar novamente"); enabled: !!rowCard.entry.source; onClicked: workspace.invoke("history_retry",{index:rowCard.index}) }
                        ActionButton {text:bridge.translate("Mais ações");onClicked:historyContext.popup()}
                    }
                }
            }
        }
    }
}
