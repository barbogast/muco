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
            hash_sum = add_folder(element_path, hash_file_name)
        else:
            hash_sum = hash_file(element_path)

        hf.add(element, hash_sum)
    
    # Touch file if its still not created
    open(hash_file_path, 'a').close()
        
    return hash_file(hash_file_path)
                                  
    

def check_folder(path, hash_file_name):
    hash_file_path = os.path.join(path, hash_file_name)
    hf = DictFile(hash_file_path)

    for element in os.listdir(path):
        element_path = os.path.join(path, element)
        if element == hash_file_name:
            continue
        elif os.path.isdir(element_path):
            hash_sum = check_folder(element_path, hash_file_name)
        else:
            hash_sum = hash_file(element_path)

        if element not in hf:
            print 'Hash sum for %s [%s] not found in %s' % (element, path, hash_file_path)
        elif hf[element] != hash_sum:
            print 'Hash sum for %s differs' % (element_path, )
    
    return hash_file(hash_file_path)

            

hash_file_name = '_hash_file02.txt'
folder = '/home/ben/muell/RoyalEnvoyIICE/Base'    
#add_folder(folder, hash_file_name)
check_folder(folder, hash_file_name)
