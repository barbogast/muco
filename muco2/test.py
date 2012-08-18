import unittest
from StringIO import StringIO
import os

from main import DictFile


class Test_SHA_file(unittest.TestCase):
    tmp_filename = 'testtmpfile.txt'
    
    def _prepare_file(self, contents):
        f = open(self.tmp_filename, 'w')
        f.write(contents)
        f.close()
        
    def assert_file_content(self, expected):
        written = open(self.tmp_filename).read()
        self.assertEqual(expected, written)
        
    def setUp(self):
        if os.path.isfile(self.tmp_filename):
            os.remove(self.tmp_filename)
        
        
    def test_read_file(self):
        self._prepare_file('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        sf = DictFile(self.tmp_filename)
        self.assertEqual(2, len(sf))
        
        self.assertIn('file_a.txt', sf)
        self.assertIn('file_b.xyz', sf)
        
        self.assertEqual('xxx', sf['file_a.txt'])
        self.assertEqual('yyy', sf['file_b.xyz'])
        
        self.assertRaises(KeyError, sf.__getitem__, 'file_c.xyz')

        
    def test_write_file(self):
        sf = DictFile(self.tmp_filename)
        sf.add('file_a.txt', 'xxx')
        sf.add('file_b.xyz', 'yyy')
        
        expected = {'file_a.txt': 'xxx', 'file_b.xyz': 'yyy'}
        self.assertEqual(expected, sf)
        self.assert_file_content('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        
    def test_append_to_existing_file(self):
        self._prepare_file('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        sf = DictFile(self.tmp_filename)
        sf.add('file_c.mp3', 'zzz')

        expected = {'file_a.txt': 'xxx', 'file_b.xyz': 'yyy', 'file_c.mp3': 'zzz'}
        self.assertEqual(expected, sf)
        self.assert_file_content('file_a.txt=xxx\nfile_b.xyz=yyy\nfile_c.mp3=zzz\n')
        
    
    def test_write_file_duplicate(self):
        self._prepare_file('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        sf = DictFile(self.tmp_filename)
        
        with self.assertRaises(KeyError) as cm:
            sf.add('file_a.txt', 'xxx')
        the_exception = cm.exception
        self.assertEqual("Key 'file_a.txt' already present", cm.exception.args[0])
        self.assert_file_content('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        
    def test_change_value(self):
        self._prepare_file('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        sf = DictFile(self.tmp_filename)
        sf['file_a.txt'] = 'x1x'
        
        self.assertEqual('x1x', sf['file_a.txt'])
        self.assert_file_content('file_a.txt=x1x\nfile_b.xyz=yyy\n')
        
    def test_change_entry_does_not_exist(self):
        self._prepare_file('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        sf = DictFile(self.tmp_filename)
        with self.assertRaises(KeyError) as cm:
            sf['file_c'] = 'zzz'
        self.assertEqual("Key 'file_c' does not exist", cm.exception.args[0])
        
    def test_remove(self):
        self._prepare_file('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        sf = DictFile(self.tmp_filename)
        del(sf['file_a.txt'])
        
        self.assertNotIn('file_a.txt', sf)
        self.assert_file_content('file_b.xyz=yyy\n')
        
        
    def test_remove_entry_does_not_exist(self):
        self._prepare_file('file_a.txt=xxx\nfile_b.xyz=yyy\n')
        
        sf = DictFile(self.tmp_filename)
        with self.assertRaises(KeyError) as cm:
            del(sf['file_c'])       

    
class Test_Files(unittest.TestCase):
    def test_add_file(self):
        pass
    
    def test_check_file(self):
        pass
    