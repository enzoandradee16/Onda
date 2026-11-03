import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "remoteControlPopup"
    parent: Overlay.overlay
    width: Math.min(420,parent.width-24)
    height: Math.max(200,parent.height-playerBottomSpace-24)
    x: parent.width-width-12+slideOffset
    y: 12
    property real slideOffset: 0
    readonly property color panelColor: bridge.palette.flat_black ? "#101010" : bridge.palette.surface
    readonly property color deviceCardColor: bridge.palette.flat_black ? "#202020" : bridge.palette.input
    padding: 18
    modal: false
    dim: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    property real playerBottomSpace: workspace.currentPage==="jukebox" ? 118 : bridge.stateValue(bridge.stateRevision,"playing") ? 96 : 0
    property double closedAt: 0
    onAboutToHide: closedAt=Date.now()
    property bool pairingExpanded: false
    property bool manualExpanded: false
    onAboutToShow: {pairingExpanded=false;manualExpanded=false}
    background: Rectangle {radius:12;color:popup.panelColor;border.color:bridge.palette.line;border.width:bridge.palette.flat_black?0:1}
    enter: Transition {
        ParallelAnimation {
            NumberAnimation {target:popup;property:"slideOffset";from:popup.width+12;to:0;duration:bridge.animations?250:0;easing.type:Easing.OutCubic}
            NumberAnimation {property:"opacity";from:0;to:1;duration:bridge.animations?160:0;easing.type:Easing.OutCubic}
        }
    }
    exit: Transition {
        ParallelAnimation {
            NumberAnimation {target:popup;property:"slideOffset";to:popup.width+12;duration:bridge.animations?220:0;easing.type:Easing.InCubic}
            NumberAnimation {property:"opacity";to:0;duration:bridge.animations?180:0}
        }
    }
    contentItem: ColumnLayout {
        spacing: 18
        RowLayout {
            Layout.fillWidth:true
            Label {Layout.fillWidth:true;text:bridge.translate("Dispositivos");font.pixelSize:20;font.bold:true;color:bridge.palette.text}
            QueueIconButton {objectName:"closeDevicesPanel";glyph:"close";text:bridge.translate("Fechar");onClicked:popup.close()}
        }
        Rectangle {
            Layout.fillWidth:true
            implicitHeight:computerBody.implicitHeight+28
            radius:10;color:popup.deviceCardColor
            ColumnLayout {
                id:computerBody
                anchors.fill:parent;anchors.margins:14;spacing:10
                RowLayout {
                    Layout.fillWidth:true;spacing:12
                    LineIcon {glyph:"computer";ink:bridge.palette.accent;Layout.preferredWidth:28;Layout.preferredHeight:28}
                    ColumnLayout {
                        Layout.fillWidth:true;spacing:4
                        Label {Layout.fillWidth:true;text:bridge.translate("Este computador");color:bridge.palette.accent;font.bold:true;font.pixelSize:16}
                        Label {Layout.fillWidth:true;text:remoteControl.state.name || "ONDA PC";textFormat:Text.PlainText;color:bridge.palette.muted;elide:Text.ElideRight}
                    }
                }
                Label {
                    Layout.fillWidth:true;wrapMode:Text.Wrap;textFormat:Text.PlainText;color:bridge.palette.muted
                    text:bridge.stateValue(bridge.stateRevision,"ready") ? [bridge.stateValue(bridge.stateRevision,"title"),bridge.stateValue(bridge.stateRevision,"artist")].filter(Boolean).join(" · ") : bridge.translate("O áudio toca neste computador.")
                }
            }
        }
        OndaScrollView {
            id:scroll
            Layout.fillWidth:true;Layout.fillHeight:true;clip:true;contentWidth:availableWidth
            ScrollBar.horizontal.policy:ScrollBar.AlwaysOff

            ColumnLayout {
                id:body
                width:scroll.availableWidth;spacing:18
                Label {Layout.fillWidth:true;text:bridge.translate(remoteControl.state.connected?"Dispositivo conectado":"Nenhum celular conectado");color:bridge.palette.text;font.bold:true;wrapMode:Text.Wrap}
                Rectangle {
                    objectName:"connectedPhoneCard";visible:remoteControl.state.connected;Layout.fillWidth:true;implicitHeight:connectedRow.implicitHeight+24;radius:10;color:popup.deviceCardColor
                    RowLayout {
                        id:connectedRow;anchors.fill:parent;anchors.margins:12;spacing:12
                        LineIcon {glyph:"phone";ink:bridge.palette.accent;Layout.preferredWidth:28;Layout.preferredHeight:28}
                        ColumnLayout {
                            Layout.fillWidth:true
                            Label {text:bridge.translate("Celular conectado");color:bridge.palette.text;font.bold:true}
                            Label {Layout.fillWidth:true;text:bridge.translate("Controlando este computador");color:bridge.palette.muted;wrapMode:Text.Wrap}
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth:true;spacing:14
                    LineIcon {glyph:"wifi";ink:bridge.palette.muted;Layout.preferredWidth:26;Layout.preferredHeight:26}
                    ColumnLayout {
                        Layout.fillWidth:true;spacing:4
                        Label {text:bridge.translate("Verifique o Wi-Fi");color:bridge.palette.text;font.bold:true}
                        Label {Layout.fillWidth:true;text:bridge.translate("Conecte o computador e o celular à mesma rede Wi-Fi.");color:bridge.palette.muted;wrapMode:Text.Wrap}
                    }
                }
                RowLayout {
                    Layout.fillWidth:true;spacing:14
                    LineIcon {glyph:"devices";ink:bridge.palette.muted;Layout.preferredWidth:26;Layout.preferredHeight:26}
                    ColumnLayout {
                        Layout.fillWidth:true;spacing:4
                        Label {text:bridge.translate("Controle pelo celular");color:bridge.palette.text;font.bold:true}
                        Label {Layout.fillWidth:true;text:bridge.translate("No Android, abra Dispositivos e escolha este computador ou leia o QR Code.");color:bridge.palette.muted;wrapMode:Text.Wrap}
                    }
                }
                ActionButton {
                    objectName:"connectPhoneButton";Layout.fillWidth:true;primary:true
                    text:bridge.translate(popup.pairingExpanded?"Ocultar código":"Conectar celular")
                    onClicked:{if(!remoteControl.state.enabled)remoteControl.start();popup.pairingExpanded=!popup.pairingExpanded}
                }
                ColumnLayout {
                    visible:popup.pairingExpanded && remoteControl.state.enabled;Layout.fillWidth:true;spacing:12
                    ComboBox {id:qrAddress;visible:count>1;Layout.fillWidth:true;model:remoteControl.state.addresses}
                    Image {
                        visible:!popup.manualExpanded && !!source;Layout.alignment:Qt.AlignHCenter;Layout.preferredWidth:180;Layout.preferredHeight:180
                        source:popup.pairingExpanded && remoteControl.state.enabled && qrAddress.currentText ? remoteControl.qrCode(qrAddress.currentText) : ""
                        smooth:false;Accessible.name:bridge.translate("QR Code para conectar o celular")
                    }
                    Label {visible:!popup.manualExpanded;Layout.fillWidth:true;wrapMode:Text.Wrap;text:bridge.translate("No celular, toque em Ler QR Code para conectar sem digitar.");color:bridge.palette.muted}
                    OndaTextField {objectName:"devicesAddress";visible:popup.manualExpanded && remoteControl.state.addresses.length>0;Layout.fillWidth:true;readOnly:true;selectByMouse:true;text:qrAddress.currentText;Accessible.name:bridge.translate("Endereço do PC")}
                    Label {Layout.fillWidth:true;text:bridge.translate("Código de conexão")+": "+remoteControl.state.code;font.pixelSize:24;color:bridge.palette.accent;wrapMode:Text.Wrap}
                    ActionButton {Layout.fillWidth:true;text:bridge.translate(popup.manualExpanded?"Ler QR Code":"Usar endereço e código");onClicked:popup.manualExpanded=!popup.manualExpanded}
                    Label {visible:!remoteControl.state.addresses.length;Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted;text:bridge.translate("Nenhum endereço local encontrado. Verifique a conexão Wi-Fi do PC.")}
                }
                Label {visible:!!remoteControl.state.error;Layout.fillWidth:true;wrapMode:Text.Wrap;text:remoteControl.state.error;color:bridge.palette.text}
            }
        }
        ActionButton {objectName:"disableRemoteButton";visible:remoteControl.state.enabled;Layout.fillWidth:true;text:bridge.translate("Desativar e desconectar");onClicked:{remoteControl.stop();popup.pairingExpanded=false}}
    }
}
