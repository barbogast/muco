# *-* coding: utf-8 -*-

import unittest as ut
import sqlite3
import os
import shutil
import hashlib

import apsw
from nose.plugins.skip import SkipTest

from muco.model import Model
from muco.model import ImportFilesAction, CheckFilesAction, DeleteFilesAction

#import nose
#from nose.plugins import errorclass
#class Todo(Exception):
    #pass
#class TodoError(nose.plugins.errorclass.ErrorClassPlugin):
    #todo = nose.plugins.errorclass.ErrorClass(Todo, label='TODO', isfailure=False)
#nose.main(addplugins=[TodoError()])



class SqliteForeignKeys(ut.TestCase):
    #TEST_DB_PATH = os.path.join(os.path.realpath('./testdata'), 'test.sqlite')
    
    def setUp(self):
        try: os.remove(self.TEST_DB_PATH) 
        except: pass
        #self.conn = apsw.Connection(self.TEST_DB_PATH)
        self.conn = apsw.Connection(':memory:')
        self.conn.cursor().execute(open('schema.sql').read())
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


#class TestFSCreator_Test(ut.TestCase):
    #def setUp(self):
        #pass
    
#class ActionTester(object):
    #def __init__(self, action):
        #self.actionClass = actionClass
        
    #def runAction(self, *args):
        #o = self.actionClass(*args)
        #for state, stats in o.run_action():
            #pass
class TestModel(ut.TestCase):
    TEST_DB_PATH = os.path.join(os.path.realpath('./testdata'), 'test.sqlite')

    def setUp(self):
        def printer(msg): print msg
        self.model = Model()
        self.model.set_connection(sqlite3.connect(':memory:'))
        self.model.make_schema('schema.sql')
        
    #def tearDown(self):
        #os.remove(self.TEST_DB_PATH)
    ###################### Model.insert_folder() ###############################
    def test_insertFolderMountPoint(self):
        fo = self.model.insert_folder('/', None, True)
        self.assertEqual(fo.parent_folder, None)
        self.assertEqual(fo.parent_folder_id, None)
        self.assertEqual(fo.hash_, None)
        self.assertEqual(fo.is_ok, True)
        self.assertEqual(fo.name, '/')
        self.assertEqual(fo.full_path, '/')
        self.assertEqual(fo.is_mount_point, True)
        stmt = '''select name, full_path, is_mount_point, hash, is_ok from 
                     folder where id = ?'''
        res = self.model.get_connection().execute(stmt, (fo.id_,))
        self.assertEqual(list(res)[0], ('/', '/', 1, None, 1))
        
    def test_insertFolder(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/aaa', fo1, False)
        self.assertEqual(fo2.parent_folder, fo1)
        self.assertEqual(fo2.parent_folder_id, fo1.id_)
        self.assertEqual(fo2.hash_, None)
        self.assertEqual(fo2.is_ok, True)
        self.assertEqual(fo2.name, 'aaa')
        self.assertEqual(fo2.full_path, '/aaa')
        self.assertEqual(fo2.is_mount_point, False)
        self.assertEqual(fo1.child_folders[fo2.id_], fo2)
        stmt = '''select name, full_path, is_mount_point, hash, is_ok, parent_folder_id from 
                     folder where id = ?'''
        res = self.model.get_connection().execute(stmt, (fo2.id_,))
        self.assertEqual(list(res)[0], ('aaa', '/aaa', 0, None, 1, fo1.id_))
        
    def test_insertFolderFailNotMountWithoutParent(self):
        self.failUnlessRaises(Exception, self.model.insert_folder, '/', None, False)
        
    def test_insertFolderFailMountWithParent(self):
        class Mock(object): id_=5
        self.failUnlessRaises(Exception, self.model.insert_folder, '/', Mock(), True)
            
    def test_insertFolderFailWhenInsertedTwice(self):
        self.model.insert_folder('/aaa', None, True)
        self.failUnlessRaises(Exception, self.model.insert_folder, '/aaa', None, True)
        
###################### Model.insert_file() ###############################    
    def test_insertFile(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/bbb', fo1, False)       
        fi = self.model.insert_file('/aaa/bbb/ccc.txt', fo2, 1234)
        self.assertFalse(fi.is_none())
        self.assertEqual(fi.name, 'ccc.txt')
        self.assertEqual(fi.hash_is_wrong, False)
        self.assertEqual(fi.hash_, None)
        self.assertFalse(fi.folder.is_none())
        self.assertEqual(fi.folder.name, 'bbb')
        self.assertEqual(fo2.child_files[fi.id_], fi)
        stmt = '''select folder_id, name, hash, hash_is_wrong, filesize 
                    from file where id = ?'''
        res = self.model.get_connection().execute(stmt, (fi.id_,))
        self.assertEqual(list(res)[0], (fo2.id_, 'ccc.txt', None, 0, 1234))
        
    def test_insertFileInRoot(self):
        fo1 = self.model.insert_folder('/', None, True)
        fi = self.model.insert_file('/ccc.txt', fo1, 1234)
        self.assertFalse(fi.is_none())
        self.assertEqual(fi.name, 'ccc.txt')
        self.assertEqual(fi.hash_is_wrong, False)
        self.assertEqual(fi.hash_, None)
        self.assertFalse(fi.folder.is_none())
        self.assertEqual(fi.folder.name, '/')
        self.assertEqual(fo1.child_files[fi.id_], fi)
        stmt = '''select folder_id, name, hash, hash_is_wrong, filesize 
                    from file where id = ?'''
        res = self.model.get_connection().execute(stmt, (fi.id_,))
        self.assertEqual(list(res)[0], (fo1.id_, 'ccc.txt', None, 0, 1234))
        
###################### Model.insert_file_by_path() ###############################    
    def test_getFileByPathInRootWithFolder(self):
        fo1 = self.model.insert_folder('/', None, True)
        self.model.insert_file('/ccc.txt', fo1, 1234)
        fi = self.model.get_file_by_path('ccc.txt', fo1)
        self.assertFalse(fi.is_none())
        self.assertEqual(fi.name, 'ccc.txt')
        self.assertEqual(fi.hash_is_wrong, False)
        self.assertEqual(fi.hash_, None)
        self.assertFalse(fi.folder.is_none())
        self.assertEqual(fi.folder.name, '/')
        stmt = '''select folder_id, name, hash, hash_is_wrong, filesize 
                    from file where id = ?'''
        res = self.model.get_connection().execute(stmt, (fi.id_,))
        self.assertEqual(list(res)[0], (fo1.id_, 'ccc.txt', None, 0, 1234))
        
    def test_getFileByPathInRootWithoutFolder(self):
        fo1 = self.model.insert_folder('/', None, True)
        self.model.insert_file('/ccc.txt', fo1, 1234)
        fi = self.model.get_file_by_path('/ccc.txt')
        self.assertFalse(fi.is_none())
        self.assertEqual(fi.name, 'ccc.txt')
        self.assertEqual(fi.hash_is_wrong, False)
        self.assertEqual(fi.hash_, None)
        self.assertFalse(fi.folder.is_none())
        self.assertEqual(fi.folder.name, '/')
        stmt = '''select folder_id, name, hash, hash_is_wrong, filesize 
                    from file where id = ?'''
        res = self.model.get_connection().execute(stmt, (fi.id_,))
        self.assertEqual(list(res)[0], (fo1.id_, 'ccc.txt', None, 0, 1234))
    
    def test_getFileByPathWithFolder(self): 
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/bbb', fo1, False)   
        self.model.insert_file('/bbb/ccc.txt', fo2, 1234)
        fi = self.model.get_file_by_path('/bbb/ccc.txt', fo2)
        self.assertFalse(fi.is_none())
        self.assertEqual(fi.name, 'ccc.txt')
        self.assertEqual(fi.hash_is_wrong, False)
        self.assertEqual(fi.hash_, None)
        self.assertFalse(fi.folder.is_none())
        self.assertEqual(fi.folder.name, 'bbb')
        stmt = '''select folder_id, name, hash, hash_is_wrong, filesize 
                    from file where id = ?'''
        res = self.model.get_connection().execute(stmt, (fi.id_,))
        self.assertEqual(list(res)[0], (fo2.id_, 'ccc.txt', None, 0, 1234))
    
    def test_getFileByPathWithoutFolder(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/bbb', fo1, False)   
        self.model.insert_file('/bbb/ccc.txt', fo2, 1234)
        fi = self.model.get_file_by_path('/bbb/ccc.txt')
        self.assertFalse(fi.is_none())
        self.assertEqual(fi.name, 'ccc.txt')
        self.assertEqual(fi.hash_is_wrong, False)
        self.assertEqual(fi.hash_, None)
        self.assertFalse(fi.folder.is_none())
        self.assertEqual(fi.folder.name, 'bbb')
        stmt = '''select folder_id, name, hash, hash_is_wrong, filesize 
                    from file where id = ?'''
        res = self.model.get_connection().execute(stmt, (fi.id_,))
        self.assertEqual(list(res)[0], (fo2.id_, 'ccc.txt', None, 0, 1234))
        
    def test_getFileByPathFailFileMissing(self):
        fi = self.model.get_file_by_path('/bbb/ccc.txt')
        self.assertTrue(fi.is_none())
        
    def test_getFileByPathFailFolderMissing(self):
        class Mock(object): 
            id_=5
            def is_none(self):return False
        fi = self.model.get_file_by_path('/bbb/ccc.txt', Mock())
        self.assertTrue(fi.is_none())
        
    
    
def it(o):
    for i in o.run_action():pass
        
class TestFSActions(ut.TestCase):
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
        self.model = Model()
        self.model.set_connection(sqlite3.connect(':memory:'))
        #self.model.set_connection(sqlite3.connect(self.TEST_DB_PATH))
        self.model.make_schema('schema.sql')
        self.tf = TestFileCreator('/tmp/test')
        self.tf.createFolder('/tmp/test', self.files)
        
    def test_insertFile(self):
        it(ImportFilesAction(self.model, '/tmp/test/file0_1.txt'))
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        
    def test_insertFile_delete_reinsert(self):
        f = '/tmp/test/file0_1.txt'
        it(ImportFilesAction(self.model, f))
        self.assertFalse(self.model.get_file_by_path(f).is_none())
        it(DeleteFilesAction(self.model, f))
        self.assertTrue(self.model.get_file_by_path(f).is_none())
        it(ImportFilesAction(self.model, f))
        self.assertFalse(self.model.get_file_by_path(f).is_none())
        
    def test_insertFileFromDifferentFolders(self):
        it(ImportFilesAction(self.model, '/tmp/test/file0_1.txt'))
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        it(ImportFilesAction(self.model, '/tmp/test/folder4/file4_1.txt'))
        self.assertFalse(self.model.get_file_by_path('/tmp/test/folder4/file4_1.txt').is_none())
        
    def test_insertMultipleFiles(self):
        f1 = '/tmp/test/file0_1.txt'
        f2 = '/tmp/test/file0_2.txt'
        f3 = '/tmp/test/file0_3.txt'
        f4 = '/tmp/test/folder1/file1_1.txt'
        it(ImportFilesAction(self.model, f1))
        it(ImportFilesAction(self.model, f2))
        it(ImportFilesAction(self.model, f3))
        it(ImportFilesAction(self.model, f4))
        self.assertTrue(self.model.get_file_by_path(f1).name == 'file0_1.txt')
        self.assertTrue(self.model.get_file_by_path(f2).name == 'file0_2.txt')
        self.assertTrue(self.model.get_file_by_path(f3).name == 'file0_3.txt')
        self.assertTrue(self.model.get_file_by_path(f4).name == 'file1_1.txt')
        #print self.model.get_file_by_path(f1).folder, self.model.get_file_by_path(f2).folder, self.model.get_file_by_path(f3).folder
        self.assertTrue(self.model.get_file_by_path(f1).folder == self.model.get_file_by_path(f2).folder)
        self.assertTrue(self.model.get_file_by_path(f2).folder == self.model.get_file_by_path(f3.folder))
        self.assertTrue(self.model.get_file_by_path(f1).folder != self.model.get_file_by_path(f4.folder))
    ############################################################################    
    #def test_insertFolder(self):
        
        
        
    ############################################################################
    def test_deleteFile(self):
        it(ImportFilesAction(self.model, '/tmp/test/file0_1.txt'))
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        it(DeleteFilesAction(self.model, '/tmp/test/file0_1.txt'))
        self.assertTrue(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
            
   
    
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
    
    
    
    