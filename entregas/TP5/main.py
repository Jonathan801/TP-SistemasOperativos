from hardware import *
from so import *
import log

##
##  MAIN
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(40)

    ## Switch on computer
    HARDWARE.switchOn()

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    kernel = Kernel()

    ##  create a program
    ##prg = Program("test.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(3)])
    ##prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    ##prg2 = Program("prg2.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])
    ##prg3 = Program("prg3.exe", [ASM.CPU(3)])

    prg1 = Program([ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program([ASM.CPU(6)])
    prg3 = Program([ASM.CPU(4), ASM.IO(), ASM.CPU(1)])


    ##Ahora vamos a guardar los programas en el FileSystem
    kernel.fileSystem().write("c:/prg1.exe", prg1)
    kernel.fileSystem().write("c:/prg2.exe", prg2)
    kernel.fileSystem().write("c:/prg3.exe", prg3)

    # execute the program
    #kernel.run(prg1, 2)
    #kernel.run(prg2, 1)
    #kernel.run(prg3)



    kernel.run("c:/prg1.exe", 0)
    kernel.run("c:/prg2.exe", 2)
    kernel.run("c:/prg3.exe", 1)
    #log.logger.info("MemoryTable " + str(kernel.memoryManager().memoryTable()))





