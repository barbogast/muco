from functools import partial
import traceback

from PyQt4.QtCore import (QThread, QWriteLocker, QMutex, QMutexLocker, Qt, 
                          SIGNAL, QTimer, QVariant)
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
            #raise e

        print 'run ende'            
    
          
            
class ActionController(object):
    STATUS, NAME, PROGRESS, CURRENT = range(4)
    HEADERS = ('Status', 'Name', 'Progress', 'Current Item')

    def __init__(self, tableWidget, pauseButton, parent):
        self.parent = parent
        self._tableWidget = tableWidget

        self._tableWidget.setColumnCount(len(self.HEADERS))
        self._tableWidget.setHorizontalHeaderLabels(self.HEADERS)
                
        self._actionRunnerDict = {} # key=id(action), value=ActionRunner
        self._actionRunnerList = []
        pauseButton.connect(pauseButton, SIGNAL('clicked()'), self.pause_action)
         
        self._timer = QTimer()
        self._timer.connect(self._timer, SIGNAL('timeout()'), self.update_progress)
        self._timer.start(500)
        
        self._noOpenActions = 0
        
    def add_action(self, action):
        actionRunner = ActionRunner(action, self.parent)
        actionRunnerID = id(actionRunner)
        actionRunner.connect(actionRunner, SIGNAL('newState'), partial(self.state_changed, actionRunner))
        self._actionRunnerDict[actionRunnerID] = actionRunner
        
        self._actionRunnerList.append(actionRunner)
        actionRunner.start()

        count = len(self._actionRunnerDict)
        self._tableWidget.setRowCount(count)
        row = count - 1
        self._tableWidget.setItem(row, self.NAME, QTableWidgetItem(actionRunner.get_action_name()))
        self._tableWidget.setItem(row, self.PROGRESS, QTableWidgetItem('0'))
        self._tableWidget.resizeColumnsToContents()
        self._noOpenActions += 1
        
        return actionRunnerID
                
      
    def pause_action(self):
        row = self._tableWidget.currentRow()
        if row is None:
            return
        actionRunner = self._actionRunnerList[row]
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
                
                
                
#class ActionControllerAlt(object):
    #def __init__(self, listWidget, pauseButton, resumeButton, parent):
        #self.parent = parent
        #self._listWidget = listWidget
        #self._actionRunnerDict = {}
        #self._actionRunnerList = []
        #pauseButton.connect(pauseButton, SIGNAL('clicked()'), self.pause_action)
        #resumeButton.connect(resumeButton, SIGNAL('clicked()'), self.resume_action)
        
        #self._timer = QTimer()
        #self._timer.connect(self._timer, SIGNAL('timeout()'), self.update_progress)
        #self._timer.start(500)
        
    #def add_action(self, action):
        #a = ActionRunner(action, self.parent)
        #aID = id(a)
        
        #a.connect(a, SIGNAL('newState'), partial(self.state_changed, a))
        #self._actionRunnerDict[aID] = a
        #self._actionRunnerList.append(a)
        #a.start()
        #self._listWidget.addItem( '%s   ...started'%(action,))
        #return aID
                
      
    #def pause_action(self):
        #row = self._listWidget.currentRow()
        #if row is None:
            #return
        #a = self._actionRunnerList[row]
        #if a.get_state() == 'running':
            #a.set_state('pause')
        
        
    #def resume_action(self):
        #row = self._listWidget.currentRow()
        #if row is None:
            #return
        #self._actionRunnerList[row].start()

    #def state_changed(self, action, state):
        #print 'state changed', state
        #index = self._actionRunnerList.index(action)
        #item = self._listWidget.item(index)
        #item.setData(Qt.DisplayRole, '%s   ...%s'%(action, state))
        
    #def update_progress(self):
        #for index, action in enumerate(self._actionRunnerList):
            #percentage, currentItem = action.get_progress()
            #listItem = self._listWidget.item(index)
            #listItem.setData(Qt.DisplayRole, '%s ... %s, %s'%(action, percentage, currentItem))
                
                
#from twisted.internet import defer
#from zope.interface import Interface

        
#class IListener(object):
    #def new_state(self, state, info):
        #""" """
    #def step(self, newState):
        #""" """
        
#class IAction(Interface):
    ##@defer.inlineCallbacks
    ##def doStart(self):
        ##""" Do starting tasks. Dont call self.doStep() here, it will be called
        ##from the controller."""
    
    #@defer.inlineCallbacks
    #def doStep(self):
        #""" Do one step of the action and return the new state. Dont call 
        #self.doStep() here. Instead raise StopAction() to tell the controller 
        #that you are done. It will then call self.doStop()"""
        
    #@defer.inlineCallbacks
    #def doStop(self):
        #""" Do finishing tasks """
    
#class StopAction(Exception):
    #pass

    
#class ActionController(object):
    #def __init__(self, action, listeners):
        #self.listeners = listeners
        #self.action = action
        #self.state = 'stopped'
        #self._doStopCb = None
        #self._doPauseCb = None

    #def new_state(self, state, info=None):
        #self.state = state
        #for l in listeners:
            #l.new_state(self.state, info)
        
    
    #@inlineCallbacs
    #def start(self, callback):
        #if self.state in ('started', 'pausing', 'stopping'):
            #raise RuntimeError('The current state of the action is %s. Starting is not allowed')
        #self.new_state('started')
        #yield self._run()
    
    #def stop(self, callback):
        #self._doStopCb = callback
        
    #def pause(self, callback):
        #self._doPauseCb = callback

    #@inlineCallbacks
    #def _run(self):
        #yield 
        #while True:

            #if self._doPauseCb:
                #self._doPauseCb = None
                #return

            #elif self._doStopCb:
                #self.new_state('stopping')
                #try:
                    #yield self.action.doStop()
                    #self.new_state('stopped')
                    #self._doStopCb.callback()
                #except Exception, e:
                    #self.new_state('error', e)
                    #self._doStopCb.errback(e)
                    #break
                #self._doStopCb = None
            #else:
                #try:
                    #newState = yield self.action.doActionStep()
                #except StopAction:
                    #yield self.action.doStop()
                    #self.new_state('stopped')
                    #break
                #except Exception, e:
                    #self.new_state('error', e)
                    #for l in self.listeners:
                        #l.step(newState)
                        
                        
#class Action(object):
    #@inlineCallbacks
    #def doActionStep(self):
        #yield x.callRemote('asdf')
        #self.state += 1
        #if isFinished:
            #raise StopAction()
        #returnValue(action.state)
