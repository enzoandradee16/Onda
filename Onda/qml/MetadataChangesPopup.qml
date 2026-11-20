import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: popup
    objectName: "metadataChangesPopup"
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(780, parent.width - 40)
    height: Math.min(700, parent.height - 60, previewBody.implicitHeight + 48)
    modal: true
    focus: true
    padding: 24
    closePolicy: Popup.NoAutoClose
    property var selection: ({})
    readonly property var report: workspace.choice
    background: Card {}
    Connections {
        target: workspace
        function onChoiceChanged() {
            if (workspace.choice.type === "review_metadata_changes" && workspace.choice.identity) {
                var values = {};
                (workspace.choice.entries || []).forEach(function (row, index) {
                    values[String(index)] = row.fields.map(function (field) {
                        return field.key;
                    });
                });
                popup.selection = values;
                popup.open();
            } else
                popup.close();
        }
    }
    function toggle(row, key, checked) {
        var values = Object.assign({}, selection);
        var fields = (values[String(row)] || []).slice();
        if (checked && fields.indexOf(key) < 0)
            fields.push(key);
        if (!checked)
            fields = fields.filter(function (value) {
                return value !== key;
            });
        values[String(row)] = fields;
        selection = values;
    }
    contentItem: ColumnLayout {
        id: previewBody
        spacing: 14
        Label {
            text: bridge.translate("Prévia das alterações")
            font.pixelSize: 22
            color: bridge.palette.text
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: bridge.translate("Confira as alterações. Desmarque o que deseja preservar.")
            color: bridge.palette.muted
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: bridge.translate(popup.report.overwrite_original ? "Os arquivos originais selecionados serão substituídos." : "Os arquivos originais serão preservados; cópias editadas serão salvas.")
            color: bridge.palette.muted
            font.pixelSize: 12
        }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: Math.min(420, Math.max(80, contentHeight))
            clip: true
            spacing: 12
            model: popup.report.entries || []
            ScrollBar.vertical: OndaScrollBar {}
            delegate: Card {
                id: entry
                required property var modelData
                required property int index
                width: ListView.view.width
                height: fieldsColumn.implicitHeight + 28
                ColumnLayout {
                    id: fieldsColumn
                    x: 14
                    y: 14
                    width: parent.width - 28
                    spacing: 10
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        text: entry.modelData.name
                        font.bold: true
                        color: bridge.palette.text
                    }
                    Repeater {
                        model: entry.modelData.fields
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 10
                            CheckBox {
                                checked: (popup.selection[String(entry.index)] || []).indexOf(modelData.key) >= 0
                                Accessible.name: modelData.label
                                onToggled: popup.toggle(entry.index, modelData.key, checked)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 3
                                Label {
                                    text: bridge.translate(modelData.label)
                                    font.bold: true
                                    color: bridge.palette.text
                                }
                                Label {
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                    color: bridge.palette.muted
                                    text: bridge.translate("Atual") + ": " + (modelData.before || bridge.translate("Vazio"))
                                }
                                Label {
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                    color: bridge.palette.accent
                                    text: bridge.translate("Novo") + ": " + (modelData.after || bridge.translate("Vazio"))
                                }
                            }
                        }
                    }
                    RowLayout {
                        visible: !!entry.modelData.after_cover
                        spacing: 16
                        ColumnLayout {
                            Label {
                                text: bridge.translate("Atual")
                                color: bridge.palette.muted
                            }
                            RoundedArtwork {
                                source: entry.modelData.before_cover || ""
                                Layout.preferredWidth: 76
                                Layout.preferredHeight: 76
                                fillMode: Image.PreserveAspectFit
                            }
                        }
                        ColumnLayout {
                            Label {
                                text: bridge.translate("Novo")
                                color: bridge.palette.muted
                            }
                            RoundedArtwork {
                                source: entry.modelData.after_cover || ""
                                Layout.preferredWidth: 76
                                Layout.preferredHeight: 76
                                fillMode: Image.PreserveAspectFit
                            }
                        }
                    }
                    Label {
                        visible: !entry.modelData.fields.length
                        text: bridge.translate("Sem alterações de metadados.")
                        color: bridge.palette.muted
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            ActionButton {
                text: bridge.translate("Cancelar")
                onClicked: workspace.replyChoice(popup.report.identity, {
                    cancel: true
                })
            }
            Item {
                Layout.fillWidth: true
            }
            ActionButton {
                text: bridge.translate("Salvar alterações")
                primary: true
                onClicked: workspace.replyChoice(popup.report.identity, {
                    selected: popup.selection
                })
            }
        }
    }
}
