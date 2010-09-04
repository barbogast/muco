# -*- coding: utf-8 -*-

import sqlite3
import apsw
import os
import hashlib

from action import Action

def _one(cursor):
    res = cursor.fetchone()
    if res is None:
        return None
    else:
        return res[0]
    

class DB_File(object):
    ATTRIBUTES = frozenset(['id_', 'folder_id', 'name', 'hash_', 'hash_is_wrong'])

    def __init__(self, kwargs):
        if kwargs is None:
            self._is_none = True
        else:
            self._is_none = False
            for a in self.ATTRIBUTES:
                try:
                    setattr(self, a, kwargs[a])
                except KeyError:
                    raise AttributeError('Keyword arg "%s" is required'%a)

    def __str__(self):
        if self.is_none():
            details = 'None'
        else:
            details = '%s [id=%s, folder_id=%s, hash=%s, is_hash_wrong=%s]'%(
                self.name, self.id_, self.folder_id, self.hash_, self.hash_is_wrong)
        return 'DB_File: '+details
        
    def is_none(self):
        return self._is_none
    
    
class Model(object):
    """
    Optimierungen:
     * wenn ich einen Ordner finde, der noch nicht in der DB ist, muss ich bei 
       allen untergeordneten Ordnern/Dateien nicht mehr pruefen, ob sie schon in 
       der DB sind.
     * Wenn ich dabei bin, einen Ordner zu pruefen und finde diesen Ordner in der
       DB, kann ich alle untergeordneten elemente dieses ordners auf einem 
       aus der DB selektieren und pruefen.
    """
    
    conn = None
    
    def __init__(self, logger=None):
        if logger is None:
            logger = lambda _: None
        self.log = logger
        
    def set_connection(self, conn):
        self.conn = conn
        return self
      
    def commit(self):
        self.conn.commit()
        
    def commit_and_close(self):
        self.conn.commit()
        self.conn.close()
        
    def rollback(self):
        self.conn.rollback()
        
    def make_schema(self, path=None):
        if not path:
            path = 'schema.sql'
        sql = open(path).read()
        self.conn.cursor().executescript(sql)
              
    
    def get_file(self, path, folder_id=None):
        self.log('get_file: path=%s, folder_id=%s'%(path, folder_id))
        
        folder, filename = os.path.split(path)
        
        # select parent folder
        if folder_id is None:
            
            folder_id = self.get_folder(folder)
            if folder_id is None:
                return DB_File(None)
        
        # select file
        c = self.conn.cursor()
        c.execute("""select id, folder_id, name, hash, hash_is_wrong from file 
                     where name = ? and folder_id = ?""", (filename, folder_id))
        row = c.fetchone()
        if row is not None:
            return DB_File(dict(id_=row[0], 
                           folder_id=row[1],
                           name=row[2],
                           hash_=row[3],
                           hash_is_wrong=True if row[4] else False))
        
        return DB_File(None)
    
    
    def insert_file(self, path, folder_id=None, newHashSum=None):
        self.log('insert_file: path=%s, folder_id=%s'%(path, folder_id))
        
        if os.path.islink(path):
            # Ingnore links
            return DB_File(None)
        
        folder, filename = os.path.split(path)
                
        # select parent folder
        if folder_id is None:
            folder_id = self.folder(folder, False)
            if folder_id is None:
                return DB_File(None)
        
        c = self.conn.cursor()
        c.execute("insert into file (name, folder_id, hash) values (?, ?, ?)",
                  (filename, folder_id, newHashSum))
        return DB_File(dict(id_=c.lastrowid, 
                       folder_id=folder_id,
                       name=filename,
                       hash_=newHashSum,
                       hash_is_wrong=False))
            
    
    def get_folder(self, path, parent_folder_id=None):
        self.log('get_folder ' + path)
        if not os.path.isdir(path) or os.path.islink(path):
            self.log('Model.folder(): path %s: isdir(%s), islink(%s)' % (path, os.path.isdir(path) , os.path.islink(path)))
            return None
        
        c = self.conn.cursor()
        path = os.path.normpath(path)
        
        is_mount_point = os.path.ismount(path)
        if is_mount_point:
            c.execute("select id from folder where is_mount_point = 1 and name = ?",
                       (path, ))
            folder_id = _one(c)
            if folder_id is not None:
                return folder_id
        else:
            if parent_folder_id is None:
                c.execute("select id from folder where full_path = ?", (path,))
            else:
                root, folder = os.path.split(path)
                c.execute("select id from folder where name = ? and parent_folder_id = ?",
                          (folder, parent_folder_id))
            res = c.fetchone()
            if res is not None:
                return res[0]
            
        return None      
        
    
    def insert_folder(self, path, parent_folder_id=None):
        """ 
        Try to get the parent folder. If it is not in the DB, insert it by 
        calling this method. After the parent folder was inserted (or selected), 
        insert this folder with the received ID.
        This way the folders will be recursivly selected from top to bottom 
        until one is found or the root is reached.
        Then the folders will be inserted from bottom to top.
        """
        self.log('Folder ' + path)
        if not os.path.isdir(path) or os.path.islink(path):
            self.log('Model.folder(): path %s: isdir(%s), islink(%s)' % (path, os.path.isdir(path) , os.path.islink(path)))
            return None
        
        c = self.conn.cursor()
        root, folder = os.path.split(path)
        path = os.path.normpath(path)
        
        is_mount_point = os.path.ismount(path)
        if parent_folder_id is None and not is_mount_point:
            parent_folder_id = self.get_folder(root)
            if parent_folder_id is None:
                parent_folder_id = self.insert_folder(root)
        
        self.log('insert ' + path)
        c.execute("""insert into folder 
                     (name, full_path, parent_folder_id, is_mount_point)
                     values (?, ?, ?, ?)""", 
                    (folder, path, parent_folder_id, is_mount_point))
        return c.lastrowid
    
    
    def delete_file(self, f):
        c = self.conn.cursor()
        c.execute("delete from file where folder_id = ? and id = ?", (f.folder_id, f.id_))
        
    def get_child_folders(self, parent_folder_id):
        c = self.conn.cursor()
        c.execute("select id, full_path from folder where parent_folder_id = ?", (parent_folder_id, ))
        return c.fetchall()
    
    def get_files(self, folder_id):
        c = self.conn.cursor()
        c.execute("select id, name, hash, hash_is_wrong from file where folder_id = ?", (folder_id, ))
        files = []
        for row in c.fetchall():
            f = DB_File(dict(id_=row[0],
                             folder_id=folder_id,
                             name=row[1],
                             hash_=row[2],
                             hash_is_wrong=True if row[3] else False
                             ))
            files.append(f)
        return files
    
    def set_hash_is_wrong(self, f, is_wrong):
        c = self.conn.cursor()
        c.execute("update file set hash_is_wrong = ? where id = ?", (is_wrong, f.id_))
                
    def delete_folder(self, folder_id):
        """ Will delete the files in this folder, then the foldern itself.
        Attention: Make sure, the given folder doesnt have any subfolders!"""
        c = self.conn.cursor()
        c.execute("delete from file where folder_id = ?", (folder_id, ))
        c.execute("delete from folder where id = ?", (folder_id, ))
    
    def get_stats(self):
        c = self.conn.cursor()
        c.execute("""select count(*) from file""")
        noFiles = _one(c)
        c.execute(""" select count(*) from folder""")
        noFolders = _one(c)
        return {'files': noFiles, 'folders': noFolders}
    
    
class Hasher(object):
    CHUNK_SIZE = 1024*1024
    _hash = None
    
    def read_hash(self, filePath):
        size = os.path.getsize(filePath)
        print 'hash', filePath, size
        pos = 0
        h = hashlib.sha1()
        with open(filePath, 'r') as f:
            while True:
                d = f.read(self.CHUNK_SIZE)
                if not d: break
                h.update(d)
                pos += self.CHUNK_SIZE
                if pos > size:
                    pos = size
                yield pos*100/size, 'Hashing '+filePath
                
        self._hash = h.hexdigest()
         
    def get_hash(self):
        return self._hash
    
    
class ImportFilesAction(Action):
    def __init__(self, path):
        self.path = path
        
    def get_name(self):
        return 'Dateien importieren: %s'%self.path
    
    def import_file(self, path, folder_id):
        f = self.model.get_file(path, folder_id)
        if not f.is_none():
            return

        h = Hasher()
        for info in h.read_hash(path):
            yield info
        f = self.model.insert_file(path, folder_id=folder_id, newHashSum=h.get_hash())
        if f.is_none():
            raise Exception('Import failed: %s (%s)' % (path, folder_id))
                
 
    def import_folder(self, path, parent_folder_id):
        yield('?', path)
        folder_id = self.model.get_folder(path, parent_folder_id)
        if folder_id is None:
            folder_id = self.model.insert_folder(path, parent_folder_id)
        if folder_id is None:
            raise Exception('Import failed: %s (%s)' % (self.path, parent_folder_id))
        
        for el in os.listdir(path):
            el = os.path.join(path, el)
            if os.path.islink(el):
                continue
            if os.path.isdir(el):
                for info in self.import_folder(el, folder_id):
                    yield info

            elif os.path.isfile(el):
                for info in self.import_file(el, folder_id):
                    yield info
    
    def run_action(self):
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            folder_path = os.path.dirname(self.path)
            folder_id = self.model.get_folder(folder_path)
            if folder_id is None:
                folder_id = self.model.insert_folder(folder_path)
                
            for info in self.import_file(self.path, folder_id):
                yield info
            yield (100, self.path)
        else:
            for info in self.import_folder(self.path, None):
                yield info
        self.model.commit_and_close()
        yield('100', '')
    
        
class DeleteFilesAction(Action):
    def __init__(self, path):
        self.path = path
        
    def get_name(self):
        return 'Dateien entfernen: %s'%self.path
    
    def delete_folder(self, folder_id, path):
        rows = self.model.get_child_folders(folder_id)
        for child_folder_id, child_full_path in rows:
            for info in self.delete_folder(child_folder_id, child_full_path):
                yield info
            
        self.model.delete_folder(folder_id)
    
    def run_action(self):
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            f = self.model.get_file(self.path)
            if f.folder_id is None or f.id_ is None:
                raise Exception('delete of file failed: %s' % (self.path))
            self.model.delete_file(f)
            yield (100, self.path)
        else:
            yield ('?', self.path)
            folder_id = self.model.get_folder(self.path)
            for info in self.delete_folder(folder_id, self.path):
                yield info
        self.model.commit_and_close()
        yield('100', '')
    
            
class CheckFilesAction(Action):
    def __init__(self, path):
        self.path = path
        
    def get_name(self):
        return u'Dateien prüfen: %s'%self.path

    def check_file(self, filePath, f):
        h = Hasher()
        for info in h.read_hash(filePath):
            yield info
        if f.hash_ != h.get_hash():
            self.model.set_hash_is_wrong(f, True)
        else:
            if f.hash_is_wrong:
                self.model.set_hash_is_wrong(f, False)
        
    
    def check_folder(self, folder_id, full_path):
        child_folder_ids = self.model.get_child_folders(folder_id)
        if child_folder_ids:
            for child_id, child_path in child_folder_ids:
                yield ('?', child_path)
                for info in self.check_folder(child_id, child_path):
                    yield info
                
        for f in self.model.get_files(folder_id):
            filePath = os.path.join(full_path, f.name)
            for info in self.check_file(filePath, f):
                yield info
    
    def run_action(self):
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            f = self.model.get_file(self.path)
            if f.is_none():
                return
            for info in self.check_file(self.path, f):
                yield info
        else:
            folder_id = self.model.get_folder(self.path)
            if folder_id is None:
                return
            for info in self.check_folder(folder_id, self.path):
                yield info
        self.model.commit_and_close()
         
                
                
dbPath = 'db01.sqlite'

def get_connection(dbPath=dbPath):
    return sqlite3.connect(dbPath)

def get_connection(dbPath=dbPath):
    return sqlite3.connect(dbPath)

def printer(msg): print msg

if __name__ == '__main__':
    import time
    start = time.time()
    def printer(msg): print msg
    databasePresent = os.path.isfile(dbPath)
    m = Model(logger=None)
    m.set_connection(get_connection(dbPath))
    if not databasePresent:
        m.make_schema()
    
    m.commit_and_close()
    
    print 'Duration: ', time.time()-start