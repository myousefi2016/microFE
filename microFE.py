
import os
import sys
from ConfigParser import SafeConfigParser

class microFE():
    def __init__(self, file_name):

        # parse .ini configuration file
        p = SafeConfigParser()
        p.read(sys.argv[1])

        self.WORK = p.get("directories", "work")
        self.IMG = p.get("directories", "img")
        self.img_folder = "{0}{1}".format(self.WORK, self.IMG)
        self.img_names = p.get("images", "img_names")
        self.out_folder = p.get("directories", "out_dir")

        self.nCells = p.get("parameters", "nCells")
        self.Grey_boneThreshold = p.get("parameters", "Grey_boneThreshold")
        self.Grey_marrowThreshold = p.get("parameters", "Grey_marrowThreshold")
        self.Image_Resolution = p.get("parameters", "Image_Resolution")

        self.CAL1 = p.get("directories", "cal1")
        self.CAL2 = p.get("directories", "cal2")
        self.calibration_folder_1 = "{0}{1}".format(self.WORK, self.CAL1)
        self.calibration_folder_2 = "{0}{1}".format(self.WORK, self.CAL2)
        self.calibration_names = p.get("images", "cal_names")

        self.M_FILES = p.get("directories", "m_files")
        self.LD_LIB_PATH = p.get("directories", "ld_lib_path")

        self.job_name = p.get("job", "name")

        self.params = [self.img_folder, self.img_names, self.Grey_boneThreshold,
            self.nCells, self.Grey_marrowThreshold, self.Image_Resolution,
            self.calibration_folder_1, self.calibration_folder_2,
            self.calibration_names, self.out_folder]

        self.job_type = p.get("job", "type")

        if self.job_type == "HPC":
            self.walltime = p.get("job", "walltime")
            self.budget_code = p.get("job", "budget_code")

        # create output folder
        if not os.path.isdir(self.out_folder):
            os.mkdir(self.out_folder)

        return


    def launchMatlabMesher(self):
        sep = '" '
        pre = '"'

        # write batch script for ARCHER
        if self.job_type == "HPC":
            microFE_file = "microFE_{0}.sh".format(self.job_name)

            line="#!/bin/bash --login \n"
            line+="#PBS -N {0} \n".format(self.job_name)
            line+="#PBS -l select=serial=true:ncpus=1 \n"
            line+="#PBS -l walltime=01:00:00 \n".format(self.walltime)
            line+="#PBS -A d137-me1ame \n".format(self.budget_code)
            line+="export PBS_O_WORKDIR=$(readlink -f $PBS_O_WORKDIR) \n"
            line+="cd $PBS_O_WORKDIR \n"
            line+="module load mcr/9.0 \n"

            command = "{0}{1}run_main.sh {2} ".format(self.WORK, self.M_FILES,
                                                        self.LD_LIB_PATH)
            for p in self.params:
                command += pre+str(p)+sep
            line += command

            with open(microFE_file,"w") as f:
                f.write(line)

            os.system("qsub {0}".format(microFE_file))

        # launch mesher on workstation
        else:
            command = "{0}{1}run_main.sh {2} ".format(self.WORK, self.M_FILES,
                                                        self.LD_LIB_PATH)
            for p in self.params:
                command += pre+str(p)+sep

            print command
            os.system(command)


if __name__ == "__main__":

    # parse .ini configuration file
    mFE = microFE(sys.argv[1])

    # use matlab scripts to generate the mesh
    mFE.launchMatlabMesher()
