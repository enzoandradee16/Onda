import QtQuick
import QtQuick.Controls
Menu {
    id:menu
    padding:6
    margins:8
    overlap:0
    readonly property real visibleItemsWidth: {
        var result=0
        for(var i=0;i<count;i++){var item=itemAt(i);if(item&&item.visible)result=Math.max(result,item.implicitWidth)}
        return result
    }
    readonly property real visibleItemsHeight: {
        var result=0
        for(var i=0;i<count;i++){var item=itemAt(i);if(item&&item.visible)result+=item.implicitHeight}
        return result
    }
    implicitWidth:Math.min(380*bridge.fontScale,Math.max(168*bridge.fontScale,visibleItemsWidth+leftPadding+rightPadding))
    implicitHeight:visibleItemsHeight+topPadding+bottomPadding
    background:Rectangle {
        radius:9
        color:bridge.palette.surface
        border.width:1;border.color:bridge.palette.line
    }
    contentItem:ListView {
        implicitHeight:menu.visibleItemsHeight
        model:menu.contentModel
        currentIndex:menu.currentIndex
        clip:true;spacing:0
        interactive:contentHeight>height
        boundsBehavior:Flickable.StopAtBounds
        keyNavigationEnabled:true;keyNavigationWraps:true
        ScrollIndicator.vertical:ScrollIndicator {}
    }
}
