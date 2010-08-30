import sqlite3
import os

from action import Action

def _one(cursor):
    res = cursor.fetchone()
    if res is None:
        return None
    else:
        return res[0]
    

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
        
        
    def file(self, path, insertIfMissing, folder_id=None):
        self.log('file: path=%s, folder_id=%s'%(path, folder_id))
        
        if os.path.islink(path):
            # Ingnore links
            return None, None
        
        folder, filename = os.path.split(path)
                
        # select parent folder
        if folder_id is None:
            folder_id = self.folder(folder, False)
            if folder_id is None:
                return None, None
        
        # select file
        c = self.conn.cursor()
        c.execute("select id from file where name = ? and folder_id = ?",
                  (filename, folder_id))
        file_id = _one(c)
        if file_id is not None:
            return folder_id, file_id

        # insert file
        if insertIfMissing:
            c = self.conn.cursor()
            c.execute("insert into file (name, folder_id) values (?, ?)",
                      (filename, folder_id))
            return folder_id, c.lastrowid
        else:
            return None, None
        
    
    def folder(self, path, insertIfMissing, parent_folder_id=None):
        """ 
        @parm insertIfMissing: If the folder is not found, insert it
        
        Try to select a folder. If it fails and insertIfMissing is True
        try to insert the parent folder by calling this method. After the 
        parent folder was inserted (or selected), insert this folder with 
        the received ID.
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
        
        # Try to select
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
                c.execute("select id from folder where name = ? and parent_folder_id = ?",
                          (folder, parent_folder_id))
            res = c.fetchone()
            if res is not None:
                return res[0]
            
        # No folder in db, do insert
        if not insertIfMissing:
            print 'insertifmissing', insertIfMissing
            return None      
                
        if parent_folder_id is None and not is_mount_point:
            parent_folder_id = self.folder(root, True)
        
        self.log('insert ' + path)
        c.execute("""insert into folder 
                     (name, full_path, parent_folder_id, is_mount_point)
                     values (?, ?, ?, ?)""", 
                    (folder, path, parent_folder_id, is_mount_point))
        return c.lastrowid
    
    def delete_file(self, folder_id, file_id):
        c = self.conn.cursor()
        c.execute("delete from file where folder_id = ? and id = ?", (folder_id, file_id))
        
    def get_child_folders(self, parent_folder_id):
        c = self.conn.cursor()
        c.execute("select id, full_path from folder where parent_folder_id = ?", (parent_folder_id, ))
        return c.fetchall()
    
    def delete_folder(self, folder_id):
        """ Will delete the files in this folder, then the foldern itself.
        Attention: Make sure, the given folder doesnt have any subfolders!"""
        print folder_id
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
    
    
    
class ImportFilesAction(Action):
    def __init__(self, path):
        self.path = path
        
    def get_name(self):
        return 'Dateien importieren: %s'%self.path

    def import_files(self, path, parent_folder_id):
        yield('?', path)
        folder_id = self.model.folder(path, True, parent_folder_id)
        if folder_id is None:
            raise Exception('Import failed: %s (%s)' % (self.path, parent_folder_id))
        
        for el in os.listdir(path):
            el = os.path.join(path, el)
            if os.path.islink(el):
                continue
            if os.path.isdir(el):
                for info in self.import_files(el, folder_id):
                    yield info

            elif os.path.isfile(el):
                _, file_id = self.model.file(el, True, folder_id)
                if file_id is None:
                    raise Exception('Import failed: %s (%s)' % (el, folder_id))
    
    def run_action(self):
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            folder_id = self.model.folder(os.path.dirname(self.path), True)
            print folder_id
            _, dbID = self.model.file(self.path, True, folder_id=folder_id)
            if not dbID:
                self.model.rollback()
                raise Exception('Insert failed: %s'%self.path)
            yield (100, self.path)
        else:
            for info in self.import_files(self.path, None):
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
        for folder_id, full_path in rows:
            for info in self.delete_folder(folder_id, full_path):
                yield info
            
        self.model.delete_folder(folder_id)
    
    def run_action(self):
        self.model = Model(logger=printer).set_connection(get_connection())
        if os.path.isfile(self.path):
            folder_id, file_id = self.model.file(self.path, False)
            if folder_id is None or file_id is None:
                raise Exception('delete of file failed: %s' % (self.path))
            self.model.delete_file(folder_id, file_id)
            yield (100, self.path)
        else:
            yield ('?', self.path)
            folder_id = self.model.folder(self.path, False)
            for info in self.delete_folder(folder_id, self.path):
                yield info
        self.model.commit_and_close()
        yield('100', '')
    
            
        
         
dbPath = 'db01.sqlite'

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
    
    fs = FileSystem(m)
    fs.importFolder('/home/benjamin/d/devel')
    
    m.commit_and_close()
    
    print 'Duration: ', time.time()-start