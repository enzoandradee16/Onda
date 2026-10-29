import QtQuick
OndaProgressBar {
    objectName:"queuePreparationProgress"
    property bool preparing:false
    property real progress:0
    visible:preparing
    implicitHeight:3
    from:0;to:100
    value:Math.max(0,Math.min(100,progress))
    indeterminate:progress<=0
}
