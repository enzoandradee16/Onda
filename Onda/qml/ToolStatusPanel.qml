import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "toolStatusReport"
    property var report: workspace.values.toolReport || ({})
    property bool expanded: false
    readonly property var tools: report.tools || []
    spacing: 10
    function dateText(value) {
        var date=new Date(value)
        return !value || isNaN(date.getTime()) ? "—" : Qt.formatDateTime(date,"dd/MM/yyyy HH:mm")
    }
    Label {text:bridge.translate("Situação das ferramentas");color:bridge.palette.text;font.pixelSize:Math.round(18*bridge.fontScale);font.weight:Font.DemiBold}
    Flow {Layout.fillWidth:true;spacing:16;width:parent.width
        Label {text:panel.report.checked_at ? bridge.translate("Verificado: {date}").replace("{date}",panel.dateText(panel.report.checked_at)) : bridge.translate("Ferramentas ainda não verificadas.");color:bridge.palette.muted;font.pixelSize:Math.round(12*bridge.fontScale)}
        Label {visible:!!panel.report.updated_at;text:bridge.translate("Atualização: {date}").replace("{date}",panel.dateText(panel.report.updated_at));color:bridge.palette.muted;font.pixelSize:Math.round(12*bridge.fontScale)}
    }
    Label {visible:!!panel.report.update_state;text:bridge.translate(panel.report.update_state || "");color:bridge.palette.text;Layout.fillWidth:true;wrapMode:Text.Wrap}
    Card {
        visible:!!panel.report.restart_required
        Layout.fillWidth:true;implicitHeight:restartText.implicitHeight+20
        Label {id:restartText;anchors.fill:parent;anchors.margins:10;wrapMode:Text.Wrap;color:bridge.palette.text;text:bridge.translate("Reinício pendente. As versões exibidas são da última verificação.")}
    }
    GridLayout {
        id: toolsGrid
        objectName:"toolStatusGrid"
        Layout.fillWidth:true;columns:panel.width>=780*bridge.fontScale ? 3 : panel.width>=530*bridge.fontScale ? 2 : 1;columnSpacing:8;rowSpacing:8
        Repeater {model:panel.tools
            Card {
                required property var modelData
                objectName:"toolStatusRow_"+modelData.icon
                Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:Math.max(46,Math.round(50*bridge.fontScale))
                RowLayout {anchors.fill:parent;anchors.margins:8;spacing:10
                    Image {Layout.preferredWidth:30;Layout.preferredHeight:30;source:"../assets/tool-icons/tools/"+modelData.icon+".png";sourceSize.width:60;sourceSize.height:60;fillMode:Image.PreserveAspectFit}
                    ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0;spacing:2
                        Label {text:modelData.name;color:bridge.palette.text;font.weight:Font.DemiBold;Layout.fillWidth:true;elide:Text.ElideRight}
                        Label {objectName:"toolVersion_"+modelData.icon;text:bridge.translate(modelData.version);color:bridge.palette.muted;font.pixelSize:Math.round(12*bridge.fontScale);Layout.fillWidth:true;elide:Text.ElideRight}
                    }
                    LineIcon {Layout.preferredWidth:15;Layout.preferredHeight:15;glyph:modelData.available ? "check" : "warning";ink:modelData.available ? bridge.palette.accent : bridge.palette.text;Accessible.ignored:true}
                    Label {text:bridge.translate(modelData.status);color:bridge.palette.text;font.pixelSize:Math.round(11*bridge.fontScale)}
                }
            }
        }
    }
    ActionButton {objectName:"toolTechnicalDetails";visible:panel.tools.length>0;text:bridge.translate(panel.expanded ? "Ocultar detalhes técnicos" : "Detalhes técnicos");onClicked:panel.expanded=!panel.expanded}
    Label {objectName:"toolRawDetails";visible:panel.expanded;Layout.fillWidth:true;wrapMode:Text.WrapAnywhere;text:bridge.translate(panel.report.details || "");textFormat:Text.PlainText;color:bridge.palette.muted;font.pixelSize:Math.round(12*bridge.fontScale)}
    ActionButton {objectName:"restartAfterToolsCheck";visible:!!panel.report.can_restart;text:bridge.translate("Reiniciar ONDA");enabled:workspace.activity.active===0 && workspace.activity.busy.length===0 && !bridge.state.busy;onClicked:workspace.invoke("restart_app",{})}
}
