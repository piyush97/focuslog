import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Ui

// focuslog bar widget: "󰑴 1h20m · 14m" (study · waste).
// Left click opens the dashboard app, right click flips the focused window's label.
BarWidget {
  id: root
  moduleName: "piyush97.focuslog"

  readonly property string cmd: String(setting("command", "focuslog"))
  property string label: ""
  property string tip: ""
  property bool wasting: false

  function refresh() { if (!proc.running) proc.running = true }
  function update(raw) {
    var d = Util.parseModuleJson(raw)
    root.label = d.text || ""
    root.tip = d.tooltip || ""
    root.wasting = d["class"] === "active"
  }

  visible: label !== ""
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Process {
    id: proc
    command: ["bash", "-lc", root.cmd + " waybar"]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.update(text) }
  }

  Timer {
    interval: Math.max(2, Number(root.setting("interval", 10))) * 1000
    running: true; repeat: true; triggeredOnStart: true
    onTriggered: root.refresh()
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.label
    tooltipText: root.tip
    active: root.wasting
    onPressed: function(button) {
      if (!root.bar) return
      root.bar.run(root.cmd + (button === Qt.RightButton ? " mark" : " app"))
      if (button === Qt.RightButton) refreshLater.restart()
    }
  }

  Timer { id: refreshLater; interval: 800; onTriggered: root.refresh() }
}
