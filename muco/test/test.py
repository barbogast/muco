# *-* coding: utf-8 -*-

import unittest as ut
import sqlite3
import os
import shutil

import apsw


from muco.model import Model
from muco.model import ImportFilesAction, CheckFilesAction, DeleteFilesAction


class SqliteForeignKeys(ut.TestCase):
    #TEST_DB_PATH = os.path.join(os.path.realpath('./testdata'), 'test.sqlite')
    
    def setUp(self):
        try: os.remove(self.TEST_DB_PATH) 
        except: pass
        #self.conn = apsw.Connection(self.TEST_DB_PATH)
        self.conn = apsw.Connection(':memory:')
        self.conn.cursor().execute(open('../schema.sql').read())
        cur = self.conn.cursor()
        cur.execute("insert into folder (name) values ('folder1')")
        cur.execute("""insert into file (name, folder_id) values ('file1', 
                            (select id from folder where name = 'folder1'))""")

    def tearDown(self):
        #self.conn.commit()
        self.conn.close()
        #os.remove(self.TEST_DB_PATH)
        
    def test_select(self):
        cur = self.conn.cursor()
        cur.execute("select fo.name from folder fo, file fi where fi.folder_id = fo.id")
        res = list(cur)[0][0]
        self.assertEqual(res, 'folder1')
        
    def test_insert(self):
        def doIt(cur):
            cur.execute("insert into file (name, folder_id) values ('file2', 2)")
        cur = self.conn.cursor()
        self.assertRaises(apsw.ConstraintError, doIt, cur)
        self.assertRaises
    
    def test_update(self):
        def doIt(cur):
            cur.execute("update file set folder_id = 3 where id = 1")
        cur = self.conn.cursor()
        self.assertRaises(apsw.ConstraintError, doIt, cur)

    def test_delete(self):
        def doIt(cur):
            cur.execute("delete from folder where id = 1")
        cur = self.conn.cursor()
        self.assertRaises(apsw.ConstraintError, doIt, cur)
    

class TestFileCreator(object):
    def __init__(self, testpath):
        self._fullPaths = set() # Every write action checks if the required file is in here
        self._testpath = testpath

        
    def createFolder(self, path, fileDict):
        if not path.startswith(self._testpath):
            raise ValueError('path doesnt start with testpath', path, self._testpath)
        if not os.path.exists(path):
            os.mkdir(path)
            self._fullPaths.add(path)
        else:
            print 'Folder exists', path
        for name, content in fileDict.iteritems():
            if isinstance(content, basestring):
                self.createFile(os.path.join(path, name), content)
            elif type(content) == dict:
                self.createFolder(os.path.join(path, name), content)
            else:
                raise ValueError('Value of fileDict may be either string for ',
                                 'files or dict for directories')

            
    def createFile(self, path, content):
        if not path.startswith(self._testpath):
            raise ValueError('path doesnt start with testpath', path, self._testpath)
        if os.path.exists(path):
            print 'File exists:', path
            return
        with open(path, 'w') as f:
            f.write(content)
        self._fullPaths.add(path)
            
    
    def editFile(self, path, mode, content):
        if not path in self._fullPaths:
            print 'File was not created', path
            return
        with open(path, mode) as f:
            f.write(content)

            
    def removeFile(self, path):
        if not path in self._fullPaths:
            print 'File was not created', path
            return
        os.remove(path)
        self._fullPaths.remove(path)

        
    def removeFolder(self, path):
        if not path in self._fullPaths:
            print 'Folder was not created', path
            return
        os.rmdir(path)
        self._fullPaths.remove(path)

        
    def removeFolderRecursive(self, path):
        if not path in self._fullPaths:
            print 'Folder was not created', path
            return
        for el in os.listdir(path):
            elPath = os.path.join(path, el)
            if os.path.isfile(elPath):
                self.removeFile(elPath)
            elif os.path.isdir(elPath):
                self.removeFolderRecursive(elPath)
        self.removeFolder(path)
        
        
    def removeAll(self):
        #shutil.rmtree(self._testpath)
        for element in reversed(sorted(self._fullPaths)):
            if not os.path.exists(element):
                continue
            if os.path.isfile(element):
                self.removeFile(element)
            elif os.path.isdir(element):
                self.removeFolder(element)
            else:
                raise ValueError('Element in self._fullPaths is neither file or dir', path)


class TestFSCreator_Test(ut.TestCase):
    def setUp(self):
        pass
    
class ActionTester(object):
    def __init__(self, action):
        self.actionClass = actionClass
        
    def runAction(self, *args):
        o = self.actionClass(*args)
        for state, stats in o.run_action():
            pass
print open('../schema.sql').read()        
class TestModel(ut.TestCase):
    files = {
        'file0_1.txt': 'testtext',
        'file0_2.txt': 'testtext',
        'file0_3.txt': 'testtext',
        'folder1': {
            'file1_1.txt': 'testtext',
            'file1_2.txt': 'testtext',
            'file1_3.txt': 'testtext',
        },
        'folder2': {
            'file2_1.txt': 'testtext',
            'file2_2.txt': 'testtext',
            'file2_3.txt': 'testtext',
        },
        'folder3': {},
        'folder4': {
            'file4_1.txt': 'testtext',
            'file4_2.txt': 'testtext',
            'file4_3.txt': 'testtext',
            'folder4_4': {
                'file4_4_1.txt': 'testtext',
                'file4_4_2.txt': 'testtext',
                'file4_4_3.txt': 'testtext',
            }
        }
            
    }
    TEST_DB_PATH = os.path.join(os.path.realpath('./testdata'), 'test.sqlite')
            
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        #self.conn = sqlite3.connect(self.TEST_DB_PATH)
        self.conn.executescript(open('../schema.sql').read())
        self.conn.commit()
        
        self.model = Model()
        self.model.set_connection(self.conn)
        path = '/tmp/test'
        self.tf = TestFileCreator(path)
        self.tf.createFolder(path, self.files)
        
    def test_insertFile(self):
        a = ImportFilesAction(self.model, '/tmp/test/file0_1.txt')
        for info in a.run_action():
            pass
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        
    def test_insertFileFromDifferentFolders(self):
        a = ImportFilesAction(self.model, '/tmp/test/file0_1.txt')
        for info in a.run_action():
            pass
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        a = ImportFilesAction(self.model, '/tmp/test/file0_1.txt')
        for info in a.run_action():
            pass
        self.assertFalse(self.model.get_file_by_path('/tmp/test/folder4/file4_1.txt').is_none())
    
        
    def test_deleteFile(self):
        a = ImportFilesAction(self.model, '/tmp/test/file0_1.txt')
        for info in a.run_action():
            pass
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        a = DeleteFilesAction(self.model, '/tmp/test/file0_1.txt')
        for info in a.run_action():
            pass
        self.assertTrue(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
            
   
    def tearDown(self):
        self.tf.removeAll()
        #os.remove(self.TEST_DB_PATH)
    #def
    
     # Dateien in eine neue DB einfügen
    """
     * einzelne Datei einfuegen/loeschen
     * viele dateien einfuegen
     * einzelnes verzeichnis
     * viele veziechnisse
     * leeres verzeichnis einfuegen/loeschen
     * verzeichnis mit dateien einfuegen/loeschen
     * verzeichnis mti unterdateien einfuegen/loeschen
     * import von leerem verzeichnis
    
    # Volles Verzeichnis loeschen
    # Leeres Verzeichnis loeschen
    
    # Dateien einfuegen in einem Verzeichnis, das es schon gibt
    # Dateien einfuegen in einem Ortner, dessen unter-unterordner schon in der DB ist
    # Verzeichnis rekursiv einfuegen
    * letzte datei aus einem verzeichnis löschen
    
    * einzelne datei pruefen
    * verzeichnis pruefen
    * einzelne datei fehlt
    * verzeichnis fehlt
    
    check: datei ist nun fehlerhaft. werden alle übergeordneten verzeichnisse markiert?
    check: fehlerhafte datei ist wieder ok. werden alle übergeordneten verzeichnisse entmarkiert?
    check: fehlerhafte datei ist wieder ok, andere datei ist nun fehlerhaft
    check: fehlerhafte datei ist wieder ok. übergeordnetes verzeichnis soll neu geprüft werden. hier ist aber noch eine fehlerhafte datei enthalten
    die einzige fehlerhafte datei wird entfernt.
    
    * nicht lesbare verzeichnisse und dateien
    * inks, verknuepfungen und mount points
    
    * pruefen, ob sich alles richtig verhaelt, wenn zwei Ordner oder dateien denselben namen haben
    
    tests fuer folder.is_ok
     * 
    """
    
    
    
    