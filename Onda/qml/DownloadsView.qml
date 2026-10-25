import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: page
    property bool queuePage: workspace.currentPage === "queue"
    readonly property string cardSize: workspace.preferences.queue_card_size || "Grande"
    readonly property bool smallCards: cardSize === "Pequeno"
    spacing: Math.round(14*bridge.spacing)
    Menu {
        id: queueContext
        property string targetId: ""
        property bool targetChecked: false
        readonly property string actionId: targetChecked ? "" : targetId
        objectName: "queueContextMenu"
        width: Math.round(260*bridge.fontScale)
        background: Card {}
        OndaMenuItem { text: bridge.translate("Pausar"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"pause"}) }
        OndaMenuItem { text: bridge.translate("Retomar"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"resume"}) }
        OndaMenuItem { text: bridge.translate("Tentar novamente"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"retry"}) }
        OndaMenuItem { text: bridge.translate("Editar metadados"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_edit",{id:queueContext.actionId}) }
        MenuSeparator {}
        OndaMenuItem { text: bridge.translate("Mover para cima"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"up"}) }
        OndaMenuItem { text: bridge.translate("Mover para baixo"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"down"}) }
        OndaMenuItem { text: bridge.translate("Priorizar selecionados"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"priority"}) }
        MenuSeparator {}
        OndaMenuItem { objectName: "queueContextCopyLinks"; text: bridge.translate("Copiar link"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_copy_links",{id:queueContext.actionId}) }
        OndaMenuItem { text: bridge.translate("Abrir pasta"); onTriggered: workspace.invoke("queue_open_folder",{}) }
        OndaMenuItem { text: bridge.translate("Ver detalhes"); onTriggered: workspace.invoke("logs",{}) }
        MenuSeparator {}
        OndaMenuItem { text: bridge.translate("Cancelar selecionados"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"cancel"}) }
        OndaMenuItem { text: bridge.translate("Remover"); enabled: queueContext.targetId !== ""; onTriggered: workspace.invoke("queue_action",{id:queueContext.actionId,name:"remove"}) }
        OndaMenuItem { text: bridge.translate("Desfazer"); enabled: workspace.activity.undoCount>0; onTriggered: workspace.invoke("undo_queue",{}) }
        MenuSeparator {}
        OndaMenuItem { text: bridge.translate("Selecionar todas"); enabled: workspace.queueModel.count>0; onTriggered: workspace.invoke("check_all",{model:"queue",checked:true}) }
        OndaMenuItem { text: bridge.translate("Limpar seleção"); enabled: workspace.activity.selected>0; onTriggered: workspace.invoke("check_all",{model:"queue",checked:false}) }
        OndaMenuItem { text: bridge.translate("Limpar fila"); enabled: workspace.activity.total>0; onTriggered: workspace.invoke("queue_action",{name:"clear"}) }
    }
    Card {
        visible: !page.queuePage; Layout.fillWidth: true; implicitHeight: addControls.implicitHeight+32
        ColumnLayout { id: addControls; anchors.fill: parent; anchors.margins: 16; spacing: Math.round(14*bridge.spacing)
            Label { text: bridge.translate("Cole links para baixar vídeos, músicas e fotos."); font.pixelSize: Math.round(18*bridge.fontScale); color: bridge.palette.text }
            ScrollView { Layout.fillWidth: true; implicitHeight: 108
                OndaTextArea { text: workspace.values.links; placeholderText: bridge.translate("Um link por linha"); onTextChanged: if (activeFocus) workspace.setOption("links",text); wrapMode: Text.Wrap; selectByMouse: true; color: bridge.palette.text }
            }
            GridLayout { visible: !workspace.preferences.simple_download_ui; Layout.fillWidth: true; columns: width > 850 ? 3 : 2; columnSpacing: 12; rowSpacing: 12
                OptionField { visible: !workspace.preferences.simple_download_ui; Layout.fillWidth: true; settings: true; field: ({key:"mode",label:"Formato",kind:"select",choices:["Vídeo · melhor qualidade (MKV)","Vídeo · MP4","Áudio · original, sem recodificar","Áudio · MP3 (320 kbps)","Áudio · M4A (AAC)","Áudio · FLAC","Fotos · todas do carrossel","Publicação · fotos e vídeos originais"]}) }
                OptionField { visible: workspace.preferences.mode.indexOf("Vídeo") === 0; Layout.fillWidth: true; settings: true; field: ({key:"height",label:"Resolução máxima",kind:"select",choices:["Melhor disponível","2160p / 4K","1440p","1080p","720p","480p"]}) }
                OptionField { visible: workspace.preferences.mode.indexOf("Vídeo") === 0; Layout.fillWidth: true; settings: true; field: ({key:"fps",label:"FPS máximo",kind:"select",choices:["Original","24 fps","30 fps","60 fps","120 fps"]}) }
                OptionField { visible: workspace.preferences.mode.indexOf("MP3") >= 0; Layout.fillWidth: true; settings: true; field: ({key:"mp3_quality",label:"Qualidade MP3",kind:"select",choices:["320 kbps","256 kbps","192 kbps","128 kbps","96 kbps"]}) }
                OptionField { visible: workspace.preferences.mode.indexOf("M4A") >= 0; Layout.fillWidth: true; settings: true; field: ({key:"m4a_quality",label:"Qualidade M4A",kind:"select",choices:["256 kbps","192 kbps","128 kbps","96 kbps"]}) }
            }
            RowLayout { Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                ActionButton { objectName: "addLinksButton"; enabled: workspace.values.links.trim().length > 0; text: bridge.translate("Adicionar à fila"); onClicked: workspace.invoke("add_links",{}) }
                ActionButton { objectName: "downloadLinksNowButton"; primary: true; enabled: workspace.values.links.trim().length > 0; text: bridge.translate("Baixar agora"); onClicked: workspace.invoke("add_links",{start:true}) }
            }
        }
    }
    Card {
        objectName: "linksQueueNotice"
        visible: !page.queuePage && !!workspace.values.linksNotice
        Layout.fillWidth: true; implicitHeight: linksNoticeRow.implicitHeight+24
        RowLayout { id: linksNoticeRow; anchors.fill: parent; anchors.margins: 12; spacing: 16
            Label { text: workspace.values.linksNotice || ""; Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.text }
            ActionButton { objectName: "viewDownloadQueueButton"; text: bridge.translate("Ver fila"); onClicked: workspace.selectPage("queue") }
        }
    }
    Item {
        visible: !page.queuePage; Layout.fillWidth: true; Layout.fillHeight: true
        ColumnLayout {
            objectName: "linksEmptyState"
            visible: !workspace.values.links.trim() && !workspace.values.linksNotice
            anchors.centerIn: parent; width: Math.max(0,parent.width-32); spacing: 8
            Label { text: bridge.translate("Cole um link para começar"); color: bridge.palette.text; font.pixelSize: Math.round(20*bridge.fontScale); font.bold: true; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
            Label { text: bridge.translate("Baixe vídeos, músicas e fotos. Cole um link por linha e escolha Baixar agora ou Adicionar à fila."); color: bridge.palette.muted; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
        }
    }
    RowLayout { objectName: "downloadQueueFilters"; visible: page.queuePage; Layout.fillWidth: true
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Buscar na fila"); text: workspace.values.queueQuery; onTextEdited: workspace.setOption("queueQuery",text) }
        ChoiceBox { model: ["Todos","Na fila","Em andamento","Pausado","Concluído","Falhou","Cancelado"]; onActivated: workspace.setOption("queueState",currentText) }
        ActionButton { primary: true; text: bridge.translate(workspace.activity.running ? "Cancelar" : "Baixar fila"); onClicked: workspace.invoke(workspace.activity.running ? "stop_queue" : "start_queue",{}) }
    }
    Card { objectName: "downloadQueueTools"; visible: page.queuePage; Layout.fillWidth: true; implicitHeight: queueTools.implicitHeight+24
        Flow { id: queueTools; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 12; spacing: 8
            ActionButton { text: bridge.translate(workspace.queueModel.count>0 && workspace.activity.visibleSelected === workspace.queueModel.count ? "Desmarcar todas" : "Selecionar todas"); enabled: workspace.queueModel.count>0; onClicked: workspace.invoke("check_all",{model:"queue",checked:workspace.activity.visibleSelected !== workspace.queueModel.count}) }
            CardSizeControl { settingKey: "queue_card_size" }
            Label { text: bridge.translate("Selecionados")+": "+workspace.activity.selected; color: bridge.palette.muted; padding: 12 }
            ActionButton { text: bridge.translate("Editar metadados"); enabled: workspace.activity.selected>0; onClicked: workspace.invoke("queue_edit",{}) }
            ActionButton { text: bridge.translate("Pausar"); enabled: workspace.activity.selected>0; onClicked: workspace.invoke("queue_action",{name:"pause"}) }
            ActionButton { text: bridge.translate("Retomar"); enabled: workspace.activity.selected>0; onClicked: workspace.invoke("queue_action",{name:"resume"}) }
            ActionButton { text: bridge.translate("Remover"); enabled: workspace.activity.selected>0; onClicked: workspace.invoke("queue_action",{name:"remove"}) }
            ActionButton { text: bridge.translate("Desfazer"); enabled: workspace.activity.undoCount>0; onClicked: workspace.invoke("undo_queue",{}) }
            ChoiceBox { implicitWidth: 200; model: ["Ordem original","Título","Menor duração","Maior duração","Menor tamanho estimado"]; onActivated: workspace.invoke("queue_action",{name:"sort:"+currentText}); Accessible.name: bridge.translate("Ordenar fila") }
            ActionButton { text: bridge.translate("Mais ações"); onClicked: moreActions.popup()
                Menu { id: moreActions; width: Math.round(260*bridge.fontScale); background: Card {}
                    OndaMenuItem { text: bridge.translate("Subir selecionados"); enabled: workspace.activity.selected>0; onTriggered: workspace.invoke("queue_action",{name:"up"}) }
                    OndaMenuItem { text: bridge.translate("Descer selecionados"); enabled: workspace.activity.selected>0; onTriggered: workspace.invoke("queue_action",{name:"down"}) }
                    OndaMenuItem { text: bridge.translate("Priorizar selecionados"); enabled: workspace.activity.selected>0; onTriggered: workspace.invoke("queue_action",{name:"priority"}) }
                    OndaMenuItem { text: bridge.translate("Tentar novamente"); enabled: workspace.activity.selected>0; onTriggered: workspace.invoke("queue_action",{name:"retry"}) }
                    MenuSeparator {}
                    OndaMenuItem { text: bridge.translate("Cancelar todas"); enabled: workspace.activity.total>0; onTriggered: workspace.invoke("queue_action",{name:"cancel_all"}) }
                    OndaMenuItem { text: bridge.translate("Limpar fila"); enabled: workspace.activity.total>0; onTriggered: workspace.invoke("queue_action",{name:"clear"}) }
                    MenuSeparator {}
                    OndaMenuItem { text: bridge.translate("Ver falhas"); onTriggered: workspace.invoke("failures",{}) }
                    OndaMenuItem { text: bridge.translate("Ver detalhes"); onTriggered: workspace.invoke("logs",{}) }
                }
            }
        }
    }
    RowLayout { visible: page.queuePage; Layout.fillWidth: true; Label { Layout.fillWidth: true; text: workspace.queueModel.count+" · "+(workspace.values.queueStorage || ""); color: bridge.palette.muted; wrapMode: Text.Wrap } Label { text: bridge.translate("Tempo decorrido")+": "+workspace.clock(workspace.activity.elapsed); color: bridge.palette.muted } }
    ListView { objectName: "downloadQueueList"; visible: page.queuePage; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: Math.round(8*bridge.spacing); model: page.queuePage ? workspace.queueModel : null; reuseItems: true
        ScrollBar.vertical: ScrollBar {}
        delegate: Card { id: card; objectName: "downloadQueueCard"; required property var entry; required property int index; width: ListView.view.width; height: Math.max(page.smallCards ? 88 : page.cardSize === "Médio" ? 128 : 176,queueDetails.implicitHeight+24)
            function openContext() {
                queueContext.targetId = card.entry.id
                queueContext.targetChecked = !!card.entry.checked
                card.forceActiveFocus()
                queueContext.popup()
            }
            MouseArea { anchors.fill: parent; z: 10; acceptedButtons: Qt.RightButton; onClicked: card.openContext() }
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) {
                    card.openContext(); event.accepted = true
                }
            }
            RowLayout { anchors.fill: parent; anchors.margins: 12
                CheckBox { id: queueCheck; checked: card.entry.checked || false; onToggled: workspace.invoke("check",{model:"queue",index:card.index,checked:checked}); Accessible.name: bridge.translate("Selecionar")+" "+card.entry.track_title
                    indicator: Rectangle { implicitWidth: 20; implicitHeight: 20; x: queueCheck.leftPadding; y: (queueCheck.height-height)/2; radius: 4; color: queueCheck.checked ? bridge.palette.accent : bridge.palette.input; border.color: queueCheck.checked || queueCheck.activeFocus ? bridge.palette.accent : bridge.palette.muted; Label { anchors.centerIn: parent; text: "✓"; visible: queueCheck.checked; color: bridge.palette.accent_text } }
                }
                Rectangle { Layout.preferredWidth: Math.min(page.smallCards ? 56 : page.cardSize === "Médio" ? 96 : 132,card.height-24); Layout.preferredHeight: Layout.preferredWidth; radius: 8; color: bridge.palette.input
                    RoundedArtwork { id: queueCover; objectName: "downloadQueueArtwork"; anchors.fill: parent; source: card.entry.track_cover || ""; sourceSize.width: 264; sourceSize.height: 264; fillMode: Image.PreserveAspectFit; asynchronous: true }
                    LineIcon {anchors.centerIn:parent;visible:queueCover.status!==Image.Ready && !!card.entry.is_image;glyph:"images";width:30;height:30;ink:bridge.palette.muted}
                    Label { anchors.centerIn: parent; visible: queueCover.status !== Image.Ready && !card.entry.is_image; text: "♪"; color: bridge.palette.muted; font.pixelSize: 30 }
                }
                ColumnLayout { id: queueDetails; Layout.fillWidth: true; spacing: page.smallCards ? 3 : 5
                    Label { text: card.entry.track_title; font.pixelSize: Math.round((page.smallCards ? 13 : page.cardSize === "Médio" ? 14 : 16)*bridge.fontScale); color: bridge.palette.text; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { visible: !!card.entry.track_artist; text: card.entry.track_artist; color: bridge.palette.muted; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { visible: !page.smallCards && !!card.entry.track_album; text: card.entry.track_album; color: bridge.palette.muted; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { visible: !page.smallCards && card.entry.track_duration > 0; text: workspace.clock(card.entry.track_duration); color: bridge.palette.muted }
                    PlatformBadge {imageMedia:!!card.entry.is_image;platformKey:card.entry.platform_key || "";label:card.entry.platform || ""}
                    Label { text: bridge.translate(card.entry.state)+" · "+String(card.entry.mode).toUpperCase(); color: bridge.palette.muted }
                    OndaProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: card.entry.percent || 0; visible: card.entry.state === "Em andamento" }
                    Label { visible: workspace.preferences.queue_view === "Completa"; text: card.entry.last_error ? bridge.translateError(card.entry.last_error) : card.entry.url; color: card.entry.last_error ? bridge.palette.error : bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; maximumLineCount: 2 }
                }
                PlaybackButton { glyph: "close"; Accessible.name: bridge.translate("Remover"); onClicked: workspace.invoke("queue_action",{name:"remove",id:card.entry.id}) }
            }
        }
        EmptyState { anchors.fill: parent; visible: workspace.queueModel.count === 0; heading: bridge.translate("Nenhum item na fila"); description: bridge.translate(workspace.values.queueQuery || workspace.values.queueState !== "Todos" ? "Nenhum item corresponde à busca ou ao filtro selecionado." : "Adicione links ou músicas para organizar seus próximos downloads.") }
    }
}
