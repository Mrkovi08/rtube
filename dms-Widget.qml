import QtQuick
import Qt5Compat.GraphicalEffects
import Quickshell
import qs.Common
import qs.Modules.Plugins

PluginComponent {
    id: root

    function launch() {
        Quickshell.execDetached(["rtube"]);
    }

    horizontalBarPill: Component {
        Item {
            implicitWidth: root.iconSize
            implicitHeight: root.iconSize

            Image {
                id: glyph
                anchors.centerIn: parent
                width: root.iconSize
                height: root.iconSize
                source: Qt.resolvedUrl("skull.svg")
                sourceSize.width: root.iconSize
                sourceSize.height: root.iconSize
                visible: false
                smooth: true
            }

            ColorOverlay {
                anchors.fill: glyph
                source: glyph
                color: Theme.widgetIconColor
            }
        }
    }

    verticalBarPill: Component {
        Item {
            implicitWidth: root.iconSize
            implicitHeight: root.iconSize

            Image {
                id: glyph
                anchors.centerIn: parent
                width: root.iconSize
                height: root.iconSize
                source: Qt.resolvedUrl("skull.svg")
                sourceSize.width: root.iconSize
                sourceSize.height: root.iconSize
                visible: false
                smooth: true
            }

            ColorOverlay {
                anchors.fill: glyph
                source: glyph
                color: Theme.widgetIconColor
            }
        }
    }

    pillClickAction: () => root.launch()
}
