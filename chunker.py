"""
Copyright [2013] [James Absalon]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import io
import math
import numpy
import os
from bitarray import bitarray
from block import Source as SourceBlock

class FileChunker(object):

    def __init__(self, k, symbolsize, filename):
        """
        File chunker constructor

        Arguments:
        k           -- Integer number of symbols per block
        symbol_size -- Integer Size of each symbol (IN BYTES)
        filename    -- String name of file to chunk
        """
        self.block_id = 0
        self.k = k
        self.symbolsize = symbolsize # Bytes
        self.blocksize = self.symbolsize * self.k # Bytes
        self.filename = filename
        self.filesize = os.path.getsize(filename)
        self.total_blocks = int(math.ceil(self.filesize / (self.blocksize * 1.0)))

        if not (self.symbolsize % 8 == 0):
            raise Exception("Please choose a symbol size that is a multiple of 8 Bytes for 64 bit systems")
        self.ints_to_read = self.symbolsize / 8 # 64 bit machine
        self.padding = self.pad_to_even_blocksize()
        
        #self.ints_to_read = self.symbolsize / 4 # 32 bit machine
        #if not (self.symbolsize % 4 == 0):
        #    raise Exception("Please choose a symbol size that is a multiple of 4 Bytes for 32 bit systems")

        try:
            #self._f = io.open(filename, 'r+b')
            self._f = open(filename, 'rb')
        except Exception:
            raise Exception('Unable to open file %s for reading.' % filename)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def pad_to_even_blocksize(self):

        padding = self.blocksize - (self.filesize % self.blocksize)
        if padding:
            f = io.open(self.filename, 'a+b')
            for i in xrange(padding):
                f.write(b'\x00')
            os.fsync(f)
            f.close()
        return padding

    def chunk(self):
        """
        Should return a block of bitarrays
        Attempts to read k symbols from the file and pads a block
        so that the block is k symbols of symbolsize * 8 bits
        """
        # Check to see file is still open
        if self._f.closed:
            return None
        
        block = SourceBlock(self.k, self.symbolsize, self.get_block_id())

        j = 0
        EOF = False

        while (j < self.k and not EOF):
            b = self._read()
            if not (b is None):
                block.append(b)
                j += 1
            else:
                EOF = True
                self.close()

        if len(block) == 0:
            return None

        # Indicate padding on the last block
        if block.id == self.total_blocks - 1:
            block.padding = self.padding

        return block

    def _read(self):
        """
        Reads symbolsize bytes from the file
        Returns None if the length is 0
        Returns a bit array of symbolsize * 8 bits otherwise
        """
        difference = self.filesize + self.padding - self._f.tell()

        if difference > 0:
            return numpy.fromfile(self._f, dtype='uint64', count=self.ints_to_read)
        return None

    def get_block_id(self):
        """
        Gets the current block id and increments to prepare for the next block.
        Returns the current block id
        """
        r = self.block_id
        self.block_id += 1
        return r

    def close(self):
        """
        Attempts to close the file associated with this chunker
        """
        try:
            os.fsync(self._f)
            self._f.close()
            if self.padding:
                f = io.open(self.filename, 'a+b')
                f.truncate(self.filesize)
                f.close()
        except:
            pass


