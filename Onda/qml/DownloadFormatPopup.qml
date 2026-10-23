import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: dialog
    objectName: "downloadFormatPopup"
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(540,parent.width-48)
    height: Math.min(body.implicitHeight+48,parent.height-48)
    padding: 24
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    onClosed: if(decision.type === "choose_download_format")workspace.replyChoice(decision.identity,{cancel:true})
    readonly property var decision: workspace.choice
    readonly property var record: decision.record || ({})
    readonly property var formatCodes: ["mp3","m4a","flac","original"]
    property int formatIndex: 0
    readonly property string selectedFormat: formatCodes[formatIndex]
    readonly property var qualities: (decision.qualities || {})[selectedFormat] || []
    property string quality: "320 kbps"
    function reply(start) {workspace.replyChoice(decision.identity,{mode:selectedFormat,quality:quality,start:start})}
    background: Card {}
    Connections {
        target: workspace
        function onChoiceChanged() {
            if(workspace.choice.type === "choose_download_format") {
                dialog.formatIndex=Math.max(0,dialog.formatCodes.indexOf(workspace.choice.mode))
                dialog.quality=(workspace.choice.savedQualities || {})[dialog.selectedFormat] || ""
                dialog.open()
            } else dialog.close()
        }
    }
    contentItem: ScrollView {
        id: scroll
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            id: body
            width: scroll.availableWidth
            spacing: Math.round(16*bridge.spacing)
            Label {text:bridge.translate("Escolha o formato");font.pixelSize:Math.round(24*bridge.fontScale);color:bridge.palette.text;Layout.fillWidth:true;wrapMode:Text.Wrap}
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                RoundedArtwork {source:dialog.record.cover_url || "";Layout.preferredWidth:88;Layout.preferredHeight:88;fillMode:Image.PreserveAspectFit;asynchronous:true}
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Label {text:dialog.record.title || "";font.bold:true;Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.text;maximumLineCount:3;elide:Text.ElideRight}
                    Label {text:(dialog.record.artists || []).join(", ");Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted}
                    Label {text:dialog.record.album || "";Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted}
                }
            }
            Label {text:bridge.translate("Formato");color:bridge.palette.muted}
            ChoiceBox {
                objectName: "downloadFormatChoice"
                Layout.fillWidth: true
                model: ["MP3","M4A","FLAC","Áudio · original, sem recodificar"]
                currentIndex: dialog.formatIndex
                onActivated: function(index) {dialog.formatIndex=index;dialog.quality=(dialog.decision.savedQualities || {})[dialog.selectedFormat] || ""}
            }
            Label {visible:dialog.qualities.length>0;text:bridge.translate("Qualidade");color:bridge.palette.muted}
            ChoiceBox {
                objectName: "downloadQualityChoice"
                visible: dialog.qualities.length>0
                Layout.fillWidth: true
                model: dialog.qualities
                currentIndex: Math.max(0,dialog.qualities.indexOf(dialog.quality))
                onActivated: function(index) {dialog.quality=dialog.qualities[index]}
            }
            Label {text:bridge.translate("Inclui capa e metadados disponíveis. MP3/M4A usam YouTube; FLAC usa Monochrome.");Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted}
            Flow {
                Layout.fillWidth: true
                spacing: 10
                ActionButton {objectName:"confirmTrackDownload";primary:true;text:bridge.translate("Baixar agora");onClicked:dialog.reply(true)}
                ActionButton {objectName:"queueTrackDownload";text:bridge.translate("Adicionar à fila");onClicked:dialog.reply(false)}
                ActionButton {objectName:"cancelTrackDownload";text:bridge.translate("Voltar");onClicked:workspace.replyChoice(dialog.decision.identity,{cancel:true})}
            }
        }
    }
}
