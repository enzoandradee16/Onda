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
        TaskButton { objectName: "libraryLoadButton"; visible: !page.history; primary: true; idleText: bridge.translate(page.catalog ? "Pesquisar" : workspace.values.playlistTitle && workspace.values.loadedPlaylistUrl===workspace.values.playlistUrl ? "Atualizar" : "Carregar"); operation: page.catalog ? "search" : "load_playlist"; taskNames: page.catalog ? ["search"] : ["collection","compare_collection","check_matches"] }
        TaskButton { visible: page.catalog; idleText: bridge.translate("Atualizar busca"); operation: "search"; parameters: ({refresh:true}) }
    }
    RowLayout { visible: page.history; Layout.fillWidth: true; spacing: 8
        Repeater { model: ["Todos","Áudio","Vídeo","Imagens"]
            SegmentButton {required property string modelData;objectName: "historyFilter_"+modelData;text:bridge.translate(modelData);primary:workspace.values.historyKind===modelData;onClicked:workspace.setOption("historyKind",modelData)}
        }
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
    Flow { visible: !page.catalog; Layout.fillWidth:true; spacing:10
        ActionButton {visible:!page.history;text:bridge.translate("Importar lista");onClicked:workspace.invoke("import_playlist",{})}
        ActionButton {visible:!page.history;primary:true;text:bridge.translate("Adicionar à fila");enabled:workspace.playlistModel.count>0;onClicked:workspace.invoke("playlist_add",{})}
        ActionButton {visible:page.history && !!workspace.values.historyUndo;text:bridge.translate("Desfazer remoção");onClicked:workspace.invoke("history_undo",{})}
        ActionButton {visible:page.history;text:bridge.translate("Limpar histórico");onClicked:workspace.invoke("history_clear",{})}
        ActionButton {id:collectionActionsButton;objectName:"openCollectionActions";text:bridge.translate(page.history ? "Exportar histórico" : "Mais ações");onClicked:if(page.history)workspace.invoke("export_history",{});else collectionActions.popup(collectionActionsButton,0,collectionActionsButton.height+6)}
        OndaMenu {id:collectionActions;objectName:"collectionActionsMenu"
            OndaMenuItem {text:bridge.translate("Exportar");onTriggered:workspace.invoke(page.history ? "export_history" : "export_playlist",{})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Selecionar todas");onTriggered:workspace.invoke("check_all",{model:"playlists",checked:true})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Desmarcar todas");onTriggered:workspace.invoke("check_all",{model:"playlists",checked:false})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Conferir versões");enabled:workspace.activity.busy.length===0;onTriggered:workspace.invoke("check_matches",{})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Conferir arquivos locais");enabled:workspace.activity.busy.length===0;onTriggered:workspace.invoke("compare_playlist",{})}
            OndaMenuItem {visible:!page.history;text:bridge.translate("Selecionar ausentes");onTriggered:workspace.invoke("playlist_missing",{})}
        }
    }
    Label { visible: !page.catalog && !page.history; text: workspace.values.playlistTitle || ""; color: bridge.palette.text; font.pixelSize: Math.round(20*bridge.fontScale) }
    Label {objectName:"collectionCoverage";visible:!page.catalog && !page.history && !!text;Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.text;text:bridge.translate(workspace.values.collectionCoverage || "")}
    ActionButton {visible:!page.catalog && !page.history && workspace.playlistModel.count>0;text:bridge.translate("Conferir lista importada");enabled:workspace.activity.busy.length===0;onClicked:workspace.invoke("compare_imported_collection",{})}
    Label {visible:!page.catalog && !page.history && !!text;Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted;text:bridge.translate(workspace.values.collectionReference || "")}
    CardSizeControl { Layout.alignment: Qt.AlignRight; settingKey: page.cardSizeKey }
    ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: Math.round(10*bridge.spacing); reuseItems: true; model: page.catalog ? workspace.catalogModel : page.history ? workspace.historyModel : workspace.playlistModel
        EmptyState {
            objectName: "libraryEmptyState"
            anchors.fill: parent; visible: parent.count === 0
            heading: bridge.translate(page.history ? (workspace.values.historyQuery || workspace.values.historyKind!=="Todos" ? "Nenhum arquivo encontrado" : "Seu histórico está vazio") : page.catalog ? (workspace.activity.busy.indexOf("search")>=0 ? "Pesquisando músicas…" : workspace.values.catalogSearched ? "Nenhuma música encontrada" : "Encontre sua próxima música") : (workspace.activity.busy.indexOf("collection")>=0 ? "Carregando álbum ou playlist…" : "Nenhuma faixa para mostrar"))
            description: bridge.translate(page.history ? (workspace.values.historyQuery || workspace.values.historyKind!=="Todos" ? "Tente outro termo para buscar no histórico." : "Seus downloads e arquivos exportados aparecerão aqui.") : page.catalog ? (workspace.activity.busy.indexOf("search")>=0 ? "Aguarde os resultados ou clique em Cancelar." : workspace.values.catalogSearched ? "Tente outra busca ou ajuste os filtros de artista, álbum e versão." : "Pesquise por música ou artista, ou cole um link de faixa.") : "Cole o link de um álbum ou playlist e clique em Carregar, ou importe uma lista.")
        }
        ScrollBar.vertical: ScrollBar {}
        delegate: Card { id: rowCard; objectName: "libraryTrackCard"; required property var entry; required property int index; width: ListView.view.width; height: Math.max(page.history ? (page.smallCards ? 76 : page.cardSize === "Médio" ? 104 : 132) : (page.smallCards ? 132 : page.cardSize === "Médio" ? 160 : 192),trackDetails.implicitHeight+24)
            Component.onCompleted: if(!page.history)workspace.invoke("request_card_details",{model:page.catalog ? "catalog" : "playlists",source:entry.source_url || ""})
            ListView.onReused: if(!page.history)workspace.invoke("request_card_details",{model:page.catalog ? "catalog" : "playlists",source:entry.source_url || ""})
            OndaMenu {id:historyContext;objectName:"libraryCardActions"
                OndaMenuItem {visible:!page.history;text:bridge.translate("Baixar agora");onTriggered:workspace.invoke("catalog_download",{model:page.catalog ? "catalog" : "playlists",index:rowCard.index})}
                OndaMenuItem {visible:!page.history;text:bridge.translate("Adicionar à fila");onTriggered:workspace.invoke("catalog_add",{model:page.catalog ? "catalog" : "playlists",index:rowCard.index})}
                OndaMenuItem {visible:page.catalog;text:bridge.translate("Ouvir prévia");onTriggered:workspace.invoke("preview_catalog",{index:rowCard.index})}
                OndaMenuItem {visible:!page.history;text:bridge.translate("Ver no catálogo");onTriggered:workspace.invoke("open_url",{url:rowCard.entry.source_url})}
                OndaMenuItem {visible:!page.history;text:bridge.translate("Copiar link");onTriggered:workspace.invoke("copy_link",{url:rowCard.entry.source_url})}
                OndaMenuItem {visible:page.catalog;text:bridge.translate("Comparar resultados");onTriggered:workspace.invoke("compare_results",{index:rowCard.index})}
                OndaMenuItem {visible:page.history;text:bridge.translate("Abrir arquivo");onTriggered:workspace.invoke(rowCard.entry.is_image ? "history_preview" : "open_file",{path:rowCard.entry.path,id:rowCard.entry.id})}
                OndaMenuItem {visible:page.history;text:bridge.translate("Editar metadados");onTriggered:workspace.invoke("history_edit",rowCard.entry.checked ? {} : {index:rowCard.index})}
                OndaMenuItem {visible:page.history;text:bridge.translate("Reprodução");onTriggered:workspace.invoke("history_effects",{index:rowCard.index})}
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
                        ActionButton { visible: false; text: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "catalog" && workspace.values.previewSource === rowCard.entry.source_url ? "Parar prévia" : "Ouvir prévia"); onClicked: workspace.invoke("preview_catalog",{index:rowCard.index}) }
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
