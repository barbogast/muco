# *-* coding: utf-8 -*-

import unittest as ut
import sqlite3
import os

import sys,pprint
pprint.pprint(sys.path)
from muco.model import Model




class SqliteForeignKeys(ut.TestCase):
    TEST_DB_PATH = os.path.join(os.path.realpath('./testdata'), 'test.sqlite')
    
    def setUp(self):
        print os.listdir('.')
        self.conn = sqlite3.connect(self.TEST_DB_PATH)
        self.model = Model()
        self.model.set_connection(self.conn)
        self.model.make_schema()

    def tearDown(self):
        self.conn.close()
        os.remove(self.TEST_DB_PATH)
        
    def test_select(self):
        pass
        
    def test_insert(self):
        pass
    
    def test_update(self):
        pass

    def test_delete(self):
        pass
    
    
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
    
    
    
    