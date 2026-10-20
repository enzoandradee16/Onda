import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: page
    property bool queuePage: workspace.currentPage === "queue"
    spacing: Math.round(14*bridge.spacing)
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
                ActionButton { objectName: "addLinksButton"; text: bridge.translate("Adicionar à fila"); onClicked: workspace.invoke("add_links",{}) }
                ActionButton { primary: true; text: bridge.translate(workspace.activity.running ? "Cancelar" : "Baixar agora"); onClicked: workspace.invoke(workspace.activity.running ? "stop_queue" : "add_links",{start:true}) }
            }
        }
    }
    RowLayout { Layout.fillWidth: true
        OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Buscar na fila"); text: workspace.values.queueQuery; onTextEdited: workspace.setOption("queueQuery",text) }
        ComboBox { model: ["Todos","Na fila","Em andamento","Pausado","Concluído","Falhou","Cancelado"]; onActivated: workspace.setOption("queueState",currentText) }
        ActionButton { primary: true; text: bridge.translate(workspace.activity.running ? "Cancelar" : "Baixar fila"); onClicked: workspace.invoke(workspace.activity.running ? "stop_queue" : "start_queue",{}) }
    }
    Flow { Layout.fillWidth: true; spacing: Math.round(6*bridge.spacing)
        ActionButton { text: bridge.translate("Selecionar todas"); onClicked: workspace.invoke("check_all",{model:"queue",checked:true}) }
        Repeater { model: [{name:"Subir",key:"up"},{name:"Descer",key:"down"},{name:"Priorizar",key:"priority"},{name:"Pausar",key:"pause"},{name:"Retomar",key:"resume"},{name:"Tentar novamente",key:"retry"},{name:"Remover",key:"remove"},{name:"Cancelar todas",key:"cancel_all"},{name:"Limpar fila",key:"clear"},{name:"Ordenar por título",key:"sort"}]
            ActionButton { required property var modelData; text: bridge.translate(modelData.name); onClicked: workspace.invoke("queue_action",{name:modelData.key}) }
        }
        ComboBox { model: ["Ordem original","Título","Menor duração","Maior duração","Menor tamanho estimado"]; onActivated: workspace.invoke("queue_action",{name:"sort:"+currentText}) }
        ActionButton { text: bridge.translate("Falhas"); onClicked: workspace.invoke("failures",{}) }
        ActionButton { text: bridge.translate("Detalhes"); onClicked: workspace.invoke("logs",{}) }
    }
    RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: workspace.queueModel.count+" · "+(workspace.values.queueStorage || ""); color: bridge.palette.muted; wrapMode: Text.Wrap } Label { text: bridge.translate("Tempo decorrido")+": "+workspace.clock(workspace.activity.elapsed); color: bridge.palette.muted } }
    ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: Math.round(8*bridge.spacing); model: workspace.queueModel; reuseItems: true
        ScrollBar.vertical: ScrollBar {}
        delegate: Card { id: card; required property var entry; required property int index; width: ListView.view.width; height: workspace.preferences.queue_view === "Completa" ? 132 : 98
            RowLayout { anchors.fill: parent; anchors.margins: 14
                CheckBox { checked: card.entry.checked || false; onToggled: workspace.invoke("check",{model:"queue",index:card.index,checked:checked}) }
                ColumnLayout { Layout.fillWidth: true
                    Label { text: card.entry.display_name || card.entry.url; color: bridge.palette.text; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: bridge.translate(card.entry.state)+" · "+String(card.entry.mode).toUpperCase(); color: bridge.palette.muted }
                    OndaProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: card.entry.percent || 0; visible: card.entry.state === "Em andamento" }
                    Label { visible: workspace.preferences.queue_view === "Completa"; text: card.entry.last_error || card.entry.url; color: card.entry.last_error ? bridge.palette.error : bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; maximumLineCount: 2 }
                }
                ActionButton { text: "×"; onClicked: workspace.invoke("queue_action",{name:"remove",id:card.entry.id}) }
            }
        }
        Label { anchors.centerIn: parent; visible: workspace.queueModel.count === 0; text: bridge.translate("Sua fila está vazia."); color: bridge.palette.muted }
    }
}
