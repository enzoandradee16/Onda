import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "equalizerPopup"
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(850, parent.width-48)
    height: Math.min(content.implicitHeight+48,parent.height-48)
    padding: 24; modal: true; focus: true
    property int selectedBand: 0
    background: Card { }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: bridge.animations ? 160 : 0 } NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: bridge.animations ? 180 : 0; easing.type: Easing.OutCubic } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: bridge.animations ? 100 : 0 } }
    ScrollView {
        anchors.fill: parent; contentWidth: availableWidth; clip: true
        ColumnLayout {
            id: content; width: parent.width; spacing: Math.round(16*bridge.spacing)
            RowLayout {
                Layout.fillWidth: true
                Text { text: bridge.translate("Equalizador"); font.pixelSize: Math.round(23*bridge.fontScale); font.weight: Font.DemiBold; color: bridge.palette.text }
                Item { Layout.fillWidth: true }
                OndaSwitch { text: bridge.translate("Ativar equalizador"); checked: bridge.equalizer.enabled; onToggled: bridge.enableEqualizer(checked) }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: bridge.translate("Preset"); color: bridge.palette.muted; font.pixelSize: Math.round(13*bridge.fontScale) }
                ComboBox { Layout.fillWidth: true; model: bridge.presetNames; currentIndex: bridge.presetNames.indexOf(bridge.presetName); displayText: bridge.translate(bridge.presetName); onActivated: bridge.applyPreset(model[index]); delegate: ItemDelegate { width: parent.width; text: bridge.translate(modelData) } }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: bridge.translate("Pré-amplificação"); color: bridge.palette.text; font.pixelSize: Math.round(13*bridge.fontScale) }
                OndaSlider { Layout.fillWidth: true; from: -24; to: 0; value: bridge.equalizer.preamp; onMoved: bridge.setPreamp(value) }
                Text { text: bridge.equalizer.preamp.toFixed(1)+" dB"; color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale); Layout.preferredWidth: 55 }
            }
            ScrollView {
                Layout.fillWidth: true; Layout.preferredHeight: 260
                contentWidth: bank.implicitWidth; contentHeight: 245; clip: true
                RowLayout {
                    id: bank; spacing: Math.round(8*bridge.spacing)
                    Repeater {
                        model: 10
                        ColumnLayout {
                            required property int index
                            Layout.preferredWidth: 64; spacing: Math.round(4*bridge.spacing)
                            Text { Layout.alignment: Qt.AlignHCenter; text: (bridge.equalizer.bands[index].gain >= 0 ? "+" : "")+bridge.equalizer.bands[index].gain.toFixed(1); font.pixelSize: Math.round(12*bridge.fontScale); color: bridge.palette.text }
                            BandSlider { Layout.alignment: Qt.AlignHCenter; value: bridge.equalizer.bands[index].gain; onMoved: bridge.setBand(index,bridge.equalizer.bands[index].frequency,value,bridge.equalizer.bands[index].q); Accessible.name: bridge.equalizer.bands[index].frequency+" Hz" }
                            ActionButton { Layout.fillWidth: true; text: (bridge.equalizer.bands[index].frequency>=1000 ? (bridge.equalizer.bands[index].frequency/1000).toFixed(1)+"k" : Math.round(bridge.equalizer.bands[index].frequency)); primary: popup.selectedBand===index; onClicked: popup.selectedBand=index }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: bridge.translate("Frequência (Hz)"); font.pixelSize: Math.round(13*bridge.fontScale); color: bridge.palette.text }
                SpinBox {
                    from: 2000; to: 2000000; stepSize: 100; editable: true
                    value: Math.round(bridge.equalizer.bands[popup.selectedBand].frequency*100)
                    textFromValue: function(v,locale) { return Number(v/100).toLocaleString(locale,'f',2) }
                    valueFromText: function(t,locale) { return Math.round(Number.fromLocaleString(locale,t)*100) }
                    validator: DoubleValidator { bottom: 20; top: 20000; decimals: 2 }
                    onValueModified: bridge.setBand(popup.selectedBand,value/100,bridge.equalizer.bands[popup.selectedBand].gain,bridge.equalizer.bands[popup.selectedBand].q)
                }
                Item { Layout.fillWidth: true }
                Text { text: "Q"; font.pixelSize: Math.round(13*bridge.fontScale); color: bridge.palette.text }
                SpinBox {
                    from: 10; to: 1000; stepSize: 10; editable: true; value: Math.round(bridge.equalizer.bands[popup.selectedBand].q*100)
                    textFromValue: function(v,locale) { return Number(v/100).toLocaleString(locale,'f',2) }
                    valueFromText: function(t,locale) { return Math.round(Number.fromLocaleString(locale,t)*100) }
                    validator: DoubleValidator { bottom: 0.1; top: 10; decimals: 2 }
                    onValueModified: bridge.setBand(popup.selectedBand,bridge.equalizer.bands[popup.selectedBand].frequency,bridge.equalizer.bands[popup.selectedBand].gain,value/100)
                }
            }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: bridge.translate("Q menor: banda mais larga. Reduza a pré-amplificação ao aumentar os ganhos."); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale) }
            RowLayout { Layout.fillWidth: true; ActionButton { text: bridge.translate("Restaurar"); onClicked: bridge.resetEqualizer() } Item { Layout.fillWidth: true } ActionButton { primary: true; text: bridge.translate("Pronto"); onClicked: popup.close() } }
        }
    }
}
