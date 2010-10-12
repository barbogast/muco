# -*- coding: utf-8 -*-

import sys

from twisted.internet import threads
from PyQt4 import QtCore, QtGui

from gui import Ui_MainWindow
from model import Model, get_connection, ImportFilesAction, DeleteFilesAction, CheckFilesAction
from action import ActionController, TestAction


class FSModel(QtGui.QFileSystemModel):
    def __init__(self, actionController, parent):
        self.actionController = actionController
        super(FSModel, self).__init__(parent)
        
    def set_dbmodel(self, dbmodel):
        self.dbmodel = dbmodel
        self.fileCache = {}
        self.folderCache = {}
        
    def data(self, index, role):
        if role != 8:
            return super(FSModel, self).data(index, role)
            
        path = unicode(self.filePath(index))
        
        if self.isDir(index):
            try:
                fo = self.folderCache[path]
                if not fo.is_none():
                    if not fo.is_ok:
                        return QtGui.QColor('red')
                    return QtGui.QColor('yellow')
            except KeyError:
                fo = self.dbmodel.get_folder_by_path(path)
                if not fo.is_none():
                    self.folderCache[path] = fo
                
        else:
            try:
                fi = self.fileCache[path]
                if not fi.is_none():
                    if fi.hash_is_wrong:
                        return QtGui.QColor('red')
                    return QtGui.QColor('yellow')
                
            except KeyError:
                fi = self.dbmodel.get_file_by_path(path)
                if not fi.is_none():
                    self.fileCache[path] = fi
    
    def _getPath(self, indexes):
        """ Returns the path and True if the item was found in the db"""
        if not indexes:
            return None, False
        index = indexes[0]
        path = unicode(self.filePath(index))
        if self.isDir(index):
            fo = self.dbmodel.get_folder_by_path(path)
            if not fo.is_none():
                return path, True
        else:
            fi = self.dbmodel.get_file_by_path(path)
            if not fi.is_none():
                return path, True
        return path, False
      
    def import_el(self, indexes):
        path, isInDb = self._getPath(indexes)
        if isInDb or path is None:
            return        
        action = ImportFilesAction(path)
        self.actionController.add_action(action)
        self.folderCache = {}
        self.fileCache = {}
        self.emit(QtCore.SIGNAL('dataChanged()'))
        
    def delete_el(self, indexes):
        path, isInDb = self._getPath(indexes)
        if not isInDb or path is None:
            return
        action = DeleteFilesAction(path)
        self.actionController.add_action(action)
        self.folderCache = {}
        self.fileCache = {}
        self.emit(QtCore.SIGNAL('dataChanged()'))
        
    def check_el(self, indexes):
        path, isInDb = self._getPath(indexes)
        if not isInDb or path is None:
            return
        action = CheckFilesAction(path)
        self.actionController.add_action(action)
        self.folderCache = {}
        self.fileCache = {}
        self.emit(QtCore.SIGNAL('dataChanged()'))
        
        
class StatusView(object):
    def __init__(self, w):
        self.w = w # the Qt widget

        
class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.dbmodel = Model()
        self.dbmodel.set_connection(get_connection())
        self.refresh_stats()
        
        self.actionController = ActionController(self.ui.table_actions, self.ui.button_pause, self.ui.button_clear, self)
        
        self.fsmodel = FSModel(self.actionController, self)
        self.fsmodel.set_dbmodel(self.dbmodel)
        self.fsmodel.setRootPath('/home/benjamin')
        self.ui.treeView.setModel(self.fsmodel)
        self.ui.treeView.header().resizeSection(0, 300)
        self.ui.treeView.setExpanded(self.fsmodel.index('/'), True)
        self.ui.treeView.setExpanded(self.fsmodel.index('/home'), True)
        self.ui.treeView.setExpanded(self.fsmodel.index('/home/benjamin'), True)
        self.connect(self.ui.button_import, QtCore.SIGNAL('clicked()'), self.import_el)
        self.connect(self.ui.buttom_remove, QtCore.SIGNAL('clicked()'), self.delete_el)
        self.connect(self.ui.button_check, QtCore.SIGNAL('clicked()'), self.check_el)
        
        self.statusbar = self.statusBar()
        
        
    def import_el(self):
        self.fsmodel.import_el(self.ui.treeView.selectedIndexes())
        self.refresh_stats()
        
    def delete_el(self):
        self.fsmodel.delete_el(self.ui.treeView.selectedIndexes())
        self.refresh_stats()
        
    def check_el(self):
        self.fsmodel.check_el(self.ui.treeView.selectedIndexes())
        
        
    def refresh_stats(self):
        stats = self.dbmodel.get_stats()
        
        stats['totalSize'] = round(stats['totalSize']/(1024.*1024.), 3) if stats['totalSize'] else 0
        s = u'%(folders)s Verzeichnisse\n%(files)s Dateien\n%(totalSize)s MB Gesamtgröße'%stats
        self.ui.textEdit.setPlainText(s)
        
        
    #def twisted(self):
        #from twisted.internet import reactor
        #def f(l, d):
            #i = 0
            #import time
            #while True:
                #print l, i
                #time.sleep(d)
                #i += 1
                #if i > 20:
                    #break
            
        #threads.deferToThread(f, 'a', 1)
        #threads.deferToThread(f, 'b', 2)
        
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    #import qt4reactor
    #qt4reactor.install()
    win = MainWindow()
    win.show()
    
    #from twisted.internet import reactor
    #reactor.runReturn()

    app.exec_()

    
    

    