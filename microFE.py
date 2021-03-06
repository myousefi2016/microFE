#!/usr/bin/python

'''
File: microFE.py
Author: A Melis
'''

__author__ = "Alessandro Melis"
__copyright__ = "Copyright 2017 INSIGNEO Institute for in silico Medicine"
__credits__ = ["A Melis", "Y. Chen"]
__version__ = "0.0.1"
__maintainer__ = "Alessandro Melis"
__email__ = "a.melis@sheffield.ac.uk"

import os
import sys
from argparse import ArgumentParser
from ConfigParser import SafeConfigParser


class microFE():
    '''
    microFE class definition.
    '''

    def __init__(self, cfg_file_name):
        '''
        Read .ini configuration file and create output directory

        Parameters
        ----------
        cfg_file_name : str
            Configuration filename.
        '''

        # parse .ini configuration file
        p = SafeConfigParser()
        p.read(cfg_file_name)

        # CT images
        self.file_folder = p.get("directories", "file_folder")
        self.binary_folder = p.get("directories", "binary_folder")
        self.out_folder = p.get("directories", "out_dir")
        self.parafem_dir = p.get("directories", "parafem_files_dir")
        self.img_names = p.get("images", "img_names")

        assert os.path.isdir(self.file_folder), "FILE_FOLDER does not exist"

        # mesher
        self.threshold = p.get("mesher_parameters", "threshold")
        self.Image_Resolution = p.get("mesher_parameters", "Image_Resolution")
        self.M_FILES = p.get("directories", "m_files")
        self.LD_LIB_PATH = p.get("directories", "ld_lib_path")
        self.perc_displacement = float(p.get("mesher_parameters", "perc_displacement"))

        assert os.path.isdir(self.M_FILES), "M_FILES folder does not exist"

        self.job_name = p.get("job", "name")

        self.mesher_params = [self.file_folder, self.img_names, self.binary_folder,
            self.Image_Resolution, self.threshold, self.out_folder]

        # ParaFEM
        self.nip = p.get("parafem_parameters", "nip")
        self.limit = p.get("parafem_parameters", "limit")
        self.tol = p.get("parafem_parameters", "tol")
        self.E = p.get("parafem_parameters", "E")
        self.vP = p.get("parafem_parameters", "vP")
        self.nloadstep = p.get("parafem_parameters", "nloadstep")
        self.jump = p.get("parafem_parameters", "jump")
        self.tol2 = p.get("parafem_parameters", "tol2")

        # create output folders
        if not os.path.isdir(self.out_folder):
            os.mkdir(self.out_folder)
        elif os.path.isfile("{0}/elementdata.txt".format(self.out_folder)):
            print "WARNING: Previous matlab mesh files in OUT_DIR = {0}".format(self.out_folder)

        if not os.path.isdir(self.binary_folder):
            os.mkdir(self.binary_folder)

        if not os.path.isdir(self.parafem_dir):
            os.mkdir(self.parafem_dir)
        elif os.path.isfile("{0}/{1}.dat".format(self.out_folder, self.job_name)):
            print "WARNING: Previous ParaFEM mesh files in PARAFEM_FILES_DIR = {0}".format(self.parafem_dir)


    def launchMatlabMesher(self):
        '''
        Launch the matlab mesher.
        '''

        sep = '" '
        pre = '"'

        command = "{0}run_main.sh {1} ".format(self.M_FILES, self.LD_LIB_PATH)
        for p in self.mesher_params:
            command += pre+str(p)+sep
        # print command
        os.system(command)


    def convertMesh(self):
        '''
        Convert matlab output files to ParaFEM input files.
        '''

        # system geometry
        d_file = open("{0}/{1}.d".format(self.parafem_dir, self.job_name), 'w')
        d_file.write("*THREE_DIMENSIONAL\n")
        d_file.write("*NODES\n")
        self.nnod = 0 # nodes counter
        self.nel = 0 # elements counter
        self.nodpel = 8 # number of nodes per element

        # constrained DOFs
        bnd_file = open("{0}/{1}.bnd".format(self.parafem_dir, self.job_name), 'w')
        self.nres = 0 # constrained nodes counter

        # prescribed displacements != 0
        fix_file = open("{0}/{1}.fix".format(self.parafem_dir, self.job_name), 'w')
        self.nfixnod = 0 # fixed nodes counter
        height = 0.0

        # prescribed loads
        lds_file = open("{0}/{1}.lds".format(self.parafem_dir, self.job_name), 'w')
        self.nlnod = 0 # loaded nodes counter

        #---------------------------------------------------------------------------------

        # Write lds and bnd file
        # Loops through nodedata.txt and finds the max z-coordinate
        # this will be used to assign displacement to uppermost nodes.
        # Nodes with nz=0 are constrained, a zero load along x, y, and z is also assigned.

        # TODO: find highest node directly in matlab rather than here

        with open("{0}/nodedata.txt".format(self.out_folder), 'r') as nodes:
            for node in nodes:
                n = node.strip().split(',')

                ni = n[1]
                nx = float(n[2])
                ny = float(n[3])
                nz = float(n[4])

                # add node to nodes list
                d = "{0} {1} {2} {3}\n".format(ni, nx, ny, nz)
                d_file.write(d)
                self.nnod += 1

                # find highest (z-wise) nodes
                if nz > height:
                    height = nz



                # constrain bottom nodes
                if nz == 0.0:
                    b = "{0} 1 1 1\n".format(ni)
                    bnd_file.write(b)
                    self.nres += 1

                # assign zero load
                l = "{0} 0.0 0.0 0.0\n".format(ni)
                lds_file.write(l)
                self.nlnod += 1

        bnd_file.close()
        lds_file.close()

        # Compute upper face displacement as percentage of model height
        # perc_displacement is user-assigned in the configuration file
        displacement = height * self.perc_displacement / 100.0

        #---------------------------------------------------------------------------------

        # Assign displacement while iterating again over nodedata
        with open("{0}/nodedata.txt".format(self.out_folder), 'r') as nodes:
            for node in nodes:
                n = node.strip().split(',')

                ni = n[1]
                nz = float(n[4])

                # assign displacement to upper nodes
                if nz == height: # displacement only along z-axis
                    f = "{0} 3 {1}\n".format(ni, displacement)
                    fix_file.write(f)
                    self.nfixnod += 1
        fix_file.close()

        #---------------------------------------------------------------------------------

        # Write elements in d file

        d_file.write("*ELEMENTS\n")
        with open("{0}/elementdata.txt".format(self.out_folder), 'r') as elems:
            for element in elems:
                self.nel += 1

                e = element.strip().split(',')

                ei = self.nel # element index

                # element nodes indices
                e1 = e[1]
                e2 = e[2]
                e3 = e[3]
                e4 = e[4]
                e5 = e[5]
                e6 = e[6]
                e7 = e[7]
                e8 = e[8]

                #    8-------7
                #   /|      /|
                #  / |     / |
                # 5-------6  |
                # |  4----|--3
                # | /     | /
                # |/      |/
                # 1-------2

                d = "{0} 3 8 1 {1} {2} {3} {4} {5} {6} {7} {8} 1\n".format(ei, e1, e2, e3,
                                                                        e4, e5, e6, e7, e8)
                d_file.write(d)
        d_file.close()


    def writeDat(self):
        '''
        Write .dat file with the following structure

        nel  nnod nres nlnod nfixnod nip
        limit tol e (Young) v (Poisson)
        nodpel
        nloadstep jump
        tol2
        '''
        with open("{0}/{1}.dat".format(self.parafem_dir, self.job_name), 'w') as dat:
            line = "{0} {1} {2} {3} {4} {5}\n".format(self.nel, self.nnod, self.nres,
                                                      self.nlnod, self.nfixnod, self.nip)
            dat.write(line)

            line = "{0} {1} {2} {3}\n".format(self.limit, self.tol, self.E, self.vP)
            dat.write(line)

            dat.write("{0}\n".format(self.nodpel))
            dat.write("{0} {1}\n".format(self.nloadstep, self.jump))
            dat.write("{0}\n".format(self.tol2))


if __name__ == "__main__":

    parser = ArgumentParser()

    parser.add_argument("-c", "--cfgfile", help="configuration file name", dest="cfgfile")
    parser.add_argument("-r", "--runcmd", help="run command 'mesh' or 'convert'", dest="cmd")

    args = parser.parse_args()

    print "Parse configuration file"
    mFE = microFE(args.cfgfile)

    if args.cmd == "mesh":
        print "Run mesher"
        mFE.launchMatlabMesher()

    elif args.cmd == "convert":

        # TODO: get displacement from DVC

        print "Convert mesh to ParaFEM format"
        mFE.convertMesh()
        mFE.writeDat()
