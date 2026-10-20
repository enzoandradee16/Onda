import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Loader {
    id: page
    sourceComponent: workspace.currentPage === "catalog" || workspace.currentPage === "playlists" || workspace.currentPage === "history" ? library : workspace.currentPage === "downloads" || workspace.currentPage === "queue" ? downloads : tools
    asynchronous: false
    Component { id: library; LibraryView {} }
    Component { id: downloads; DownloadsView {} }
    Component { id: tools; ToolView {} }
    opacity: 1
    onLoaded: { if (bridge.animations) appear.restart() }
    NumberAnimation { id: appear; target: page; property: "opacity"; from: 0; to: 1; duration: 150 }
}
