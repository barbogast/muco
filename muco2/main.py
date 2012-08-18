'''
Check / Add / Remove / Move:
 * file
 * empty folder
 * folder with files
 
 * folder with emtpy sub folder
 * folder with filled sub folder
 * folder with sub folder with sub folder
 
TODO:
 * History and atomic changes when changing a SHA file:
    1. Dont touch the original file
    2. Write the changed contents to a temporary file
    3. Rename the current SHA file to a name with an ascending number
    4. Rename the temporary file to the original filename
 * support for stuff like \n " and blanks in filenames
'''

from collections import OrderedDict
import os
import hashlib



class DictFile(OrderedDict):
    def __init__(self, filepath=None):
        super(DictFile, self).__init__()
        self._filepath = filepath
        if os.path.isfile(filepath):
            self._read_file()
        
    def _read_file(self):
        with open(self._filepath) as f:
            for line in f:
                key, value = line.strip().split('=')
                super(DictFile, self).__setitem__(key, value)
        
    def _write_file(self):
        with open(self._filepath, 'w') as f:
            for key, value in self.iteritems():
                f.write('%s=%s\n'%(key, value))
            
    def add(self, key, value):
        if key in self:
            raise KeyError("Key '%s' already present"%key)
        else:
            super(DictFile, self).__setitem__(key, value)
            self._write_file()
            
    def __setitem__(self, key, value):
        if key in self:
            super(DictFile, self).__setitem__(key, value)
            self._write_file()
        else:
            raise KeyError("Key '%s' does not exist"%key)
        
    def __delitem__(self, key):
        super(DictFile, self).__delitem__(key)
        self._write_file()
        


def hash_file(path):
    h = hashlib.sha1()
    h.update(open(path).read())
    return h.hexdigest()
    
        
def add_folder(path, hash_file_name):
    hash_file_path = os.path.join(path, hash_file_name)
    hf = DictFile(hash_file_path)
    for element in os.listdir(path):
        element_path = os.path.join(path, element)
        if os.path.isdir(element_path):
            hash_sum = process_folder(element_path, hash_file_name)
        else:
            hash_sum = hash_file(element_path)

        if hash_sum is not None:
            hf.add(element, hash_sum)
    
    if hf:
        return hash_file(hash_file_path)
    else:
        return None # no files in folder => no hashes
                                  
    

def check_folder(path, hash_file_name):
    hash_file_path = os.path.join(path, hash_file_name)
    hf = DictFile(hash_file_path)
    
    contains_elements = False
    for element in os.listdir(path):
        element_path = os.path.join(path, element)
        if element == hash_file_name:
            continue
        elif os.path.isdir(element_path):
            hash_sum = check_folder(element_path, hash_file_name)
        else:
            hash_sum = hash_file(element_path)
        
        if hash_sum is not None:
            contains_elements = True
            if element not in hf:
                print 'Hash sum for %s [%s] not found in %s' % (element, path, hash_file_path)
            elif hf[element] != hash_sum:
                print 'Hash sum for %s differs' % (element_path, )
    
    if contains_elements:
        if not os.path.isfile(hash_file_path):
            print 'Hash file %s not found' % hash_file_path
            return None
        return hash_file(hash_file_path)
    else:
        return None
            
            
#process_folder('/home/ben/tmp/hnodeclient/h-client/tests_hclient', 'hash_file.txt')
check_folder('/home/ben/tmp/hnodeclient/h-client/tests_hclient', 'hash_file.txt')
