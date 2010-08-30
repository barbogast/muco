# *-* coding: utf-8 -*-

import unittest as ut
import sqlite3
import os

import apsw


from muco.model import Model


class SqliteForeignKeys(ut.TestCase):
    TEST_DB_PATH = os.path.join(os.path.realpath('./testdata'), 'test.sqlite')
    
    def setUp(self):
        try: os.remove(self.TEST_DB_PATH) 
        except: pass
        self.conn = apsw.Connection(self.TEST_DB_PATH)
        self.conn.cursor().execute(open('../schema.sql').read())
        cur = self.conn.cursor()
        cur.execute("insert into folder (name) values ('folder1')")
        cur.execute("""insert into file (name, folder_id) values ('file1', 
                            (select id from folder where name = 'folder1'))""")

    def tearDown(self):
        #self.conn.commit()
        self.conn.close()
        os.remove(self.TEST_DB_PATH)
        
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
    
    
class TestModel(ut.TestCase):
    def setUp(self):
        pass
   
    #def
    
     # Dateien in eine neue DB einfügen
    
    
    # Volles Verzeichnis loeschen
    # Leeres Verzeichnis loeschen
    
    # Dateien einfuegen in einem Verzeichnis, das es schon gibt
    # Dateien einfuegen in einem Ortner, dessen unter-unterordner schon in der DB ist
    # Verzeichnis rekursiv einfuegen
    
    
    
    