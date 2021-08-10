import sys

from hardware import *
import log

class Program():

    def __init__(self,  instructions):
        self._instructions = self.expand(instructions)


    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({instructions})".format( instructions=self._instructions)

class Disk():

    def __init__(self):
        self._programs = dict()

    def programs(self):
        return self._programs

    def writeProgram(self,patch, instructions):
        self._programs[patch]= instructions

    def getProgram(self, patch):
        return self.programs().get(patch)

    def returnInstructions(self, path, index, cant):
        res = []
        var = index + cant
        while index <  var:
            res.append(self.getProgram(path)[index])
            index = index + 1
        return res


###------------------------------------------------------------------------------------------------------------

disco = Disk()
prg1 = Program([ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])

print(prg1.instructions)
disco.writeProgram(prg1,prg1.instructions)
print(disco.getProgram(prg1))
print(disco.getProgram(prg1)[0])
print(disco.getProgram(prg1)[1])
print(disco.getProgram(prg1)[2])
print(disco.getProgram(prg1)[3])
print(disco.returnInstructions(prg1,0,4))
