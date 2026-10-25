import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout {
    id: badge
    property string platformKey: ""
    property string label: ""
    property bool imageMedia: false
    visible: imageMedia || (!!platformKey && !!label)
    spacing: 5
    LineIcon {objectName:"imageMediaIcon";visible:badge.imageMedia;glyph:"images";Layout.preferredWidth:20;Layout.preferredHeight:20;Accessible.name:bridge.translate("Imagens")}
    Image {objectName: "platformIcon";visible:!!badge.platformKey && !(badge.imageMedia && badge.platformKey==="link");source:badge.platformKey ? "image://platform/"+badge.platformKey+"/"+bridge.palette.text.replace("#","") : "";Layout.preferredWidth:20;Layout.preferredHeight:20;fillMode:Image.PreserveAspectFit;Accessible.name:bridge.translate("Plataforma")+": "+badge.label}
    Label {visible:!!badge.label;text:badge.label;color:bridge.palette.muted}
}
