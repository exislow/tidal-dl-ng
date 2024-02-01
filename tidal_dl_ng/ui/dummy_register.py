# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection

from .dummy_wiggly import WigglyWidget

# Set PYSIDE_DESIGNER_PLUGINS to point to this directory and load the plugin


TOOLTIP = "A cool wiggly widget (Python)"
DOM_XML = """
<ui language='c++'>
    <widget class='WigglyWidget' name='wigglyWidget'>
        <property name='geometry'>
            <rect>
                <x>0</x>
                <y>0</y>
                <width>400</width>
                <height>200</height>
            </rect>
        </property>
        <property name='text'>
            <string>Hello, world</string>
        </property>
    </widget>
</ui>
"""

if __name__ == "__main__":
    QPyDesignerCustomWidgetCollection.registerCustomWidget(
        WigglyWidget, module="wigglywidget", tool_tip=TOOLTIP, xml=DOM_XML
    )
