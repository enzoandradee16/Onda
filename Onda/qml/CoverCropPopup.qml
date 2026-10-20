import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: crop
    objectName: "coverCropPopup"
    parent: Overlay.overlay; anchors.centerIn: parent; width: 460; height: Math.min(650,parent.height-50); padding: 24; modal: true; focus: true
    property real zoom: 1
    property real offsetX: 0
    property real offsetY: 0
    background: Card {}
    Connections { target: workspace; function onCropRequested() { crop.zoom=1;crop.offsetX=0;crop.offsetY=0;crop.open() } }
    contentItem: ColumnLayout { spacing: Math.round(16*bridge.spacing)
        Label { text: bridge.translate("Ajustar capa"); font.pixelSize: Math.round(24*bridge.fontScale); color: bridge.palette.text }
        Label { text: bridge.translate("Arraste a imagem para mover e ajuste o zoom."); Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.muted }
        Rectangle { id: viewport; Layout.fillWidth: true; Layout.preferredHeight: width; clip: true; color: "#101419"
            Image { id: cover; source: workspace.values.cover_path ? "file:///"+workspace.values.cover_path.replace(/\\/g,"/") : ""; sourceSize.width: 1024; sourceSize.height: 1024
                width: viewport.width*Math.max(1,implicitWidth/Math.max(1,implicitHeight));height: viewport.height*Math.max(1,implicitHeight/Math.max(1,implicitWidth));fillMode: Image.PreserveAspectFit;scale: crop.zoom;x: (viewport.width-width)/2+crop.offsetX;y: (viewport.height-height)/2+crop.offsetY
            }
            Repeater { model: [1/3,2/3]; Rectangle { required property real modelData; x: modelData*viewport.width; width: 1; height: viewport.height; color: "#80ffffff" } }
            Repeater { model: [1/3,2/3]; Rectangle { required property real modelData; y: modelData*viewport.height; height: 1; width: viewport.width; color: "#80ffffff" } }
            MouseArea { anchors.fill: parent; property real previousX;property real previousY; cursorShape: Qt.SizeAllCursor
                onPressed: function(mouse) { previousX=mouse.x;previousY=mouse.y }
                onPositionChanged: function(mouse) { if (!pressed) return;var limitX=(cover.width*crop.zoom-viewport.width)/2;var limitY=(cover.height*crop.zoom-viewport.height)/2;crop.offsetX=Math.max(-limitX,Math.min(limitX,crop.offsetX+mouse.x-previousX));crop.offsetY=Math.max(-limitY,Math.min(limitY,crop.offsetY+mouse.y-previousY));previousX=mouse.x;previousY=mouse.y }
            }
        }
        OndaSlider { Layout.fillWidth: true; from: 1;to: 4;value: crop.zoom;onMoved: { crop.zoom=value;crop.offsetX=0;crop.offsetY=0 } }
        RowLayout { Layout.fillWidth: true
            ActionButton { text: bridge.translate("Cancelar"); onClicked: crop.close() }
            Item { Layout.fillWidth: true }
            ActionButton { primary: true; text: bridge.translate("Aplicar capa"); onClicked: { workspace.invoke("apply_cover_crop",{zoom:crop.zoom,x:crop.offsetX/viewport.width,y:crop.offsetY/viewport.height});crop.close() } }
        }
    }
}
