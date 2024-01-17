import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

Window {
    id: root
    visible: true
    width: 800; height: 400
    color: "#aaa"
    title: qsTr("Recorder")

    property bool recording: false
    property string promptsName: ''
    property string scriptText: ''
    property string scriptId: ''
    property string scriptFilename: ''
    property string saveDir: '.'

    Component.onCompleted: initTimer.start()
    Timer {
        id: initTimer
        interval: 0
        onTriggered: recorder.init(scriptModel)
    }

    onRecordingChanged: recorder.toggleRecording(recording)
    onScriptFilenameChanged: scriptModel.get(scriptListView.currentIndex).filename = scriptFilename

    function appendScript(data) {
        scriptModel.append(data)
    }

    function gotoNextScript() {
        scriptListView.incrementCurrentIndex();
        scriptListView.positionViewAtIndex(scriptListView.currentIndex, ListView.Center);
    }

    ListModel {
        id: scriptModel
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6

        Frame {
            Layout.fillHeight: true
            Layout.fillWidth: true
            focus: true

            ListView {
                id: scriptListView
                model: scriptModel
                anchors.fill: parent
                focus: true
                clip: true
                ScrollBar.vertical: ScrollBar { active: true; policy: ScrollBar.AlwaysOn }
                highlight: Rectangle { color: "lightsteelblue"; radius: 5 }

                onCurrentItemChanged: {
                    scriptText = model.get(currentIndex).script;
                    scriptId = model.get(currentIndex).script_id;
                    scriptFilename = model.get(currentIndex).filename;
                    console.log('selected: "' + scriptText + '", ' + scriptId + '", ' + scriptFilename);
                }

                delegate: Item {
                    width: parent.width - 20
                    height: 48
                    Column {
                        Text {
                            text: script
                            font.pointSize: 10
                        }
                        Text {
                            text: script_id
                            font.pointSize: 8
                        }
                        Text {
                            text: 'Filename: ' + filename
                            font.pointSize: 8
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: scriptListView.currentIndex = index
                    }
                }
            }
        }

        CheckBox {
            Layout.fillWidth: true
            font.pointSize: 14
            text: 'Filter all punctuation (only speak normal words!)'
            checked: true
            enabled: false
        }

        TextArea {
            Layout.fillWidth: true
            font.pointSize: 14
            wrapMode: TextEdit.Wrap
            readOnly: true
            text: scriptText
            background: Rectangle {
                border.width: 3
                border.color: recording ? "#2b2" : "#b22"
            }
        }

        Button {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            font.pointSize: 16
            highlighted: recording
            text: recording ? "Stop Recording (r)" : "Start Recording (r)"
            onClicked: {
                recording = !recording;
                if (recording) {
                    recorder.startRecording();
                } else {
                    recorder.finishRecording();
                    gotoNextScript();
                }
            }
            Shortcut {
                sequence: "r"
                onActivated: {
                    recording = !recording;
                    if (recording) {
                        recorder.startRecording();
                    } else {
                        recorder.finishRecording();
                        gotoNextScript();
                    }
                }
            }
        }

        RowLayout {
            Button {
                Layout.fillWidth: true
                font.pointSize: 14
                text: "Play (p)"
                enabled: scriptFilename
                highlighted: playFile.playbackState == playFile.PlayingState
                onClicked: {
                    playFile.source = scriptFilename
                    playFile.play()
                }
                MediaPlayer {
                    id: playFile
                    source: ''
                    audioOutput: AudioOutput {}
                }
                Shortcut {
                    sequence: "p"
                    onActivated: {
                        playFile.source = scriptFilename
                        playFile.play()
                    }
                }
            }

            

            Button {
                Layout.fillWidth: true
                font.pointSize: 14
                text: "Delete (d)"
                enabled: scriptFilename
                onClicked: {
                    playFile.stop()
                    playFile.source = ''
                    recorder.deleteFile(scriptFilename)
                }
                Shortcut {
                    sequence: "d"
                    onActivated: {
                        playFile.stop()
                        playFile.source = ''
                        recorder.deleteFile(scriptFilename)
                    }
                }
            }

            Button {
                Layout.fillWidth: true
                font.pointSize: 14
                text: recording ? "Cancel (n)" : "Next (n)"
                onClicked: {
                    if (recording) {
                        recording = !recording;
                    } else {
                        gotoNextScript()
                    }
                }
                Shortcut {
                    sequence: "n"
                    onActivated: {
                        if (recording) {
                            recording = !recording;
                        } else {
                            gotoNextScript()
                        }
                    }
                }
            }
        }
    }

}
