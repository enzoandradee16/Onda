import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "remoteControlPopup"
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(510,parent.width-40); padding: 22; modal: true; focus: true
    background: Card {}
    height:Math.min(parent.height-40,contentItem.implicitHeight+topPadding+bottomPadding)
    contentItem: ScrollView {
        id: scroll
        clip:true
        implicitHeight:body.implicitHeight
        contentWidth:availableWidth
        ColumnLayout {
        id:body
        width:scroll.availableWidth
        spacing: 14
        Label {text:bridge.translate("Controle remoto · teste");color:bridge.palette.text;font.pixelSize:22}
        Label {Layout.fillWidth:true;wrapMode:Text.WordWrap;color:bridge.palette.muted;text:bridge.translate("No Android, abra Mais → Controlar ONDA no PC. Conecte os dois aparelhos à mesma rede Wi-Fi confiável. O áudio continua no computador.")}
        ActionButton {visible:!remoteControl.state.enabled;text:bridge.translate("Ativar controle remoto");onClicked:remoteControl.start()}
        TextField {
            visible:remoteControl.state.enabled && remoteControl.state.addresses.length>0
            Layout.fillWidth:true;readOnly:true;selectByMouse:true
            text:qrAddress.currentText
            Accessible.name:bridge.translate("Endereço do PC")
        }
        Label {visible:remoteControl.state.enabled && !remoteControl.state.addresses.length;Layout.fillWidth:true;wrapMode:Text.WordWrap;color:bridge.palette.text;text:bridge.translate("Nenhum endereço local encontrado. Verifique a conexão Wi-Fi do PC.")}
        ComboBox {
            id: qrAddress
            visible:remoteControl.state.enabled && count>1
            Layout.fillWidth:true
            model:remoteControl.state.addresses
        }
        Image {
            visible:remoteControl.state.enabled && !!source
            Layout.alignment:Qt.AlignHCenter
            Layout.preferredWidth:200; Layout.preferredHeight:200
            source:remoteControl.state.enabled && qrAddress.currentText ? remoteControl.qrCode(qrAddress.currentText) : ""
            smooth:false
            Accessible.name:bridge.translate("QR Code para conectar o celular")
        }
        Label {visible:remoteControl.state.enabled;Layout.fillWidth:true;wrapMode:Text.WordWrap;color:bridge.palette.muted;text:bridge.translate("No celular, toque em Ler QR Code para conectar sem digitar.")}
        Label {visible:remoteControl.state.enabled;text:bridge.translate("Código de conexão")+": "+remoteControl.state.code;font.pixelSize:28;color:bridge.palette.accent}
        Label {visible:remoteControl.state.paired;text:bridge.translate("Celular pareado");color:bridge.palette.text}
        Label {visible:!!remoteControl.state.error;Layout.fillWidth:true;wrapMode:Text.WordWrap;text:remoteControl.state.error;color:bridge.palette.text}
        RowLayout {
            ActionButton {visible:remoteControl.state.enabled;text:bridge.translate("Desativar e desconectar");onClicked:remoteControl.stop()}
            ActionButton {text:bridge.translate("Fechar");onClicked:popup.close()}
        }
        }
    }
}
