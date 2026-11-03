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
    readonly property var currentBand: bridge.equalizer.bands[Math.min(selectedBand,bridge.equalizer.bands.length-1)] || {frequency:1000,gain:0,q:1.4}
    Connections { target: bridge; function onEqualizerChanged() { popup.selectedBand=Math.max(0,Math.min(popup.selectedBand,bridge.equalizer.bands.length-1)) } }
    background: Card { }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: bridge.animations ? 160 : 0 } NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: bridge.animations ? 180 : 0; easing.type: Easing.OutCubic } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: bridge.animations ? 100 : 0 } }
    OndaScrollView {
            id: equalizerScroll

            property var scrollTopButton: ScrollToTop { target: equalizerScroll.contentItem; viewport: equalizerScroll }
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
                ChoiceBox { Layout.fillWidth: true; model: bridge.presetNames; currentIndex: bridge.presetNames.indexOf(bridge.presetName); displayText: bridge.translate(bridge.presetName); onActivated: bridge.applyPreset(model[index]) }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: bridge.translate("Quantidade de bandas"); color: bridge.palette.muted; font.pixelSize: Math.round(13*bridge.fontScale) }
                ChoiceBox { objectName: "equalizerBandCount"; Layout.fillWidth: true; model: [5,10,15]; currentIndex: model.indexOf(bridge.equalizer.band_count); onActivated: {popup.selectedBand=0;bridge.setEqualizerBandCount(model[index])} }
            }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: bridge.translate("Os ajustes são adaptados às novas frequências ao mudar a quantidade de bandas."); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale) }
            RowLayout {
                Layout.fillWidth: true
                Text { text: bridge.translate("Pré-amplificação"); color: bridge.palette.text; font.pixelSize: Math.round(13*bridge.fontScale) }
                OndaSlider { id: preampSlider; Layout.fillWidth: true; from: -24; to: 0; value: bridge.equalizer.preamp; onMoved: if(!pressed)bridge.setPreamp(value); onPressedChanged: if(!pressed)bridge.setPreamp(value) }
                Text { text: preampSlider.value.toFixed(1)+" dB"; color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale); Layout.preferredWidth: 55 }
            }
            OndaScrollView {
                id: bandScroll
                Layout.fillWidth: true; Layout.preferredHeight: 260
                contentWidth: Math.max(availableWidth, bank.implicitWidth); contentHeight: 245; clip: true
                RowLayout {
                    id: bank; spacing: Math.round(8*bridge.spacing)
                    x: Math.max(0, (bandScroll.availableWidth - implicitWidth) / 2)
                    Repeater {
                        model: bridge.equalizer.bands.length
                        ColumnLayout {
                            required property int index
                            readonly property var band: bridge.equalizer.bands[index] || {frequency:1000,gain:0,q:1.4}
                            Layout.preferredWidth: 64; spacing: Math.round(4*bridge.spacing)
                            Text { Layout.alignment: Qt.AlignHCenter; text: (gainSlider.value >= 0 ? "+" : "")+gainSlider.value.toFixed(1); font.pixelSize: Math.round(12*bridge.fontScale); color: bridge.palette.text }
                            BandSlider { id: gainSlider; Layout.alignment: Qt.AlignHCenter; value: parent.band.gain; onMoved: if(!pressed && index<bridge.equalizer.bands.length)bridge.setBand(index,parent.band.frequency,value,parent.band.q); onPressedChanged: if(!pressed && index<bridge.equalizer.bands.length)bridge.setBand(index,parent.band.frequency,value,parent.band.q); Accessible.name: parent.band.frequency+" Hz" }
                            ActionButton { Layout.fillWidth: true; text: (parent.band.frequency>=1000 ? (parent.band.frequency/1000).toFixed(1)+"k" : Math.round(parent.band.frequency)); primary: popup.selectedBand===index; onClicked: popup.selectedBand=index }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: bridge.translate("Frequência (Hz)"); font.pixelSize: Math.round(13*bridge.fontScale); color: bridge.palette.text }
                SpinBox {
                    from: 2000; to: 2000000; stepSize: 100; editable: true
                    value: Math.round(popup.currentBand.frequency*100)
                    textFromValue: function(v,locale) { return Number(v/100).toLocaleString(locale,'f',2) }
                    valueFromText: function(t,locale) { return Math.round(Number.fromLocaleString(locale,t)*100) }
                    validator: DoubleValidator { bottom: 20; top: 20000; decimals: 2 }
                    onValueModified: bridge.setBand(popup.selectedBand,value/100,popup.currentBand.gain,popup.currentBand.q)
                }
                Item { Layout.fillWidth: true }
                Text { text: "Q"; font.pixelSize: Math.round(13*bridge.fontScale); color: bridge.palette.text }
                SpinBox {
                    from: 10; to: 1000; stepSize: 10; editable: true; value: Math.round(popup.currentBand.q*100)
                    textFromValue: function(v,locale) { return Number(v/100).toLocaleString(locale,'f',2) }
                    valueFromText: function(t,locale) { return Math.round(Number.fromLocaleString(locale,t)*100) }
                    validator: DoubleValidator { bottom: 0.1; top: 10; decimals: 2 }
                    onValueModified: bridge.setBand(popup.selectedBand,popup.currentBand.frequency,popup.currentBand.gain,value/100)
                }
            }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: bridge.translate("Q menor: banda mais larga. Reduza a pré-amplificação ao aumentar os ganhos."); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale) }
            RowLayout { Layout.fillWidth: true; ActionButton { text: bridge.translate("Restaurar"); onClicked: bridge.resetEqualizer() } Item { Layout.fillWidth: true } ActionButton { primary: true; text: bridge.translate("Pronto"); onClicked: popup.close() } }
        }
    }
}
