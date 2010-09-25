# -*- coding: utf-8 -*-

import sqlite3
import apsw
import os
import hashlib
import time

from action import Action

def _one(cursor):
    res = cursor.fetchone()
    if res is None:
        return None
    else:
        return res[0]
    
class DB_Object(object):
    ATTRIBUTES = frozenset()
    RELATIONS = frozenset()
    NAME = ''
    
    def __init__(self, **kwargs):
        if not kwargs:
            self._is_none = True
        else:
            self._is_none = False
            for a in list(self.ATTRIBUTES) + list(self.RELATIONS):
                try:
                    setattr(self, a, kwargs.pop(a))
                except KeyError:
                    raise AttributeError('Keyword arg "%s" is required'%a)
            if kwargs:
                raise ValueError('Unknown keyword arg(s): %s'%kwargs)

    def __str__(self):
        if self.is_none():
            details = 'None'
        else:
            cols = ['%s=%s'%(a, getattr(self, a)) for a in sorted(self.ATTRIBUTES)]
            details = '%s %s [%s]'%(self.__class__.__name__, self.NAME, ', '.join(cols))
        return details
        
    def is_none(self):
        return self._is_none

    
class DB_File(DB_Object):
    ATTRIBUTES = frozenset(['id_', 'name', 'hash_', 'hash_is_wrong'])
    RELATIONS = frozenset(['folder'])
    hash_is_wrong=None #TODO
    def __init__(self, **kwargs):
        super(DB_File, self).__init__(**kwargs)
        if self.hash_is_wrong is None or self.hash_is_wrong is 0:
            self.hash_is_wrong = False

            
        

class DB_Folder(DB_Object):
    ATTRIBUTES = frozenset(['id_', 'name', 'full_path', 'is_mount_point', 
                            'hash_', 'is_ok', 'parent_folder_id'])
    RELATIONS = frozenset(['parent_folder'])
    full_path = None #TODO
    is_ok=None
    def __init__(self, **kwargs):
        super(DB_Folder, self).__init__(**kwargs)
        if self.full_path and not self.name:
            self.name = os.path.split(os.path.normpath(self.full_path))[1]
        if self.is_ok is None or self.is_ok is 0:
            self.is_ok = False
        
        
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
              
    
    def get_file_by_path(self, path, fo=DB_Folder()):
        self.log('get_file: path=%s, folder_id=%s'%(path, fo))
        
        folder, filename = os.path.split(path)
        
        # select parent folder
        if fo.is_none():
            fo = self.get_folder_by_path(folder)
            if fo.is_none():
                return DB_File()
        
        # select file
        c = self.conn.cursor()
        c.execute("""select id, folder_id, name, hash, hash_is_wrong from file 
                     where name = ? and folder_id = ?""", (filename, fo.id_))
        row = c.fetchone()
        if row is not None:
            return DB_File(id_=row[0], folder=fo, name=row[2], hash_=row[3],
                           hash_is_wrong=row[4])
        
        return DB_File()
    
    
    def insert_file(self, path, fo=DB_Folder(), newHashSum=None):
        self.log('insert_file: path=%s, folder_id=%s'%(path, fo))
        
        if os.path.islink(path):
            # Ingnore links
            return DB_File()
        
        folder, filename = os.path.split(path)
                
        # select parent folder
        ## TODO: is this path ever used/tested???
        if fo.is_none():
            fo = self.get_folder_by_path(folder, False)
            if fo.is_none():
                return DB_File()
        
        c = self.conn.cursor()
        c.execute("insert into file (name, folder_id, hash) values (?, ?, ?)",
                  (filename, fo.id_, newHashSum))
        return DB_File(id_=c.lastrowid, 
                       folder=fo,
                       name=filename,
                       hash_=newHashSum,
                       hash_is_wrong=False)
            
    
    def get_folder_by_path(self, path, parent_fo=DB_Folder()):
        self.log('get_folder ' + path)
        if not os.path.isdir(path) or os.path.islink(path):
            self.log('Model.folder(): path %s: isdir(%s), islink(%s)' % (path, os.path.isdir(path) , os.path.islink(path)))
            return DB_Folder()
        
        c = self.conn.cursor()
        path = os.path.normpath(path)
        
        is_mount_point = os.path.ismount(path)
        if is_mount_point:
            where = "is_mount_point = 1 and full_path = ?"
            args = (path, )
        else:
            if parent_fo.is_none():
                where = "full_path = ?"
                args = (path,)
            else:
                root, folder = os.path.split(path)
                where = "name = ? and parent_folder_id = ?"
                args = (folder, parent_fo.id_)
            
        stmt = "select id, hash, is_ok, parent_folder_id from folder where " + where
        res = list(self.conn.cursor().execute(stmt, args))
        if not res:
            return DB_Folder()
        d = dict(zip(['id_', 'hash_', 'is_ok', 'parent_folder_id'], res[0]))
        d.update(name='', 
                 full_path=path, 
                 is_mount_point=is_mount_point,
                 parent_folder=parent_fo)
        return DB_Folder(**d)
            
        
    def get_folder_by_id(self, folder_id):    
        res = list(self.conn.cursor().execute(""" 
            select id, name, full_path, is_mount_point, hash, is_ok, parent_folder_id from folder
            where id = ?""", (folder_id, )))
        d = dict(zip(('id_', 'name', 'full_path', 'is_mount_point', 'hash_', 'is_ok', 'parent_folder_id'), res[0]))
        d.update(parent_folder=DB_Folder())
        return DB_Folder(**d)
        
    
    def insert_folder(self, path, parent_fo=DB_Folder()):
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
        path = os.path.normpath(path)
        root, folder = os.path.split(path)
        
        is_mount_point = os.path.ismount(path)
        if parent_fo.is_none() and not is_mount_point:
            parent_fo = self.get_folder_by_path(root)
            if parent_fo.is_none():
                parent_fo = self.insert_folder(root)
            parent_folder_id = parent_fo.id_
        else:
            parent_folder_id = None
        
        self.log('insert ' + path)
        c.execute("""insert into folder 
                     (name, full_path, parent_folder_id, is_mount_point)
                     values (?, ?, ?, ?)""", 
                    (folder, path, parent_folder_id, is_mount_point))
        return DB_Folder(id_=c.lastrowid,
                         name=folder,
                         full_path=path,
                         parent_folder=parent_fo,
                         parent_folder_id=parent_folder_id,
                         is_mount_point=is_mount_point,
                         hash_=None,
                         is_ok=False)
    
    
    def delete_file(self, fi):
        c = self.conn.cursor()
        c.execute("delete from file where folder_id = ? and id = ?", (fi.folder.id_, fi.id_))
        
    def get_child_folders(self, parent_fo):
        c = self.conn.cursor()
        c.execute("""select id, name, full_path, is_mount_point, hash, is_ok 
                     from folder where parent_folder_id = ?""", (parent_fo.id_, ))
        folders = []
        for row in c:
            folders.append(DB_Folder(id_=row[0],
                                     name=row[1],
                                     full_path=row[2],
                                     parent_folder=parent_fo,
                                     is_mount_point=row[3],
                                     hash_=row[4],
                                     is_ok=row[5]))
        return folders
    
    def get_files(self, fo):
        c = self.conn.cursor()
        c.execute("select id, name, hash, hash_is_wrong from file where folder_id = ?", (fo.id_, ))
        files = []
        for row in c.fetchall():
            fi = DB_File(id_=row[0], name=row[1], hash_=row[2], hash_is_wrong=row[3], folder=fo)
            files.append(fi)
        return files
    
    def set_file_hash_is_wrong(self, fi, is_wrong):
        if fi.hash_is_wrong is is_wrong:
            return
        c = self.conn.cursor()
        c.execute("update file set hash_is_wrong = ? where id = ?", (is_wrong, fi.id_))
        fi.hash_is_wrong = is_wrong
          
    def set_file_hash(self, fi, hashSum):
        if fi.hash_ == hashSum:
            return
        self.conn.cursor().execute('update file set hash = ? where id = ?',
                                   (hashSum, fi.id_))
        fi.hash_ = hashSum
        
        
    def delete_folder(self, fo):
        """ Will delete the files in this folder, then the foldern itself.
        Attention: Make sure, the given folder doesnt have any subfolders!"""
        c = self.conn.cursor()
        c.execute("delete from file where folder_id = ?", (fo.id_, ))
        c.execute("delete from folder where id = ?", (fo.id_, ))
    
    def set_folder_is_ok(self, fo, isOk):
        """ returns True if is_ok was changed"""
        if fo.is_ok == isOk:
            return False

        #c = self.conn.cursor()
        #if isWrong is None:
            #isWrong = False
            #c.execute("select id from folder where parent_folder_id = ? and hash_is_wrong = 1")
            #if c.fetchall():
                #isWrong = True
            #else:
                #c.execute("select id from file where folder_id = ? and hash_is_wrong = 1")
                #if c.fetchall():
                    #isWrong = True
        
        c.execute("update folder set is_ok = ? where id = ?", (0 if isOk else 1, fo.id_))
        fo.is_ok = isOk
        return True
        
    def set_folder_hash(self, fo, hashSum):
        if fo.hash_ == hashSum:
            return
        self.conn.cursor().execute('update folder set hash = ? where id = ?',
                                   (hashSum, fo.id_))
        fo.hash_ = hashSum
        
        
        
    #def add_to_folder_hash(self)
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
        self._size = os.path.getsize(filePath)
        pos = 0
        h = hashlib.sha1()
        with open(filePath, 'r') as fi:
            while True:
                d = fi.read(self.CHUNK_SIZE)
                if not d: break
                h.update(d)
                pos += self.CHUNK_SIZE
                if pos > self._size:
                    pos = self._size
                yield pos*100/self._size
                
        self._hash = h.hexdigest()
         
    def get_hash(self):
        return self._hash
    
    def get_size(self):
        return self._size
    
    
class ImportFilesAction(Action):
    def __init__(self, path):
        self.path = path
        self._totalSize = 0
        self._noFiles = 0
        self._duration = 0
        
    def get_name(self):
        return 'Dateien importieren: %s'%self.path
    
    def get_stats(self):
        return {
            'totalSize': '%.3f'%(self._totalSize/(1024.*1024.)),
            'duration': int(self._duration),
            'noFiles': self._noFiles
        }
    
    def import_file(self, path, fo):
        fi = self.model.get_file_by_path(path, fo)
        if not fi.is_none():
            return

        h = Hasher()
        for pos in h.read_hash(path):
            yield None, 'Hashing (%s%%) %s'%(pos, path)
        fi = self.model.insert_file(path, fo=fo, newHashSum=h.get_hash())
        self._totalSize += h.get_size()
        self._noFiles += 1
        yield ('%s files imported'%self._noFiles, None)
        if fi.is_none():
            raise Exception('Import failed: %s (%s)' % (path, folder_id))
                
 
    def import_folder(self, path, parent_fo=DB_Folder()):
        yield(None, path)
        fo = self.model.get_folder_by_path(path, parent_fo)
        if fo.is_none():
            fo = self.model.insert_folder(path, parent_fo)
        if fo.is_none():
            raise Exception('Import failed: %s (%s)' % (self.path, parent_fo))
        
        for el in os.listdir(path):
            el = os.path.join(path, el)
            if os.path.islink(el):
                continue
            if os.path.isdir(el):
                for info in self.import_folder(el, fo):
                    yield info

            elif os.path.isfile(el):
                for info in self.import_file(el, fo):
                    yield info
    
    def run_action(self):
        start = time.time()
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            folder_path = os.path.dirname(self.path)
            fo = self.model.get_folder_by_path(folder_path)
            if fo.is_none():
                fo = self.model.insert_folder(folder_path)
                
            for info in self.import_file(self.path, fo):
                yield info
            yield (100, self.path)
        else:
            for info in self.import_folder(self.path, DB_Folder()):
                yield info
        self.model.commit_and_close()
        self._duration = time.time() - start
        s = '%s files total'%self._noFiles
        yield(s, unicode(self.get_stats()))
        
    
        
class DeleteFilesAction(Action):
    def __init__(self, path):
        self.path = path
        self._duration = 0
        
    def get_name(self):
        return 'Dateien entfernen: %s'%self.path
    
    def get_stats(self):
        return {
            'duration': int(self._duration)
        }
    
    def delete_folder(self, fo):
        rows = self.model.get_child_folders(fo)
        for child_fo in rows:
            for info in self.delete_folder(child_fo):
                yield info
        yield('TODO', fo.full_path)
        self.model.delete_folder(fo)
    
    def run_action(self):
        start = time.time()
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            fi = self.model.get_file_by_path(self.path)
            if fi.is_none():
                raise Exception('delete of file failed, file not in db: %s' % (self.path))
            self.model.delete_file(fi)
            yield (None, self.path)
        else:
            yield (None, self.path)
            fo = self.model.get_folder_by_path(self.path)
            for info in self.delete_folder(fo):
                yield info
        self.model.commit_and_close()
        self._duration = time.time() - start
        yield(None, unicode(self.get_stats()))
    
            
class CheckFilesAction(Action):
    def __init__(self, path):
        self.path = path
        self._totalSize = 0
        self._duration = 0
        self._noFiles = 0
        
    def get_name(self):
        return u'Dateien prüfen: %s'%self.path
    
    def get_stats(self):
        return {
            'totalSize': '%.3f'%(self._totalSize/(1024.*1024.)),
            'duration': int(self._duration),
            'noFiles': self._noFiles
        }
    
    def update_parent_folder_is_ok(self, fo):
        """ Will recheck the parent folder of this folder, is the is_ok-values 
        does not match """
        if fo.is_mount_point:
            return
        
        parent_fo = self.model.get_folder_by_id(fo.parent_folder_id)
        if fo.is_ok == parent_fo.is_ok:
            return
        else:
            child_files = self.model.get_files(parent_fo)
            child_folders = self.model.get_child_folders(parent_fo)
            was_changed = self.check_folder_is_ok(parent_fo, child_files, child_folders)
            if was_changed and not parent_fo.is_mount_point:
                parent_parent_folder_id = self.model.get_folder_by_id(parent_fo.parent_folder_id)
                self.update_parent_folder_is_ok(parent_parent_folder_id)
    
    def check_folder_is_ok(self, fo, child_folders, child_files):
        """ Returns False if the folder was not ok """
        for child_fo in child_folders:
            if not child_fo.is_ok:
                was_changed = self.model.set_folder_is_ok(fo, False)
                return was_changed

        for child_fi in child_files:
            if child_fi.hash_is_wrong:
                was_changed = self.model.set_folder_is_ok(fo, False)
                return was_changed
         
        h = hashlib.sha1()
        for child_fo in child_folders:
            h.update(child_fo.hash_)
        for child_fi in child_files:
            h.update(child_fi.hash_)
        hashSum = h.hexdigest()
        
        if not fo.hash_:
            was_changed = self.model.set_folder_hash(fo, hashSum)
            return was_changed
        else:
            was_changed = self.model.set_folder_is_ok(fo, fo.hash_ == hashSum)
            return was_changed
            

    def check_file(self, filePath, fi):
        h = Hasher()
        for pos in h.read_hash(filePath):
            yield None, 'Hashing (%s%%) %s'%(pos, filePath)
        
        if fi.hash_ is None:
            self.model.set_file_hash(fi, h.get_hash())
        else:
            self.model.set_file_hash_is_wrong(fi, fi.hash_ != h.get_hash())
        
        self._totalSize += h.get_size()
        self._noFiles += 1
        yield ('%s files checked'%self._noFiles, None)
    
    def check_folder(self, fo):
        # Check subfolders
        child_folders = self.model.get_child_folders(fo)
        for child_fo in child_folders:
            yield (None, child_fo.full_path)
            for info in self.check_folder(child_fo):
                yield info
        
        # Check files
        child_files = self.model.get_files(fo)
        for fi in child_files:
            filePath = os.path.join(fo.full_path, fi.name)
            for info in self.check_file(filePath, fi):
                yield info
                
        self.check_folder_is_ok(fo, child_folders, child_files)
    
    def run_action(self):
        start = time.time()
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            fi = self.model.get_file_by_path(self.path)
            if fi.is_none():
                return
            for info in self.check_file(self.path, fi):
                yield info
            self.update_parent_folder_is_ok(fi.folder)
        else:
            fo = self.model.get_folder_by_path(self.path)
            if fo.is_none():
                return
            for info in self.check_folder(fo):
                yield info
            self.update_parent_folder_is_ok(fo)
        self.model.commit_and_close()
        self._duration = time.time() - start
        s = '%s files total'%self._noFiles
        yield(s, unicode(self.get_stats()))
                
                
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