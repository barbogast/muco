from functools import partial
import traceback

from PyQt4.QtCore import (QThread, QWriteLocker, QMutex, QMutexLocker, Qt, 
                          SIGNAL, SLOT, QTimer, QVariant)
from PyQt4.QtGui import (QTableWidgetItem)


class Action(object):
    def get_name(self):
        return 'An action template'
    
    def get_state(self):
        return {'someFancyState':123}
    
    def run_action(self):
        raise NotImplemented()
    

class ActionRunner(QThread):
    def __init__(self, action, parent=None):
        super(ActionRunner, self).__init__(parent)
        
        self._action = action
        self._actionIter = None
        
        self.ALLOWED_STATES = frozenset(['pause', 'paused', 'finished', 'running', 'error'])
        self._state = ''
        self._stateMutex = QMutex()
        
        self._progressPercentage = None
        self._progressItem = None
        self._progressMutex = QMutex()
        
    def get_action_name(self):
        return self._action.get_name()
    
    def set_state(self, newState):
        if not newState in self.ALLOWED_STATES:
            raise ValueError('New state must be one of %s'%self.ALLOWED_STATES)
        with QMutexLocker(self._stateMutex):
            self._state = newState
            self.emit(SIGNAL("newState"), self._state)

    def get_state(self):
        with QMutexLocker(self._stateMutex):
            return self._state
        
    def get_progress(self):
        with QMutexLocker(self._progressMutex):
            return (self._progressPercentage, self._progressItem)
        
    def run(self):
        if self._actionIter is None:
            self._actionIter = self._action.run_action()
            
        self.set_state('running')
        try:
            while True:
                if self.get_state() == 'pause':
                    self.set_state('paused')
                    break

                progress = self._actionIter.next()
                
                with QMutexLocker(self._progressMutex):
                    (self._progressPercentage, self._progressItem) = progress
                    
        except StopIteration:
            self.set_state('finished')
        except Exception, e:
            self.set_state('error')
            print e
            print traceback.format_exc()
            raise e

        print 'run ende'            
    
          
            
class ActionController(object):
    STATUS, NAME, PROGRESS, CURRENT = range(4)
    HEADERS = ('Status', 'Name', 'Progress', 'Current Item')

    def __init__(self, ui, parent):
        self.parent = parent
        self._tableWidget = ui.table_actions

        self._tableWidget.setColumnCount(len(self.HEADERS))
        self._tableWidget.setHorizontalHeaderLabels(self.HEADERS)
                
        self._actionRunnerList = []
        ui.button_pause.connect(ui.button_pause, SIGNAL('clicked()'), self.pause_action)
        ui.button_clear.connect(ui.button_clear, SIGNAL('clicked()'), self.clear_list)
         
        self._timer = QTimer()
        self._timer.connect(self._timer, SIGNAL('timeout()'), self.update_progress)
        self._timer.start(500)
        
        self._noOpenActions = 0
        
    def add_action(self, action):
        actionRunner = ActionRunner(action, self.parent)
        actionRunnerID = id(actionRunner)
        actionRunner.connect(actionRunner, SIGNAL('newState'), partial(self.state_changed, actionRunner))
        
        self._actionRunnerList.append(actionRunner)
        actionRunner.start()

        count = len(self._actionRunnerList)
        row = count - 1
        self._tableWidget.setItem(row, self.NAME, QTableWidgetItem(actionRunner.get_action_name()))
        self._tableWidget.setItem(row, self.PROGRESS, QTableWidgetItem('0'))
        self._tableWidget.resizeColumnsToContents()
        self._tableWidget.setRowCount(count)
        self._noOpenActions += 1
        
        return actionRunnerID
                
      
    def pause_action(self):
        row = self._tableWidget.currentRow()
        if row is None:
            return
        try:
            actionRunner = self._actionRunnerList[row]
        except IndexError:
            return
        state = actionRunner.get_state()
        if state == 'running':
            actionRunner.set_state('pause')
        elif state == 'paused':
            actionRunner.start()
        
   
    def state_changed(self, actionRunner, state):
        print 'state changed', state
        row = self._actionRunnerList.index(actionRunner)
        item = self._tableWidget.setItem(row, self.STATUS, QTableWidgetItem(state))
        if state in ('finished', 'error'):
            self._noOpenActions -= 1
        self._tableWidget.resizeColumnsToContents()
            
    def get_no_open_actions(self):
        return self._noOpenActions

        
    def update_progress(self):
        for row, actionRunner in enumerate(self._actionRunnerList):
            percentage, currentItem = actionRunner.get_progress()
            if percentage:
                self._tableWidget.setItem(row, self.PROGRESS, QTableWidgetItem('%s'%percentage))
            if currentItem:
                self._tableWidget.setItem(row, self.CURRENT, QTableWidgetItem(currentItem))
            
    
    def clear_list(self):
        newL = []
        for row, actionRunner in enumerate(self._actionRunnerList):
            state = actionRunner.get_state()
            if state in ('finished', 'error'):
                self._tableWidget.removeRow(row)
            else:
                newL.append(actionRunner)
        self._actionRunnerList = newL
        self._tableWidget.setRowCount(len(newL))
    
        
        
class TestAction(Action):
    def __init__(self, name, length):
        self.length = length
        self.name = name
        
    def get_name(self):
        return 'Count to %s with one second pause in each step'%self.length
    
    def run_action(self):
        import time
        for i in xrange(self.length):
            time.sleep(1)
            if i%3==0:
                yield (i*100/self.length, 'das ist nr %s'%i)
        yield (100, 'das ist nr %s'%self.length)
                
                