﻿#!/usr/bin/env python
#!/usr/bin/env python
"""Facepager was made for fetching public available data from Facebook, Twitter and other JSON-based API. All data is stored in a SQLite database and may be exported to csv. """

# MIT License

# Copyright (c) 2019 Jakob Jünger and Till Keyling

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import argparse
import html

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QWidget, QStyleFactory

from icons import *
from datatree import *
from dictionarytree import *
from database import *
from actions import *
from apimodules import *
from help import *
from presets import *
from timer import *
from apiviewer import *
from dataviewer import *
from selectnodes import *
import logging
import threading

# Some hackery required for pyInstaller
# See https://justcode.nimbco.com/PyInstaller-with-Qt5-WebEngineView-using-PySide2/#could-not-find-qtwebengineprocessexe-on-windows
if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
    os.environ['QTWEBENGINEPROCESS_PATH'] = os.path.normpath(os.path.join(
        sys._MEIPASS, 'PySide2', 'Qt', 'lib',
        'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app',
        'Contents', 'MacOS', 'QtWebEngineProcess'
    ))

class MainWindow(QMainWindow):

    def __init__(self,central=None):
        super(MainWindow,self).__init__()

        self.setWindowTitle("Facepager 4.2")
        self.setWindowIcon(QIcon(":/icons/icon_facepager.png"))
        QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton)


        # This is needed to display the app icon on the taskbar on Windows 7
        if os.name == 'nt':
            import ctypes
            myappid = 'Facepager.4.2' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.setMinimumSize(1100,680)
        #self.setMinimumSize(1400,710)
        #self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center()-QPoint(0,100))
        #self.setStyleSheet("* {font-size:21px;}")
        #self.deleteSettings()
        self.lock_logging = threading.Lock()
        self.readSettings()
        self.createActions()

        self.createUI()
        self.createDB()
        self.updateUI()
        self.updateResources()

    def createDB(self):
        self.database = Database(self)

        dbname= cmd_args.database #sys.argv[1] if len(sys.argv) > 1 else None
        lastpath = self.settings.value("lastpath")

        if dbname and os.path.isfile(dbname):
            self.database.connect(dbname)
        elif lastpath and os.path.isfile(lastpath):
            self.database.connect(self.settings.value("lastpath"))

        self.tree.loadData(self.database)
        self.actions.actionShowColumns.trigger()

    def createActions(self):
        self.actions=Actions(self)


    def createUI(self):
        #
        #  Windows
        #

        self.helpwindow=HelpWindow(self)
        self.presetWindow=PresetWindow(self)
        self.presetWindow.logmessage.connect(self.logmessage)
        self.apiWindow = ApiViewer(self)
        self.apiWindow.logmessage.connect(self.logmessage)
        self.dataWindow = DataViewer(self)
        self.timerWindow=TimerWindow(self)
        self.selectNodesWindow=SelectNodesWindow(self)

        self.timerWindow.timerstarted.connect(self.actions.timerStarted)
        self.timerWindow.timerstopped.connect(self.actions.timerStopped)
        self.timerWindow.timercountdown.connect(self.actions.timerCountdown)
        self.timerWindow.timerfired.connect(self.actions.timerFired)

        #
        #  Statusbar and toolbar
        #

        self.statusbar = self.statusBar()
        self.toolbar=Toolbar(parent=self,mainWindow=self)
        self.addToolBar(Qt.TopToolBarArea,self.toolbar)

        self.timerStatus = QLabel("Timer stopped ")
        self.statusbar.addPermanentWidget(self.timerStatus)

        self.databaseLabel = QPushButton("No database connection ")
        self.statusbar.addWidget(self.databaseLabel)

        self.selectionStatus = QLabel("0 node(s) selected ")
        self.statusbar.addPermanentWidget(self.selectionStatus)
        #self.statusBar.showMessage('No database connection')
        self.statusbar.setSizeGripEnabled(False)

        self.databaseLabel.setFlat(True)
        self.databaseLabel.clicked.connect(self.databaseLabelClicked)


        #
        #  Layout
        #

        #dummy widget to contain the layout manager
        self.mainWidget=QSplitter(self)
        self.mainWidget.setOrientation(Qt.Vertical)
        self.setCentralWidget(self.mainWidget)

        #top
        topWidget=QWidget(self)
        self.mainWidget.addWidget(topWidget)
        dataLayout=QHBoxLayout()
        topWidget.setLayout(dataLayout)
        dataSplitter = QSplitter(self)
        dataLayout.addWidget(dataSplitter)

        #top left
        dataWidget=QWidget()
        dataLayout=QVBoxLayout()
        dataLayout.setContentsMargins(0,0,0,0)
        dataWidget.setLayout(dataLayout)
        dataSplitter.addWidget(dataWidget)
        dataSplitter.setStretchFactor(0, 1)

        #top right
        detailSplitter=QSplitter(self)
        detailSplitter.setOrientation(Qt.Vertical)

        #top right top
        detailWidget=QWidget(self)
        detailLayout=QVBoxLayout()
        detailLayout.setContentsMargins(11,0,0,0)
        detailWidget.setLayout(detailLayout)
        detailSplitter.addWidget(detailWidget)

        dataSplitter.addWidget(detailSplitter)
        dataSplitter.setStretchFactor(1, 0);

        #bottom
        bottomSplitter=QSplitter(self)
        self.mainWidget.addWidget(bottomSplitter)
        self.mainWidget.setStretchFactor(0, 1);

        #requestLayout=QHBoxLayout()
        #bottomWidget.setLayout(requestLayout)

        #bottom left
        modulesWidget = QWidget(self)
        moduleslayout=QVBoxLayout()
        modulesWidget.setLayout(moduleslayout)
        bottomSplitter.addWidget(modulesWidget)

        #bottom middle
        fetchWidget = QWidget(self)
        fetchLayout=QVBoxLayout()
        fetchWidget.setLayout(fetchLayout)
        bottomSplitter.addWidget(fetchWidget)

        settingsGroup=QGroupBox("Settings")
        fetchLayout.addWidget(settingsGroup)

        fetchsettings = QFormLayout()
        fetchsettings.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fetchsettings.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        fetchsettings.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        fetchsettings.setLabelAlignment(Qt.AlignLeft)
        settingsGroup.setLayout(fetchsettings)
        #fetchLayout.addLayout(fetchsettings)

        fetchdata=QHBoxLayout()
        fetchdata.setContentsMargins(10,0,10,0)
        fetchLayout.addLayout(fetchdata)

        #bottom right
        statusWidget = QWidget(self)
        statusLayout=QVBoxLayout()
        statusWidget.setLayout(statusLayout)
        bottomSplitter.addWidget(statusWidget)

        #
        #  Components
        #

        #main tree
        treetoolbar = QToolBar(self)
        treetoolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        treetoolbar.setIconSize(QSize(16,16))

        treetoolbar.addActions(self.actions.treeActions.actions())
        dataLayout.addWidget (treetoolbar)

        self.tree=DataTree(self.mainWidget)
        self.tree.nodeSelected.connect(self.actions.treeNodeSelected)
        self.tree.logmessage.connect(self.logmessage)
        dataLayout.addWidget(self.tree)


        #right sidebar - toolbar
        detailtoolbar = QToolBar(self)
        detailtoolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        detailtoolbar.setIconSize(QSize(16,16))
        detailtoolbar.addActions(self.actions.detailActions.actions())
        detailLayout.addWidget (detailtoolbar)

        #right sidebar - json viewer
        self.detailTree=DictionaryTree(self.mainWidget,self.apiWindow)
        detailLayout.addWidget(self.detailTree)

        #right sidebar - column setup
        detailGroup=QGroupBox("Custom Table Columns (one key per line)")
        detailSplitter.addWidget(detailGroup)
        groupLayout=QVBoxLayout()
        detailGroup.setLayout(groupLayout)

        self.fieldList=QTextEdit()
        self.fieldList.setLineWrapMode(QTextEdit.NoWrap)
        self.fieldList.setWordWrapMode(QTextOption.NoWrap)
        self.fieldList.acceptRichText=False
        self.fieldList.clear()
        self.fieldList.append('name')
        self.fieldList.append('message')
#         self.fieldList.append('type')
#         self.fieldList.append('metadata.type')
#         self.fieldList.append('talking_about_count')
#         self.fieldList.append('likes')
#         self.fieldList.append('likes.count')
#         self.fieldList.append('shares.count')
#         self.fieldList.append('comments.count')
#         self.fieldList.append('created_time')
#         self.fieldList.append('updated_time')

        self.fieldList.setPlainText(self.settings.value('columns',self.fieldList.toPlainText()))

        groupLayout.addWidget(self.fieldList)

        columnlayout=QHBoxLayout()
        groupLayout.addLayout(columnlayout)

        button=QPushButton("Apply Column Setup")
        button.setToolTip(wraptip("Apply the columns to the central data view. New columns may be hidden and are appended on the right side"))
        button.clicked.connect(self.actions.actionShowColumns.trigger)
        columnlayout.addWidget(button)

        button=QPushButton("Clear Column Setup")
        button.setToolTip(wraptip("Remove all columns to get space for a new setup."))
        button.clicked.connect(self.actions.actionClearColumns.trigger)
        columnlayout.addWidget(button)


        #Requests/Apimodules
        self.RequestTabs=QTabWidget()
        moduleslayout.addWidget(self.RequestTabs)
        self.RequestTabs.addTab(YoutubeTab(self),"YouTube")
        self.RequestTabs.addTab(TwitterTab(self),"Twitter")
        self.RequestTabs.addTab(TwitterStreamingTab(self),"Twitter Streaming")
        self.RequestTabs.addTab(FacebookTab(self), "Facebook")
        self.RequestTabs.addTab(AmazonTab(self),"Amazon")
        self.RequestTabs.addTab(GenericTab(self),"Generic")

        module = self.settings.value('module',False)
        tab = self.getModule(module)
        if tab is not None:
            self.RequestTabs.setCurrentWidget(tab)

        #Fetch settings
        #-Level
        self.levelEdit=QSpinBox(self.mainWidget)
        self.levelEdit.setMinimum(1)
        self.levelEdit.setToolTip(wraptip("Based on the selected nodes, only fetch data for nodes and subnodes of the specified level (base level is 1)"))
        fetchsettings.addRow("Node level",self.levelEdit)

        #-Selected nodes
        self.allnodesCheckbox = QCheckBox(self)
        self.allnodesCheckbox.setCheckState(Qt.Unchecked)
        self.allnodesCheckbox.setToolTip(wraptip("Check if you want to fetch data for all nodes. This helps with large datasets because manually selecting all nodes slows down Facepager."))
        fetchsettings.addRow("Select all nodes", self.allnodesCheckbox)

        #Object types
        self.typesEdit = QLineEdit('offcut')
        self.typesEdit.setToolTip(wraptip("Skip nodes with these object types, comma separated list. Normally this should not be changed."))
        fetchsettings.addRow("Exclude object types",self.typesEdit)

        # #-Empty nodes
        # self.emptynodesCheckbox = QCheckBox(self)
        # self.emptynodesCheckbox.setCheckState(Qt.Unchecked)
        # self.emptynodesCheckbox.setToolTip(wraptip("Check if you want to fetch data only for nodes without children. This can be used to continue cancelled data collection."))
        # fetchsettings.addRow("Select only empty nodes", self.emptynodesCheckbox)

        #-Continue pagination
        self.resumeCheckbox = QCheckBox(self)
        self.resumeCheckbox.setCheckState(Qt.Unchecked)
        self.resumeCheckbox.setToolTip(wraptip("Check if you want to continue collection after fetching was cancelled or nodes were skipped. The last fetched offcut or data node is used to determine the pagination value. Nodes are skipped if no pagination value can be found. Nodes without children having status fetched(200) are processed anyway."))
        fetchsettings.addRow("Resume collection", self.resumeCheckbox)

        # Thread Box
        self.threadsEdit = QSpinBox(self)
        self.threadsEdit.setMinimum(1)
        self.threadsEdit.setMaximum(40)
        self.threadsEdit.setToolTip(wraptip("The number of concurrent threads performing the requests. Higher values increase the speed, but may result in API-Errors/blocks"))
        fetchsettings.addRow("Parallel Threads", self.threadsEdit)

        # Speed Box
        self.speedEdit = QSpinBox(self)
        self.speedEdit.setMinimum(1)
        self.speedEdit.setMaximum(60000)
        self.speedEdit.setValue(200)
        self.speedEdit.setToolTip(wraptip("Limit the total amount of requests per minute (calm down to avoid API blocking)"))
        fetchsettings.addRow("Requests per minute", self.speedEdit)

        #Error Box
        self.errorEdit = QSpinBox(self)
        self.errorEdit.setMinimum(1)
        self.errorEdit.setMaximum(100)
        self.errorEdit.setValue(10)
        self.errorEdit.setToolTip(wraptip("Set the number of consecutive errors after which fetching will be cancelled. Please handle with care! Continuing with erroneous requests places stress on the servers."))
        fetchsettings.addRow("Maximum errors", self.errorEdit)


        #Add headers
        self.headersCheckbox = QCheckBox(self)
        #self.headersCheckbox.setCheckState(Qt.Checked)
        self.headersCheckbox.setToolTip(wraptip("Check if you want to create nodes containing headers of the response."))
        fetchsettings.addRow("Header nodes", self.headersCheckbox)

        #Expand Box
        self.autoexpandCheckbox = QCheckBox(self)
        self.autoexpandCheckbox.setCheckState(Qt.Unchecked)
        self.autoexpandCheckbox.setToolTip(wraptip("Check to automatically expand new nodes when fetching data. Disable for big queries to speed up the process."))
        fetchsettings.addRow("Expand new nodes", self.autoexpandCheckbox)

        #Log Settings
        self.logCheckbox = QCheckBox(self)
        self.logCheckbox.setCheckState(Qt.Checked)
        self.logCheckbox.setToolTip(wraptip("Check to see every request in status window; uncheck to hide request messages."))
        fetchsettings.addRow("Log all requests", self.logCheckbox)

        #Clear setttings
        self.clearCheckbox = QCheckBox(self)
        self.settings.beginGroup("GlobalSettings")
        clear = self.settings.value('clearsettings',False)
        self.clearCheckbox.setChecked(str(clear)=="true")
        self.settings.endGroup()

        self.clearCheckbox.setToolTip(wraptip("Check to clear all settings and access tokens when closing Facepager. You should check this on public machines to clear credentials."))
        fetchsettings.addRow("Clear settings when closing", self.clearCheckbox)


        
        #Fetch data

        #-button
        f=QFont()
        f.setPointSize(11)
        button=QPushButton(QIcon(":/icons/fetch.png"),"Fetch Data", self.mainWidget)
        button.setToolTip(wraptip("Fetch data from the API with the current settings"))
        button.setMinimumSize(QSize(120,40))
        button.setIconSize(QSize(32,32))
        button.clicked.connect(self.actions.actionQuery.trigger)
        button.setFont(f)
        fetchdata.addWidget(button,1)

        #-timer button
        button=QToolButton(self.mainWidget)
        button.setIcon(QIcon(":/icons/timer.png"))
        button.setMinimumSize(QSize(40,40))
        button.setIconSize(QSize(25,25))
        button.clicked.connect(self.actions.actionTimer.trigger)
        fetchdata.addWidget(button,1)

        #Status
        detailGroup=QGroupBox("Status Log")
        groupLayout=QVBoxLayout()
        detailGroup.setLayout(groupLayout)
        statusLayout.addWidget(detailGroup,1)


        self.loglist=QTextEdit()
        self.loglist.setLineWrapMode(QTextEdit.NoWrap)
        self.loglist.setWordWrapMode(QTextOption.NoWrap)
        self.loglist.acceptRichText=False
        self.loglist.clear()
        groupLayout.addWidget(self.loglist)

    def databaseLabelClicked(self):
        if self.database.connected:
            if platform.system() == "Windows":
                webbrowser.open(os.path.dirname(self.database.filename))
            elif platform.system() == "Darwin":
                webbrowser.open('file:///'+os.path.dirname(self.database.filename))
            else:
                webbrowser.open('file:///'+os.path.dirname(self.database.filename))


    def getModule(self,module):
        for i in range(0, self.RequestTabs.count()):
            if self.RequestTabs.widget(i).name == module:
                tab = self.RequestTabs.widget(i)
                return tab
        return None

    def updateUI(self):
        #disable buttons that do not work without an opened database
        self.actions.databaseActions.setEnabled(self.database.connected)
        self.actions.actionQuery.setEnabled(self.tree.selectedCount() > 0)

        if self.database.connected:
            #self.statusBar().showMessage(self.database.filename)
            self.databaseLabel.setText(self.database.filename)
        else:
            #self.statusBar().showMessage('No database connection')
            self.databaseLabel.setText('No database connection')

    # Downloads default presets and api definitions in the background
    def updateResources(self):

        self.apiWindow.checkDefaultFiles()
        self.presetWindow.checkDefaultFiles()

        def getter():
            self.apiWindow.downloadDefaultFiles(True)
            self.presetWindow.downloadDefaultFiles(True)

        t = threading.Thread(target=getter)
        t.start()


    def writeSettings(self):
        QCoreApplication.setOrganizationName("Strohne")
        QCoreApplication.setApplicationName("Facepager")

        self.settings = QSettings()
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("version","4.2")
        self.settings.endGroup()


        self.settings.setValue('columns',self.fieldList.toPlainText())
        self.settings.setValue('module',self.RequestTabs.currentWidget().name)
        self.settings.setValue("lastpath", self.database.filename)

        self.settings.beginGroup("GlobalSettings")
        self.settings.setValue("clearsettings", self.clearCheckbox.isChecked())
        self.settings.endGroup()

        for i in range(self.RequestTabs.count()):
            self.RequestTabs.widget(i).saveSettings()

    def readSettings(self):
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QCoreApplication.setOrganizationName("Strohne")
        QCoreApplication.setApplicationName("Facepager")
        self.settings = QSettings()

    def deleteSettings(self):
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QCoreApplication.setOrganizationName("Strohne")
        QCoreApplication.setApplicationName("Facepager")
        self.settings = QSettings()

        self.settings.clear()
        self.settings.sync()

        self.settings.beginGroup("GlobalSettings")
        self.settings.setValue("clearsettings", self.clearCheckbox.isChecked())
        self.settings.endGroup()


    def closeEvent(self, event=QCloseEvent()):
        if self.close():
            if self.clearCheckbox.isChecked():
                self.deleteSettings()
            else:
                self.writeSettings()
            event.accept()
        else:
            event.ignore()

    @Slot(str)
    def logmessage(self,message):
        with self.lock_logging:
            if isinstance(message,Exception):
                self.loglist.append(str(datetime.now())+" Exception: "+str(message))
                logging.exception(message)

            else:
                self.loglist.append(str(datetime.now())+" "+message)
            time.sleep(0)

class Toolbar(QToolBar):
    """
    Initialize the main toolbar for the facepager - that provides the central interface and functions.
    """
    def __init__(self,parent=None,mainWindow=None):
        super(Toolbar,self).__init__(parent)
        self.mainWindow=mainWindow
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        self.setIconSize(QSize(24,24))

        self.addActions(self.mainWindow.actions.basicActions.actions())
        self.addSeparator()
        self.addActions(self.mainWindow.actions.databaseActions.actions())

        self.addSeparator()
        #self.addAction(self.mainWindow.actions.actionExpandAll)
        #self.addAction(self.mainWindow.actions.actionCollapseAll)
        #self.addAction(self.mainWindow.actions.actionSelectNodes)
        self.addAction(self.mainWindow.actions.actionLoadPreset)
        self.addAction(self.mainWindow.actions.actionLoadAPIs)
        self.addAction(self.mainWindow.actions.actionHelp)



# See https://stackoverflow.com/questions/4795757/is-there-a-better-way-to-wordwrap-text-in-qtooltip-than-just-using-regexp
class QAwesomeTooltipEventFilter(QObject):
    '''
    Tooltip-specific event filter dramatically improving the tooltips of all
    widgets for which this filter is installed.

    Motivation
    ----------
    **Rich text tooltips** (i.e., tooltips containing one or more HTML-like
    tags) are implicitly wrapped by Qt to the width of their parent windows and
    hence typically behave as expected.

    **Plaintext tooltips** (i.e., tooltips containing no such tags), however,
    are not. For unclear reasons, plaintext tooltips are implicitly truncated to
    the width of their parent windows. The only means of circumventing this
    obscure constraint is to manually inject newlines at the appropriate
    80-character boundaries of such tooltips -- which has the distinct
    disadvantage of failing to scale to edge-case display and device
    environments (e.g., high-DPI). Such tooltips *cannot* be guaranteed to be
    legible in the general case and hence are blatantly broken under *all* Qt
    versions to date. This is a `well-known long-standing issue <issue_>`__ for
    which no official resolution exists.

    This filter globally addresses this issue by implicitly converting *all*
    intercepted plaintext tooltips into rich text tooltips in a general-purpose
    manner, thus wrapping the former exactly like the latter. To do so, this
    filter (in order):

    #. Auto-detects whether the:

       * Current event is a :class:`QEvent.ToolTipChange` event.
       * Current widget has a **non-empty plaintext tooltip**.

    #. When these conditions are satisfied:

       #. Escapes all HTML syntax in this tooltip (e.g., converting all ``&``
          characters to ``&amp;`` substrings).
       #. Embeds this tooltip in the Qt-specific ``<qt>...</qt>`` tag, thus
          implicitly converting this plaintext tooltip into a rich text tooltip.

    .. _issue:
        https://bugreports.qt.io/browse/QTBUG-41051
    '''


    def eventFilter(self, widget: QObject, event: QEvent) -> bool:
        '''
        Tooltip-specific event filter handling the passed Qt object and event.
        '''


        # If this is a tooltip event...
        if event.type() == QEvent.ToolTipChange:
            # If the target Qt object containing this tooltip is *NOT* a widget,
            # raise a human-readable exception. While this should *NEVER* be the
            # case, edge cases are edge cases because they sometimes happen.
            if not isinstance(widget, QWidget):
                raise ValueError('QObject "{}" not a widget.'.format(widget))

            # Tooltip for this widget if any *OR* the empty string otherwise.
            tooltip = widget.toolTip()

            # If this tooltip is both non-empty and not already rich text...
            if tooltip and not tooltip.startswith('<'): #not Qt.mightBeRichText(tooltip):
                tooltip = '<qt>{}</qt>'.format(html.escape(tooltip))
                widget.setToolTip(tooltip)

                # Notify the parent event handler this event has been handled.
                return True

        # Else, defer to the default superclass handling of this event.
        return super().eventFilter(widget, event)

def startMain():
    app = QApplication(sys.argv)

    # Change styling for Mac
    if cmd_args.style is not None:
        QApplication.setStyle(cmd_args.style)
    elif sys.platform == 'darwin':
        QApplication.setStyle('Fusion')

    # Word wrap tooltips (does not work yet, chrashes app)
    #tooltipfilter = QAwesomeTooltipEventFilter(app)
    #app.installEventFilter(tooltipfilter)

    main=MainWindow()
    main.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    # Logging
    try:
        logfolder = os.path.join(os.path.expanduser("~"),'Facepager','Logs')
        if not os.path.isdir(logfolder):
            os.makedirs(logfolder)
        logging.basicConfig(filename=os.path.join(logfolder,'facepager.log'),level=logging.ERROR,format='%(asctime)s %(levelname)s:%(message)s')
    except Exception as e:
        print("Error intitializing log file: {}".format(e.message))

    # Command line options
    cmd_args = argparse.ArgumentParser(description='Run Facepager.')
    cmd_args.add_argument('database', help='Database file to open', nargs='?')
    cmd_args.add_argument('--style', dest='style', default=None, help='Select the PySide style, for example Fusion')

    cmd_args = cmd_args.parse_args()

    # Locate the SSL certificate for requests
    os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(getResourceFolder() , 'ssl', 'cacert.pem')

    startMain()
