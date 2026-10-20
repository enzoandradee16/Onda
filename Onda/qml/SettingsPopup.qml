import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "settingsPopup"
    parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(1050,parent.width-60); height: Math.min(780,parent.height-50)
    padding: 24; modal: true; focus: true
    property string category: "Geral"
    background: Card {}
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: bridge.animations ? 150 : 0 } }
    ResetPopup { id: reset }
    contentItem: ColumnLayout { spacing: Math.round(16*bridge.spacing)
        RowLayout { Layout.fillWidth: true
            Label { text: bridge.translate("Configurações"); font.pixelSize: Math.round(26*bridge.fontScale); color: bridge.palette.text; Layout.fillWidth: true }
            ActionButton { text: bridge.translate("Pronto"); primary: true; onClicked: popup.close() }
        }
        OndaTextField { id: search; Layout.fillWidth: true; placeholderText: bridge.translate("Pesquisar configurações") }
        RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: Math.round(22*bridge.spacing)
            ColumnLayout { Layout.preferredWidth: 160; Layout.alignment: Qt.AlignTop; spacing: Math.round(5*bridge.spacing)
                Repeater { model: ["Geral","Aparência","Downloads","Imagens","Áudio","Contas","Ferramentas","Desempenho"]
                    ActionButton { required property string modelData; Layout.fillWidth: true; text: bridge.translate(modelData); primary: popup.category === modelData; onClicked: { popup.category=modelData;search.clear() } }
                }
                Item { Layout.fillHeight: true }
            }
            ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                ColumnLayout { width: parent.availableWidth; spacing: Math.round(18*bridge.spacing)
                    Repeater { model: workspace.settingsFields
                        OptionField { required property var modelData; Layout.fillWidth: true; field: modelData; settings: true; visible: (modelData.key !== "pure_black_separators" || workspace.preferences.theme_mode === "Preto puro") && (search.text ? bridge.translate(modelData.label).toLowerCase().indexOf(search.text.toLowerCase()) >= 0 : modelData.category === popup.category) }
                    }
                    ActionButton { visible: popup.category === "Geral" && !search.text; text: bridge.translate("Escolher quais configurações restaurar…"); onClicked: reset.open() }
                    Flow { visible: popup.category === "Geral" && !search.text; Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                        Repeater { model: [{name:"Exportar configurações…",key:"export_settings"},{name:"Importar configurações…",key:"import_settings"},{name:"Restaurar configurações",key:"restore_settings"}]
                            TaskButton { required property var modelData; idleText: bridge.translate(modelData.name); operation: modelData.key }
                        }
                    }
                    ColumnLayout { visible: popup.category === "Aparência" && !search.text; Layout.fillWidth: true
                        Label { text: bridge.translate("Ordem e visibilidade das abas"); color: bridge.palette.text; font.pixelSize: Math.round(19*bridge.fontScale) }
                        Repeater { model: workspace.navigation
                            ColumnLayout { required property var modelData; Layout.fillWidth: true; spacing: 6
                                Label { objectName: "appearanceTabGroup"; visible: !!modelData.group; text: bridge.translate(modelData.group || ""); color: bridge.palette.muted; font.pixelSize: Math.round(13*bridge.fontScale); font.weight: Font.DemiBold; Layout.topMargin: 12; Layout.bottomMargin: 4 }
                                RowLayout { visible: !!modelData.key; Layout.fillWidth: true
                                    CheckBox { checked: workspace.hiddenTabs.indexOf(modelData.key) < 0; enabled: ["catalog","downloads","queue"].indexOf(modelData.key) < 0; onToggled: workspace.invoke("toggle_tab",{key:modelData.key}) }
                                    Label { Layout.fillWidth: true; text: modelData.key ? workspace.pageLabel(modelData.key) : ""; color: bridge.palette.text }
                                    ActionButton { text: "↑"; enabled: !!modelData.canMoveUp; Accessible.name: bridge.translate("Mover para cima"); onClicked: workspace.invoke("tab_move",{key:modelData.key,direction:-1}) }
                                    ActionButton { text: "↓"; enabled: !!modelData.canMoveDown; Accessible.name: bridge.translate("Mover para baixo"); onClicked: workspace.invoke("tab_move",{key:modelData.key,direction:1}) }
                                }
                            }
                        }
                        ActionButton { text: bridge.translate("Restaurar ordem das abas"); onClicked: workspace.invoke("reset_tab_order",{}) }
                    }
                    Flow { visible: popup.category === "Downloads" && !search.text; Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                        ActionButton { text: bridge.translate("Escolher pasta"); onClicked: workspace.invoke("pick",{kind:"folder"}) }
                    }
                    Flow { visible: popup.category === "Contas" && !search.text; Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                        Repeater { model: [{name:"Salvar credenciais",key:"save_credentials"},{name:"Remover credenciais",key:"forget_credentials"},{name:"Conectar Spotify",key:"spotify_connect"},{name:"Desconectar",key:"spotify_disconnect"}]
                            TaskButton { required property var modelData; idleText: bridge.translate(modelData.name); operation: modelData.key }
                        }
                        ActionButton { text: bridge.translate("Importar cookies do YouTube"); onClicked: workspace.invoke("pick",{kind:"youtube_cookies"}) }
                        ActionButton { text: bridge.translate("Importar cookies.txt"); onClicked: workspace.invoke("pick",{kind:"social_cookies"}) }
                        ActionButton { text: bridge.translate("Remover cookies"); onClicked: { workspace.setSetting("youtube_cookies","");workspace.setSetting("social_cookies","") } }
                    }
                    Flow { visible: popup.category === "Ferramentas" && !search.text; Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                        Repeater { model: [{name:"Preparar FFmpeg",key:"prepare_tools"},{name:"Verificar ferramentas",key:"verify_tools"},{name:"Atualizar ferramentas",key:"update_tools"},{name:"Verificar atualização do ONDA",key:"app_update"},{name:"Atualizar tamanho do cache",key:"cache_info"},{name:"Limpar cache",key:"cache_clear"}]
                            TaskButton { required property var modelData; idleText: bridge.translate(modelData.name); operation: modelData.key }
                        }
                    }
                    Item { Layout.preferredHeight: 20 }
                }
            }
        }
    }
}
