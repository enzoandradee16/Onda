import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: gallery
    objectName: "imageGalleryPopup"
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(1000,parent.width-40); height: parent.height-40
    modal: true; focus: true; padding: 20
    background: Rectangle {radius:14;color:bridge.palette.surface;border.color:bridge.palette.line}
    property var images: workspace.values.imageGallery || []
    property int index: workspace.values.imageGalleryIndex || 0
    property var current: images[index] || ({})
    visible: images.length>0 && !workspace.values.imageGalleryEmbedded
    onClosed: if(!workspace.values.imageGalleryEmbedded)workspace.invoke("image_gallery_close",{})
    readonly property bool online: !!workspace.values.imageGalleryToken
    function navigate(delta) {
        var target=index+delta
        if(target>=0 && target<images.length)workspace.setOption("imageGalleryIndex",target)
    }
    Shortcut {sequence:"Left";enabled:gallery.opened;onActivated:gallery.navigate(-1)}
    Shortcut {sequence:"Right";enabled:gallery.opened;onActivated:gallery.navigate(1)}
    ColumnLayout {
        anchors.fill: parent
        Label {visible:gallery.online;text:bridge.translate("Prévia antes de baixar");color:bridge.palette.accent}
        Label {text: gallery.current.name || "";color:bridge.palette.text; Layout.fillWidth:true; elide:Text.ElideRight}
        Image {objectName:"galleryImage";readonly property bool imageReady:status===Image.Ready;autoTransform:true;source:gallery.current.url || ""; asynchronous:true; fillMode:Image.PreserveAspectFit; Layout.fillWidth:true; Layout.fillHeight:true
            MouseArea {
                anchors.fill:parent
                property real startX:0
                property real startY:0
                onPressed:function(mouse){startX=mouse.x;startY=mouse.y}
                onReleased:function(mouse){
                    var dx=mouse.x-startX,dy=mouse.y-startY
                    if(Math.abs(dx)>=48 && Math.abs(dx)>Math.abs(dy))gallery.navigate(dx<0 ? 1 : -1)
                }
            }
            ActionButton {objectName:"galleryArrowPrevious";visible:gallery.images.length>1;anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter;text:"‹";enabled:gallery.index>0;Accessible.name:bridge.translate("Anterior");onClicked:gallery.navigate(-1)}
            ActionButton {objectName:"galleryArrowNext";visible:gallery.images.length>1;anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;text:"›";enabled:gallery.index<gallery.images.length-1;Accessible.name:bridge.translate("Próxima");onClicked:gallery.navigate(1)}
            Label {anchors.centerIn:parent; visible:parent.status===Image.Error || !!gallery.current.error;color:bridge.palette.error; text:gallery.current.error ? bridge.translateError(gallery.current.error) : bridge.translate("Não foi possível abrir este arquivo.")}
        }
        BusyIndicator {Layout.alignment:Qt.AlignHCenter;visible:gallery.online && !gallery.current.url && !gallery.current.error;running:visible}
        ActionButton {visible:gallery.online && !!gallery.current.error;text:bridge.translate("Tentar novamente");onClicked:workspace.invoke("image_gallery_retry",{})}
        RowLayout {
            ActionButton {objectName:"galleryPrevious";text:bridge.translate("Anterior"); enabled:gallery.index>0; onClicked:workspace.setOption("imageGalleryIndex",gallery.index-1)}
            Label {text:(gallery.index+1)+" / "+gallery.images.length;color:bridge.palette.text}
            ActionButton {objectName:"galleryNext";text:bridge.translate("Próxima"); enabled:gallery.index+1<gallery.images.length; onClicked:workspace.setOption("imageGalleryIndex",gallery.index+1)}
            ActionButton {objectName:"galleryShare";text:bridge.translate(gallery.online ? "Copiar link" : "Copiar para compartilhar"); onClicked:gallery.online ? workspace.invoke("copy_link",{url:workspace.values.imageGallerySource}) : workspace.invoke("share_image",{path:gallery.current.path})}
            ActionButton {objectName:"downloadPreviewImages";visible:gallery.online;primary:true;text:bridge.translate("Baixar imagens");onClicked:{workspace.invoke("image_gallery_download",{});gallery.close()}}
            ActionButton {objectName:"galleryClose";text:bridge.translate("Fechar"); onClicked:gallery.close()}
        }
    }
}
