# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/main.ui'
#
# Created: Tue Oct 12 20:50:52 2010
#      by: PyQt4 UI code generator 4.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1074, 830)
        MainWindow.setMouseTracking(False)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setMouseTracking(False)
        self.centralwidget.setObjectName("centralwidget")
        self.splitter_2 = QtGui.QSplitter(self.centralwidget)
        self.splitter_2.setGeometry(QtCore.QRect(9, 9, 1061, 771))
        self.splitter_2.setOrientation(QtCore.Qt.Vertical)
        self.splitter_2.setObjectName("splitter_2")
        self.splitter = QtGui.QSplitter(self.splitter_2)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtGui.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtGui.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.treeView = QtGui.QTreeView(self.layoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeView.sizePolicy().hasHeightForWidth())
        self.treeView.setSizePolicy(sizePolicy)
        self.treeView.setMouseTracking(False)
        self.treeView.setObjectName("treeView")
        self.treeView.header().setStretchLastSection(False)
        self.verticalLayout.addWidget(self.treeView)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.button_import = QtGui.QPushButton(self.layoutWidget)
        self.button_import.setObjectName("button_import")
        self.horizontalLayout.addWidget(self.button_import)
        self.buttom_remove = QtGui.QPushButton(self.layoutWidget)
        self.buttom_remove.setObjectName("buttom_remove")
        self.horizontalLayout.addWidget(self.buttom_remove)
        self.button_check = QtGui.QPushButton(self.layoutWidget)
        self.button_check.setObjectName("button_check")
        self.horizontalLayout.addWidget(self.button_check)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.textEdit = QtGui.QTextEdit(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textEdit.sizePolicy().hasHeightForWidth())
        self.textEdit.setSizePolicy(sizePolicy)
        self.textEdit.setObjectName("textEdit")
        self.verticalLayoutWidget = QtGui.QWidget(self.splitter_2)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.table_actions = QtGui.QTableWidget(self.verticalLayoutWidget)
        self.table_actions.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table_actions.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table_actions.setObjectName("table_actions")
        self.table_actions.setColumnCount(0)
        self.table_actions.setRowCount(0)
        self.verticalLayout_2.addWidget(self.table_actions)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.button_pause = QtGui.QPushButton(self.verticalLayoutWidget)
        self.button_pause.setObjectName("button_pause")
        self.horizontalLayout_2.addWidget(self.button_pause)
        self.button_clear = QtGui.QPushButton(self.verticalLayoutWidget)
        self.button_clear.setObjectName("button_clear")
        self.horizontalLayout_2.addWidget(self.button_clear)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1074, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.button_import.setText(QtGui.QApplication.translate("MainWindow", "Importieren", None, QtGui.QApplication.UnicodeUTF8))
        self.buttom_remove.setText(QtGui.QApplication.translate("MainWindow", "Entfernen", None, QtGui.QApplication.UnicodeUTF8))
        self.button_check.setText(QtGui.QApplication.translate("MainWindow", "Prüfen", None, QtGui.QApplication.UnicodeUTF8))
        self.button_pause.setText(QtGui.QApplication.translate("MainWindow", "Pause/Fortsetzen", None, QtGui.QApplication.UnicodeUTF8))
        self.button_clear.setText(QtGui.QApplication.translate("MainWindow", "Beendete entfernen", None, QtGui.QApplication.UnicodeUTF8))

