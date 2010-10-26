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
        
    def test_insertFolderFailNotMountWithoutParent2(self):
        fo1 = self.model.insert_folder('/', None, True)
        self.failUnlessRaises(Exception, self.model.insert_folder, '/aaa/bbb', None, False)
        
    def test_insertFolderFailMountWithParent(self):
        class Mock(object): id_=5
        self.failUnlessRaises(Exception, self.model.insert_folder, '/', Mock(), True)
            
    def test_insertFolderFailWhenInsertedTwice(self):
        self.model.insert_folder('/aaa', None, True)
        self.failUnlessRaises(Exception, self.model.insert_folder, '/aaa', None, True)
        
    ###################### Model.get_folder_by_path() ###############################
    def test_getFolderByPath_withParent(self): 
        fo1 = self.model.insert_folder('/', None, True)
        self.model.insert_folder('/aaa', fo1, False)
        fo2 = self.model.get_folder_by_path('/aaa', fo1, False)
        self.assertFalse(fo2.is_none())
        self.assertEqual(fo2.parent_folder, fo1)
        self.assertEqual(fo2.parent_folder_id, fo1.id_)
        self.assertEqual(fo2.hash_, None)
        self.assertEqual(fo2.is_ok, True)
        self.assertEqual(fo2.name, 'aaa')
        self.assertEqual(fo2.full_path, '/aaa')
        self.assertEqual(fo2.is_mount_point, False)
        self.assertEqual(fo1.child_folders[fo2.id_], fo2)
        
    def test_getFolderByPath_withoutParent(self):
        fo1 = self.model.insert_folder('/', None, True)
        self.model.insert_folder('/aaa', fo1, False)
        fo2 = self.model.get_folder_by_path('/aaa', is_mount_point=False)
        self.assertFalse(fo2.is_none())
        #self.assertEqual(fo2.parent_folder, fo1)
        ##Attention: should a global folder cache be implemented?
        self.assertEqual(fo2.parent_folder_id, fo1.id_)
        self.assertEqual(fo2.hash_, None)
        self.assertEqual(fo2.is_ok, True)
        self.assertEqual(fo2.name, 'aaa')
        self.assertEqual(fo2.full_path, '/aaa')
        self.assertEqual(fo2.is_mount_point, False)
    
    def test_getFolderByPath_isMount(self):
        self.model.insert_folder('/', None, True)
        fo1 = self.model.get_folder_by_path('/', is_mount_point=True)
        self.assertFalse(fo1.is_none())
        self.assertTrue(fo1.parent_folder.is_none())
        self.assertEqual(fo1.parent_folder_id, None)
        self.assertEqual(fo1.hash_, None)
        self.assertEqual(fo1.is_ok, True)
        self.assertEqual(fo1.name, '/')
        self.assertEqual(fo1.full_path, '/')
        self.assertEqual(fo1.is_mount_point, True)
        
    def test_getFolderByPath_isMount_noInfo(self):
        self.model.insert_folder('/', None, True)
        fo1 = self.model.get_folder_by_path('/')
        self.assertFalse(fo1.is_none())
        self.assertTrue(fo1.parent_folder.is_none())
        self.assertEqual(fo1.parent_folder_id, None)
        self.assertEqual(fo1.hash_, None)
        self.assertEqual(fo1.is_ok, True)
        self.assertEqual(fo1.name, '/')
        self.assertEqual(fo1.full_path, '/')
        self.assertEqual(fo1.is_mount_point, True)
        
    def test_getFolderByPath_fail_isMount_withParent(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/aaa', fo1, True)
        self.failUnlessRaises(Exception, self.model.get_folder_by_path, '/aaa', fo2, True)
        
    def test_getFolderByPath_fail_existsNot(self):
        fo1 = self.model.get_folder_by_path('/')
        self.assertTrue(fo1.is_none())
        
    def test_getFolderByPath_fail_withWrongParent(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/aaa', fo1, False)
        fo3 = self.model.insert_folder('/aaa/bbb', fo2, False)
        fo4 = self.model.get_folder_by_path('/aaa/bbb', fo1)
        self.assertTrue(fo4.is_none())
    
    
    ###################### Model.get_folder_by_id() ############################
    def test_getFolderById(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/aaa', fo1, False)
        fo3 = self.model.insert_folder('/aaa/bbb', fo2, False)
        fo4 = self.model.get_folder_by_id(fo3.id_)
        self.assertFalse(fo4.is_none())
        self.assertTrue(fo4.parent_folder.is_none())
        self.assertEqual(fo4.parent_folder_id, fo2.id_)
        self.assertEqual(fo4.hash_, None)
        self.assertEqual(fo4.is_ok, True)
        self.assertEqual(fo4.name, 'bbb')
        self.assertEqual(fo4.full_path, '/aaa/bbb')
        self.assertEqual(fo4.is_mount_point, False)
        
    def test_getFolderById_fail_folderIsMissing(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/aaa', fo1, False)
        fo3 = self.model.get_folder_by_id(234234)
        
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
    
    ###################### Model.delete_folder() ###############################
    def test_delete_folder(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2a = self.model.insert_folder('/aaa', fo1, False)
        self.model.insert_file('/aaa/fff1.txt', fo2a, 100)
        self.model.insert_file('/aaa/fff2.txt', fo2a, 200)
        
        fo2b = self.model.insert_folder('/bbb', fo1, False)
        self.model.insert_folder('/bbb/ccc1', fo2b, False)
        self.model.insert_folder('/bbb/ccc2', fo2b, False)
        self.model.insert_file('/bbb/fff1.txt', fo2b, 100)
        self.model.insert_file('/bbb/fff2.txt', fo2b, 200)
        
        self.model.delete_folder(fo2a)
        self.assertTrue(self.model.get_folder_by_path('/aaa').is_none())
        self.assertTrue(self.model.get_file_by_path('/aaa/fff1.txt').is_none())
        self.assertTrue(self.model.get_file_by_path('/aaa/fff2.txt').is_none())
        
        self.assertFalse(self.model.get_folder_by_path('/bbb/ccc1').is_none())
        self.assertFalse(self.model.get_folder_by_path('/bbb/ccc2').is_none())
        self.assertFalse(self.model.get_file_by_path('/bbb/fff1.txt').is_none())
        self.assertFalse(self.model.get_file_by_path('/bbb/fff2.txt').is_none())
        
    def test_delete_folder_fail_existsNot(self):
        class Mock(): 
            id_=5
            child_folders = {}
            child_files = {}
            def set_to_none(self): pass
        self.model.delete_folder(Mock())
    
    def test_delete_folder_fail_hasChildFolders(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/aaa', fo1, False)
        self.failUnlessRaises(Exception, self.model.delete_folder, fo1)
        
    ###################### Model.delete_file() #################################
    def test_delete_file(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2 = self.model.insert_folder('/aaa', fo1, False)
        fi1 = self.model.insert_file('/aaa/fff1.txt', fo2, 100)
        fi2 = self.model.insert_file('/aaa/fff2.txt', fo2, 200)
        self.assertTrue(len(fo2.child_files)==2)
        self.model.delete_file(fi1)
        self.assertTrue(self.model.get_file_by_path('/aaa/fff1.txt').is_none())
        self.assertFalse(self.model.get_file_by_path('/aaa/fff2.txt').is_none())
        self.assertTrue(len(fo2.child_files)==1 and fi2.id_ in fo2.child_files)
        
    ########### Model.fill_child_folders() Model.fill_child_files()#############
    def test_fillChilds(self):
        fo1 = self.model.insert_folder('/', None, True)
        fo2a = self.model.insert_folder('/aaa', fo1, False)
        fo2b = self.model.insert_folder('/bbb', fo1, False)
        fi2a = self.model.insert_file('/aaa.txt', fo1, 1234)
        fi2b = self.model.insert_file('/bbb.txt', fo1, 1234)
        self.assertEqual(sorted(fo1.child_folders.values()),
                         sorted((fo2a, fo2b)))
        self.assertEqual(sorted(fo1.child_files.values()),
                         sorted((fi2a, fi2b)))
        
        fox = self.model.get_folder_by_path('/')
        self.model.fill_child_folders(fox)
        self.model.fill_child_files(fox)
        self.assertEqual(sorted((fo.name for fo in fox.child_folders.values())),
                         sorted(('aaa', 'bbb')))
        self.assertEqual(sorted((fi.name for fi in fox.child_files.values())),
                         sorted(('aaa.txt', 'bbb.txt')))
        
    ###################### Model.set_file_hash_is_wrong() ######################
    def test_setFielHashIsWrong(self):
        fo1 = self.model.insert_folder('/', None, True)
        fi2a = self.model.insert_file('/aaa.txt', fo1, 1234)
        fi2b = self.model.insert_file('/bbb.txt', fo1, 1234)
        self.model.set_file_hash_is_wrong(fi2a, True)
        self.model.set_file_hash_is_wrong(fi2b, False)
        self.assertTrue(fi2a.hash_is_wrong)
        self.assertFalse(fi2b.hash_is_wrong)
        stmt = "select hash_is_wrong from file where id = ?"
        res = self.model.get_connection().execute(stmt, (fi2a.id_,))
        self.assertEqual(list(res)[0], (1,))
        res = self.model.get_connection().execute(stmt, (fi2b.id_,))
        self.assertEqual(list(res)[0], (0,))
        
        
    ###################### Model.set_file_hash() ###############################
    def test_setFileHash(self):
        fo1 = self.model.insert_folder('/', None, True)
        fi2a = self.model.insert_file('/aaa.txt', fo1, 1234)
        fi2b = self.model.insert_file('/bbb.txt', fo1, 1234)
        self.model.set_file_hash(fi2a, 'xxx')
        self.model.set_file_hash(fi2b, 'yyy')
        self.assertEqual(fi2a.hash_, 'xxx')
        self.assertEqual(fi2b.hash_, 'yyy')
        stmt = "select hash from file where id = ?"
        res = self.model.get_connection().execute(stmt, (fi2a.id_,))
        self.assertEqual(list(res)[0], ('xxx',))
        res = self.model.get_connection().execute(stmt, (fi2b.id_,))
        self.assertEqual(list(res)[0], ('yyy',))
        
    ############# Model.set_folder_hash() Model.set_folder_is_ok() #############
    def test_setFolderIsOk(self):
        fo1 = self.model.insert_folder('/', None, True)
        changed = self.model.set_folder_hash(fo1, 'xxx')
        self.assertTrue(changed)
        changed = self.model.set_folder_hash(fo1, 'xxx')
        self.assertFalse(changed)
        changed = self.model.set_folder_is_ok(fo1, False)
        self.assertTrue(changed)
        self.assertFalse(fo1.is_ok)
        changed = self.model.set_folder_is_ok(fo1, False)
        self.assertFalse(changed)
        
        stmt = "select is_ok, hash from folder where id = ?"
        res = self.model.get_connection().execute(stmt, (fo1.id_,))
        self.assertEqual(list(res)[0], (0, None))
        
    ######################  #############################

    
    
def it(o):
    for i in o.run_action():pass
        
class TestFSActions(ut.TestCase):
    files = {
        'file0_1.txt': 'testtextfile0_1',
        'file0_2.txt': 'testtextfile0_2',
        'file0_3.txt': 'testtextfile0_3',
        'folder1': {
            'file1_1.txt': 'testtextfile1_1',
            'file1_2.txt': 'testtextfile1_2',
            'file1_3.txt': 'testtextfile1_3',
        },
        'folder2': {
            'file2_1.txt': 'testtextfile2_1',
            'file2_2.txt': 'testtextfile2_2',
            'file2_3.txt': 'testtextfile2_3',
        },
        'folder3': {},
        'folder4': {
            'file4_1.txt': 'testtextfile4_1',
            'file4_2.txt': 'testtextfile4_2',
            'file4_3.txt': 'testtextfile4_3',
            'folder4_4': {
                'file4_4_1.txt': 'testtextfile4_4_1',
                'file4_4_2.txt': 'testtextfile4_4_2',
                'file4_4_3.txt': 'testtextfile4_4_3',
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
        
    def tearDown(self):
        self.tf.removeAll()
    
    #########################ImportFilesAction files############################
    def test_importFile(self):
        it(ImportFilesAction(self.model, '/tmp/test/file0_1.txt'))
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        
    def test_importFile_delete_reinsert(self):
        f = '/tmp/test/file0_1.txt'
        it(ImportFilesAction(self.model, f))
        self.assertFalse(self.model.get_file_by_path(f).is_none())
        it(DeleteFilesAction(self.model, f))
        self.assertTrue(self.model.get_file_by_path(f).is_none())
        it(ImportFilesAction(self.model, f))
        self.assertFalse(self.model.get_file_by_path(f).is_none())
        
    def test_importFileFromDifferentFolders(self):
        it(ImportFilesAction(self.model, '/tmp/test/file0_1.txt'))
        self.assertFalse(self.model.get_file_by_path('/tmp/test/file0_1.txt').is_none())
        
        it(ImportFilesAction(self.model, '/tmp/test/folder4/file4_1.txt'))
        self.assertFalse(self.model.get_file_by_path('/tmp/test/folder4/file4_1.txt').is_none())
        
    def test_importMultipleFiles(self):
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
        self.assertTrue(self.model.get_file_by_path(f1).folder.id_ == self.model.get_file_by_path(f2).folder.id_)
        self.assertTrue(self.model.get_file_by_path(f2).folder.id_ == self.model.get_file_by_path(f3).folder.id_)
        self.assertTrue(self.model.get_file_by_path(f1).folder.id_ != self.model.get_file_by_path(f4).folder.id_)
        
    def test_importFiles_Hash(self):
        filepath = '/tmp/test/file0_1.txt'
        it(ImportFilesAction(self.model, filepath))
        hs = hashlib.sha1()
        f = open(filepath)
        hs.update(f.read())
        f.close()
        hs = hs.hexdigest()
        self.assertEqual(self.model.get_file_by_path(filepath).hash_, hs)
        
    ###########################ImportFilesAction folders########################    
    def test_importFolder_simple(self):
        path = '/tmp/test/folder1'
        it(ImportFilesAction(self.model, path))
        
        fo = self.model.get_folder_by_path(path)
        self.assertFalse(fo.is_none())
        self.model.fill_child_files(fo)
        hs = hashlib.sha1()
        childNames = []
        for child_id, child_fi in fo.child_files.iteritems():
            self.assertEqual(child_fi.id_, child_id)
            childNames.append(child_fi.name)
            hs.update(child_fi.hash_)
        self.assertEqual(hs.hexdigest(), fo.hash_)
        self.assertEqual(sorted(childNames), sorted(('file1_1.txt', 'file1_2.txt', 'file1_3.txt')))
        
        
    def test_importFolder_recursive(self):
        path = '/tmp/test/folder4'
        it(ImportFilesAction(self.model, path))
        fo1 = self.model.get_folder_by_path(path)
        self.model.fill_child_files(fo1)
        self.model.fill_child_folders(fo1)
        
        hs1 = hashlib.sha1()
        childFileNames1 = []
        for child_id, child_fi in fo1.child_files.iteritems():
            self.assertEqual(child_fi.id_, child_id)
            childFileNames1.append(child_fi.name)
            hs1.update(child_fi.hash_)
        self.assertEqual(sorted(childFileNames1), sorted(('file4_1.txt', 'file4_2.txt', 'file4_3.txt')))
        
        self.assertEqual(fo1.child_folders.values()[0].full_path, '/tmp/test/folder4/folder4_4')
        fo2 = self.model.get_folder_by_path('/tmp/test/folder4/folder4_4')
        self.assertEqual(fo1.child_folders.values()[0].id_, fo2.id_)
        
        self.model.fill_child_files(fo2)
        hs2 = hashlib.sha1()
        childFileNames2 = []
        for child_id, child_fi in fo2.child_files.iteritems():
            self.assertEqual(child_fi.id_, child_id)
            childFileNames2.append(child_fi.name)
            hs2.update(child_fi.hash_)
        self.assertEqual(sorted(childFileNames2), sorted(('file4_4_1.txt', 'file4_4_2.txt', 'file4_4_3.txt')))
        print hs1.hexdigest(), fo2.hash_
        self.assertEqual(hs2.hexdigest(), fo2.hash_)
        
        hs1.update(fo2.hash_)
        self.assertEqual(hs1.hexdigest(), fo1.hash_)
        
        
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
    
    
    
    