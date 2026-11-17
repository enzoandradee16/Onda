import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id:panel
    property var report:workspace.optionValue(workspace.optionsRevision,"cacheReport") || ({})
    property bool showTracks:false
    function size(value){var bytes=Number(value || 0);return bytes<=0 ? "0 B" : bytes<1048576 ? Math.ceil(bytes/1024)+" KB" : (bytes/1048576).toFixed(1)+" MB"}
    spacing:10
    Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:bridge.translate("A música atual, as próximas preparadas e as últimas músicas ouvidas são preservadas para voltar.");color:bridge.palette.muted}
    Label {visible:report.bytes!==undefined;text:bridge.translate("Total")+": "+panel.size(report.bytes);font.bold:true;color:bridge.palette.text}
    Repeater {model:panel.report.categories || []
        RowLayout {required property var modelData;Layout.fillWidth:true
            Label {Layout.fillWidth:true;text:bridge.translate(modelData.name);color:bridge.palette.muted}
            Label {text:panel.size(modelData.bytes);color:bridge.palette.text}
        }
    }
    Label {visible:report.protected_bytes!==undefined;Layout.fillWidth:true;wrapMode:Text.Wrap;text:bridge.translate("Protegido da limpeza")+": "+panel.size(report.protected_bytes);color:bridge.palette.muted}
    Label {visible:!!report.over_budget;Layout.fillWidth:true;wrapMode:Text.Wrap;text:bridge.translate("O limite pode ser ultrapassado enquanto houver músicas protegidas. Elas serão preservadas.");color:bridge.palette.accent}
    ActionButton {text:bridge.translate(panel.showTracks ? "Ocultar músicas armazenadas" : "Ver músicas armazenadas");onClicked:{panel.showTracks=!panel.showTracks;if(panel.showTracks)workspace.invoke("cache_report",{})}}
    Repeater {model:panel.showTracks ? panel.report.tracks || [] : []
        RowLayout {required property var modelData;Layout.fillWidth:true
            ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0
                Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:modelData.name;color:bridge.palette.text}
                Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:panel.size(modelData.bytes)+" · "+bridge.translate(modelData.reason);font.pixelSize:11;color:bridge.palette.muted}
            }
            ActionButton {text:bridge.translate("Remover");compact:true;enabled:!modelData.protected;onClicked:workspace.invoke("cache_remove",{cache_id:modelData.id})}
        }
    }
}
