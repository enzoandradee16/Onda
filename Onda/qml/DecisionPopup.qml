import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: decisionDialog
    objectName: "decisionPopup"
    parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(compact ? Math.max(340,Math.min(620,decisionMeasure.boundingRect.width+60),titleMeasure.boundingRect.width+48) : 780,parent.width-60); height: Math.min(compact ? body.implicitHeight+48 : 680,parent.height-70); modal: true; focus: true; padding: 24; closePolicy: Popup.NoAutoClose
    readonly property bool compact: !media && !review && !(decision.candidates || []).length
    property var selected: []
    property var rejected: []
    property var modes: ({})
    property var changes: ({})
    readonly property var decision: workspace.choice
    readonly property bool media: decision.type === "choose_media"
    readonly property bool review: decision.type === "review_metadata"
    TextMetrics { id: decisionMeasure; font: decisionText.font; text: decisionText.text }
    TextMetrics { id: titleMeasure; font: decisionHeading.font; text: decisionHeading.text }
    background: Card {}
    Connections { target: workspace
        function onChoiceChanged() {
            if (workspace.choice.identity && workspace.choice.type !== "choose_download_format") {
                decisionDialog.selected=workspace.choice.type === "choose_media" && workspace.preferences.auto_select_media ? workspace.choice.candidates.map(function(item) { return item.id }) : []
                decisionDialog.rejected=[];decisionDialog.modes={};decisionDialog.changes=Object.assign({},workspace.choice.record || {});decisionDialog.open()
            } else decisionDialog.close()
        }
    }
    function reply(value) { workspace.replyChoice(decision.identity,value) }
    contentItem: ColumnLayout { id: body; spacing: Math.round(14*bridge.spacing)
        Label { id: decisionHeading; text: decisionDialog.decision.title || bridge.translate(decisionDialog.media ? "Escolher mídias" : decisionDialog.review ? "Revisar metadados" : "Confirmar escolha"); color: bridge.palette.text; font.pixelSize: Math.round(22*bridge.fontScale); Layout.fillWidth: true; wrapMode: Text.Wrap }
        ScrollView { Layout.fillWidth: true; Layout.preferredHeight: Math.min(240,decisionText.contentHeight); contentWidth: availableWidth; clip: true
            TextArea { id: decisionText; width: parent.availableWidth; padding: 0; text: decisionDialog.decision.message || decisionDialog.decision.path || ""; textFormat: Text.PlainText; color: bridge.palette.muted; readOnly: true; selectByMouse: true; wrapMode: Text.Wrap; background: null }
        }
        OndaSwitch { id: remember; visible: decisionDialog.decision.type === "choose_version"; text: bridge.translate("Lembrar esta escolha"); checked: false }
        ActionButton { visible: decisionDialog.media; text: bridge.translate(decisionDialog.selected.length === (decisionDialog.decision.candidates || []).length ? "Desmarcar todas" : "Selecionar todas"); onClicked: decisionDialog.selected=decisionDialog.selected.length === decisionDialog.decision.candidates.length ? [] : decisionDialog.decision.candidates.map(function(item) { return item.id }) }
        ScrollView { id: candidatesScroll; visible: !decisionDialog.compact; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
            ColumnLayout { width: candidatesScroll.availableWidth; spacing: Math.round(9*bridge.spacing)
                Repeater { model: decisionDialog.decision.candidates || []
                    Card { required property var modelData; visible: decisionDialog.rejected.indexOf(modelData.id) < 0; Layout.fillWidth: true; Layout.minimumWidth: 0; implicitHeight: Math.max(124,candidateRow.implicitHeight+24)
                        RowLayout { id: candidateRow; objectName: "decisionCandidateRow"; anchors.fill: parent; anchors.margins: 12; spacing: 12
                            CheckBox { visible: decisionDialog.media; checked: decisionDialog.selected.indexOf(modelData.id) >= 0
                                onToggled: { var values=decisionDialog.selected.slice(); if (checked && values.indexOf(modelData.id)<0) values.push(modelData.id); else if (!checked) values.splice(values.indexOf(modelData.id),1);decisionDialog.selected=values }
                            }
                            Image { visible: decisionDialog.media; Layout.preferredWidth: 100; Layout.preferredHeight: 100; source: modelData.thumbnail || modelData.preview_url || modelData.url || ""; fillMode: Image.PreserveAspectFit; asynchronous: true }
                            Label { Layout.fillWidth: true; Layout.minimumWidth: 0; text: modelData.title || modelData.name || modelData.id || ""; wrapMode: Text.Wrap; color: bridge.palette.text }
                            ChoiceBox { visible: decisionDialog.media && (modelData.outputLabels || []).length > 0; model: modelData.outputLabels || []; onActivated: { var values=Object.assign({},decisionDialog.modes);values[modelData.id]=modelData.outputCodes[index];decisionDialog.modes=values } }
                            ActionButton { visible: decisionDialog.decision.type === "choose_version"; text: bridge.translate("Versão errada"); onClicked: { var ids=decisionDialog.rejected.slice();ids.push(modelData.id);decisionDialog.rejected=ids } }
                            ActionButton { visible: !decisionDialog.media; text: bridge.translate("Escolher"); primary: true; onClicked: decisionDialog.reply({selected_id:modelData.id || modelData.source_url,remember_choice:remember.checked,rejected_ids:decisionDialog.rejected}) }
                        }
                    }
                }
                Repeater { model: decisionDialog.review ? ["title","artists","album","genre","release_date","track_number","disc_number"] : []
                    ColumnLayout { required property string modelData; Layout.fillWidth: true
                        Label { text: bridge.translate(({title:"Título",artists:"Artista",album:"Álbum",genre:"Gênero",release_date:"Data de lançamento",track_number:"Número da faixa",disc_number:"Disco"})[modelData]); color: bridge.palette.muted }
                        OndaTextField { Layout.fillWidth: true; text: decisionDialog.changes[modelData] && typeof decisionDialog.changes[modelData].join === "function" ? decisionDialog.changes[modelData].join(", ") : decisionDialog.changes[modelData] || ""; onEditingFinished: decisionDialog.changes[modelData]=modelData === "artists" ? text.split(",").map(function(name) { return name.trim() }) : text }
                    }
                }
            }
        }
        Flow { Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
            ActionButton { visible: decisionDialog.decision.type === "confirm"; text: bridge.translate("Confirmar"); primary: true; onClicked: decisionDialog.reply({yes:true}) }
            ActionButton { visible: decisionDialog.media; text: bridge.translate("Continuar"); primary: true; enabled: decisionDialog.selected.length > 0; onClicked: { var modes={};decisionDialog.selected.forEach(function(id) { if (decisionDialog.modes[id]) modes[id]=decisionDialog.modes[id] });decisionDialog.reply({selected_ids:decisionDialog.selected,media_modes:modes}) } }
            ActionButton { visible: decisionDialog.review; text: bridge.translate("Salvar"); primary: true; onClicked: decisionDialog.reply({changes:decisionDialog.changes}) }
            ActionButton { visible: decisionDialog.decision.type === "choose_flac"; text: bridge.translate("Escolher arquivo"); onClicked: workspace.invoke("pick",{kind:"flac_import"}) }
            Repeater { model: decisionDialog.decision.type === "choose_duplicate" ? [{label:"Manter ambos",code:"keep"},{label:"Substituir",code:"replace"},{label:"Ignorar",code:"skip"}] : []
                ActionButton { required property var modelData; text: bridge.translate(modelData.label); onClicked: decisionDialog.reply({choice:modelData.code}) }
            }
            ActionButton { visible: decisionDialog.decision.type === "power_countdown"; text: bridge.translate("Cancelar desligamento"); onClicked: decisionDialog.reply({cancel:true}) }
            ActionButton { visible: decisionDialog.decision.type !== "power_countdown"; text: bridge.translate("Cancelar"); onClicked: decisionDialog.reply({cancel:true,yes:false}) }
            ActionButton { visible: decisionDialog.decision.type === "choose_duplicate"; text: bridge.translate("Cancelar todas"); onClicked: { workspace.invoke("stop_queue",{});decisionDialog.reply({cancel:true}) } }
        }
    }
}
