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
                dbID = self.folderCache[path]
                return QtGui.QColor('yellow')
            except KeyError:
                dbID = self.dbmodel.folder(path, False)
                if not dbID is None:
                    self.folderCache[path] = dbID
                
        else:
            try:
                f = self.fileCache[path]
                if not f.is_none():
                    if f.hash_is_wrong:
                        return QtGui.QColor('red')
                    return QtGui.QColor('yellow')
                
            except KeyError:
                f = self.dbmodel.file(path, False)
                if not f.is_none():
                    self.fileCache[path] = f
    
        
      
    def import_el(self, indexes):
        index = indexes[0]
        path = unicode(self.filePath(index))
        action = ImportFilesAction(path)
        self.actionController.add_action(action)
        self.dbmodel.commit()
        self.dbcache = {}
        self.emit(QtCore.SIGNAL('dataChanged()'))
        
    def delete_el(self, indexes):
        index = indexes[0]
        path = unicode(self.filePath(index))
        action = DeleteFilesAction(path)
        self.actionController.add_action(action)
        self.dbmodel.commit()
        self.dbcache = {}
        self.emit(QtCore.SIGNAL('dataChanged()'))
        
    def check_el(self, indexes):
        index = indexes[0]
        path = unicode(self.filePath(index))
        action = CheckFilesAction(path)
        self.actionController.add_action(action)
        #self.dbmodel.commit()
        #self.dbcache = {}
        #self.emit(QtCore.SIGNAL('dataChanged()'))
        
        
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
        
        self.actionController = ActionController(self.ui.table_actions, self.ui.button_pause, self)
        
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
        s = '%(folders)s Verzeichnisse\n%(files)s Dateien'%stats
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

    
    

    