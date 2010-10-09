# -*- coding: utf-8 -*-

import sqlite3
import os
import hashlib
import time

from action import Action

   
class DB_Object(object):
    ATTRIBUTES = frozenset()
    RELATIONS = frozenset()
    EXTRA_ATTR = frozenset()
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

            for a in self.EXTRA_ATTR:
                if a in kwargs:
                    setattr(self, a, kwargs.pop(a))
                   
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
    ATTRIBUTES = frozenset(['id_', 'name', 'hash_', 'hash_is_wrong', 'filesize'])
    RELATIONS = frozenset(['folder'])
    hash_is_wrong=None #TODO
    def __init__(self, **kwargs):
        super(DB_File, self).__init__(**kwargs)
        if not self.is_none():
            if self.hash_is_wrong is None or self.hash_is_wrong == 0:
                self.hash_is_wrong = False
            else:
                self.hash_is_wrong = True
                
        

class DB_Folder(DB_Object):
    ATTRIBUTES = frozenset(['id_', 'name', 'full_path', 'is_mount_point', 
                            'hash_', 'is_ok', 'parent_folder_id'])
    RELATIONS = frozenset(['parent_folder'])
    
    @property
    def child_files(self):
        if self._is_none:
            raise ValueError('The current object is none: %s'%str(self))
        return self.__child_files
    
    @property
    def child_folders(self):
        if self._is_none:
            raise ValueError('The current object is none: %s'%str(self))
        return self.__child_folders
    
    def __init__(self, **kwargs):
        super(DB_Folder, self).__init__(**kwargs)
        self.__child_files = {}
        self.__child_folders = {}
    
        if not self.is_none():
            if self.full_path and not self.name:
                self.name = os.path.split(os.path.normpath(self.full_path))[1]
                
            self.is_ok = False if self.is_ok is None or self.is_ok == 0 else True
            self.is_mount_point = False if self.is_mount_point is None or self.is_mount_point == 0 else True
        
        
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
        c.execute("""select id, folder_id, name, hash, hash_is_wrong, filesize from file 
                     where name = ? and folder_id = ?""", (filename, fo.id_))
        res = c.fetchone()
        if res:
            fi = DB_File(id_=res[0], folder=fo, name=res[2], hash_=res[3],
                           hash_is_wrong=res[4], filesize=res[5])
            fo.child_files[fi.id_] = fi
            return fi
        
        return DB_File()
    
    
    def insert_file(self, path, fo=DB_Folder(), newHashSum=None, filesize=None):
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
        c.execute("insert into file (name, folder_id, hash, filesize) values (?, ?, ?, ?)",
                  (filename, fo.id_, newHashSum, filesize))
        fi = DB_File(id_=c.lastrowid, 
                     folder=fo,
                     name=filename,
                     hash_=newHashSum,
                     hash_is_wrong=False,
                     filesize=filesize)
        fo.child_files[fi.id_] = fi
        
        return fi
        
    
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
        fo = DB_Folder(**d)
        if not parent_fo.is_none():
            parent_fo.child_folders[fo.id_] = fo
        return fo
            
        
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
            return DB_Folder()
        
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
        
        fo = DB_Folder(id_=c.lastrowid,
                         name=folder,
                         full_path=path,
                         parent_folder=parent_fo,
                         parent_folder_id=parent_folder_id,
                         is_mount_point=is_mount_point,
                         hash_=None,
                         is_ok=True)
        
        if not parent_fo.is_none():
            parent_fo.child_folders[fo.id_] = fo
        return fo

    
    def delete_folder(self, fo):
        """ Will delete the files in this folder, then the foldern itself.
        Attention: Make sure, the given folder doesnt have any subfolders!"""
        c = self.conn.cursor()
        c.execute("delete from file where folder_id = ?", (fo.id_, ))
        c.execute("delete from folder where id = ?", (fo.id_, ))
        fo.child_files.clear()
        fo.child_folders.clear()
        
    def delete_file(self, fi):
        c = self.conn.cursor()
        c.execute("delete from file where folder_id = ? and id = ?", (fi.folder.id_, fi.id_))
        del(fi.folder.child_files[fi.id_])
        
        
    def fill_child_folders(self, parent_fo):
        c = self.conn.cursor()
        c.execute("""select id, name, full_path, is_mount_point, hash, is_ok 
                     from folder where parent_folder_id = ?""", (parent_fo.id_, ))
        for row in c:
            fo = DB_Folder(id_=row[0],
                          name=row[1],
                          full_path=row[2],
                          parent_folder=parent_fo,
                          parent_folder_id=parent_fo.id_,
                          is_mount_point=row[3],
                          hash_=row[4],
                          is_ok=row[5])
            parent_fo.child_folders[fo.id_] = fo
    
    def fill_child_files(self, fo):
        c = self.conn.cursor()
        c.execute("select id, name, hash, hash_is_wrong, filesize from file where folder_id = ?", (fo.id_, ))
        for row in c.fetchall():
            fi = DB_File(id_=row[0], name=row[1], hash_=row[2], hash_is_wrong=row[3], filesize=row[4], folder=fo)
            fo.child_files[fi.id_] = fi
    
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
        
    def set_folder_is_ok(self, fo, isOk):
        """ returns True if is_ok was changed"""
        if fo.is_ok == isOk:
            return False
        c = self.conn.cursor()
        c.execute("update folder set is_ok = ? where id = ?", (1 if isOk else 0, fo.id_))
        fo.is_ok = isOk
        
        if not isOk:
            self.set_folder_hash(fo, None)
            
        return True
        
    def set_folder_hash(self, fo, hashSum):
        """ Returns True if the hash was set """
        if fo.hash_ == hashSum:
            return False
        self.conn.execute('update folder set hash = ? where id = ?',
                          (hashSum, fo.id_))
        fo.hash_ = hashSum
        return True
    
    #def update_folder(self, fo, **kwargs):
        #sets = []
        #for k, v in kwargs.iteritems():
            #if fo[k] != v:
                #break
            #sets.append(k+'=:'+k)
            #fo[k] = v
        #else:
            #return False
        
        #stmt = 'update folder set %s where id = ?'%(','.join(sets))
        #self.conn.execute(stmt, kwargs)                          
        
    def get_stats(self):
        noFiles = list(self.conn.execute("select count(*) from file"))[0][0]
        noFolders = list(self.conn.execute("select count(*) from folder"))[0][0]
        totalSize = list(self.conn.execute("select sum(filesize) from file"))[0][0]
        return {'files': noFiles, 'folders': noFolders, 'totalSize': totalSize}
    
    
class Hasher(object):
    CHUNK_SIZE = 1024*1024
    
    def __init__(self, model, noFiles, totalSize, rehashFolders=True):
        self.noFiles = noFiles
        self.totalSize = totalSize
        self.currentSize = 0
        self.model = model
        self.rehashFolders = rehashFolders
    
    
    def hash_folder(self, fo, inserting=False):
        """ Returns False if the folder was not ok """
        if not fo.child_folders:
            self.model.fill_child_folders(fo)
        if not fo.child_files:
            self.model.fill_child_files(fo)
            
        for child_fo in fo.child_folders.values():
            if not child_fo.is_ok:
                was_changed = self.model.set_folder_is_ok(fo, False)
                return was_changed

        for child_fi in fo.child_files.values():
            if child_fi.hash_is_wrong:
                was_changed = self.model.set_folder_is_ok(fo, False)
                return was_changed
         
        h = hashlib.sha1()
        for child_fo in fo.child_folders.values():
            h.update(child_fo.hash_)
        for child_fi in fo.child_files.values():
            h.update(child_fi.hash_)
        hashSum = h.hexdigest()
        
        if fo.hash_ and not self.rehashFolders:
            was_changed = self.model.set_folder_is_ok(fo, fo.hash_ == hashSum)
            return was_changed
        else:
            self.model.set_folder_hash(fo, hashSum)
            self.model.set_folder_is_ok(fo, True)  # TODO: this could be merged in one stmt with model.updatefolder
            return True
        
    def update_parent_folder_is_ok(self, fo):
        """ Will recheck the parent folder of this folder, if the is_ok-values 
        does not match """
        if fo.is_mount_point:
            return
        parent_fo = self.model.get_folder_by_id(fo.parent_folder_id)
        if fo.hash_ and parent_fo.hash_ and fo.is_ok == parent_fo.is_ok:
            return
        else:
            was_changed = self.hash_folder(parent_fo)
            if was_changed and not parent_fo.is_mount_point:
                self.update_parent_folder_is_ok(parent_fo)
        
    def process_file(self, fi):
        pos = 0
        h = hashlib.sha1()
        filePath = os.path.join(fi.folder.full_path, fi.name)
        with open(filePath, 'r') as f:
            while True:
                d = f.read(self.CHUNK_SIZE)
                if not d: break
                h.update(d)
                pos += self.CHUNK_SIZE
                if pos > fi.filesize:
                    pos = fi.filesize
                yield pos*100/fi.filesize, 'Hashing (%s%%) %s'%(pos, filePath)
        
        if fi.hash_:
            self.model.set_file_hash_is_wrong(fi, fi.hash_ != h.hexdigest())
        else:
            self.model.set_file_hash(fi, h.hexdigest())
        self.currentSize += fi.filesize        
        
    def process_folder(self, fo):
        progress = self.totalSize/self.currentSize if self.currentSize else 0
        yield (progress, fo.full_path)
        for child_fo in fo.child_folders.values():
            for info in self.process_folder(child_fo):
                yield info
        for child_fi in fo.child_files.values():
            for info in self.process_file(child_fi):
                yield info
        
        self.hash_folder(fo)
    
        
    
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

        fi = self.model.insert_file(path, fo=fo, filesize=os.path.getsize(path))
        self._totalSize += fi.filesize
        self._noFiles += 1
        if fi.is_none():
            raise Exception('File %s was none'%path)
        return fi
    
    def import_folder(self, path, parent_fo=DB_Folder(), startingFolder=None):
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
                self.import_file(el, fo)
        
        # Hack to return the folder
        if not startingFolder is None:
            startingFolder.append(fo)
    
    def run_action(self):
        start = time.time()
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            folder_path = os.path.dirname(self.path)
            fo = self.model.get_folder_by_path(folder_path)
            if fo.is_none():
                fo = self.model.insert_folder(folder_path)
            fi = self.import_file(self.path, fo)
            h = Hasher(self.model, 1, fi.filesize, rehashFolders=True)
            for info in h.process_file(fi):
                yield info
            fo.child_files.clear() # remove the one child file, so update_parent_folder select the complete list from DB!
            h.hash_folder(fo)
            h.update_parent_folder_is_ok(fo)
            yield (100, self.path)
        else:
            folderContainer = []
            for info in self.import_folder(self.path, startingFolder=folderContainer):
                yield info
            fo = folderContainer[0]
            h = Hasher(self.model, self._noFiles, self._totalSize, rehashFolders=True)
            for info in h.process_folder(fo):
                yield info
            h.update_parent_folder_is_ok(fo)
            
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
    
    def delete_parent_folder(self, fo):
        self.model.fill_child_folders(fo)
        self.model.fill_child_files(fo)
        if not fo.child_folders and not fo.child_files:
            self.model.delete_folder(fo)
            if not fo.is_mount_point:
                parent_fo = self.model.get_folder_by_id(fo.parent_folder_id)
                self.delete_parent_folder(parent_fo)
        else:
            h = Hasher(self.model, 1, 0, rehashFolders=True)
            h.hash_folder(fo)
            h.update_parent_folder_is_ok(fo)
    
    def delete_folder(self, fo):
        self.model.fill_child_folders(fo)
        for child_fo in fo.child_folders.values():
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
            self.delete_parent_folder(fi.folder)
            yield (None, self.path)
        else:
            yield (None, self.path)
            fo = self.model.get_folder_by_path(self.path)
            for info in self.delete_folder(fo):
                yield info
            if not fo.parent_folder_id is None:
                parent_fo = self.model.get_folder_by_id(fo.parent_folder_id)
                self.delete_parent_folder(parent_fo)
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
   
    def read_folder(self, fo):
        self.model.fill_child_files(fo)
        for child_fi in fo.child_files.values():
            self._totalSize += child_fi.filesize
            self._noFiles += 1
            
        self.model.fill_child_folders(fo)
        for child_fo in fo.child_folders.values():
            for info in self.read_folder(child_fo):
                yield info
        
    def run_action(self):
        start = time.time()
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            fi = self.model.get_file_by_path(self.path)
            if fi.is_none():
                return
            h = Hasher(self.model, 1, fi.filesize)
            for info in h.process_file(fi):
                yield info
            fi.folder.child_files.clear() # remove the one child file, so update_parent_folder select the complete list from DB!
            h.hash_folder(fi.folder)
            h.update_parent_folder_is_ok(fi.folder)
        else:
            fo = self.model.get_folder_by_path(self.path)
            if fo.is_none():
                return
            for info in self.read_folder(fo):
                yield info
            h = Hasher(self.model, self._noFiles, self._totalSize)
            for info in h.process_folder(fo):
                yield info
            h.update_parent_folder_is_ok(fo)
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
        print 'schema created'
    
    m.commit_and_close()
    
    print 'Duration: ', time.time()-start
