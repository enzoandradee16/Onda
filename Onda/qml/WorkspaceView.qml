import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Loader {
    id: page
    property string lastWorkspacePage: "catalog"
    readonly property string current: workspace.currentPage
    onCurrentChanged: if (current !== "jukebox") lastWorkspacePage = current
    sourceComponent: ["catalog", "playlists", "history"].includes(lastWorkspacePage) ? library : ["downloads", "queue"].includes(lastWorkspacePage) ? downloads : tools
    asynchronous: false
    Component {
        id: library
        LibraryView { mode: page.lastWorkspacePage }
    }
    Component {
        id: downloads
        DownloadsView {}
    }
    Component {
        id: tools
        ToolView {}
    }
    opacity: 1
    onLoaded: {
        if (bridge.animations)
            appear.restart();
    }
    NumberAnimation {
        id: appear
        target: page
        property: "opacity"
        from: 0
        to: 1
        duration: 150
    }
}
