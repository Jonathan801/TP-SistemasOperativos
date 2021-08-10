from so.SecondChance import *
class MemoryManager():

    def __init__(self, memory, frameSize, tablePage):
        self._memory = memory
        self._pageTable = tablePage
        self._frameSize = frameSize
        self._listVictim = SecondChance()
        #self._listVictim = VictimFIFO()
        self._freeFrames = []
        for index in range(0, (memory.getSize() // frameSize)):
           self._freeFrames.append(index)

    def getMemory(self):
        return self._memory

    def pageTable(self):
        return self._pageTable

    def frameSize(self):
        return self._frameSize

    def listVictim(self):
        return self._listVictim

    def freeFrames(self):
        return self._freeFrames

###-----------------------------------------------------------------------------------------------------------------

    def addFrames(self, listFrames):
        for frame in listFrames:
            if self.freeFrames().count(frame) < 1:
                self.freeFrames().append(frame)

    def allocFrame(self):
        if len(self.freeFrames()) > 0:
            return self.freeFrames().pop(0)

     ###Agrega una victima a la lista de victimas
    def addVictim(self, row):
        self.listVictim().addVictim(row)

    ##Retorna la siguiente victima
    def nextVictim(self):
        log.logger.info("Table Page: " + str(self.pageTable()))
        return self.listVictim().returnVictim()

    def setFrameInPage(self, pid , page, frame):
        self.pageTable().setFrameOfPage(pid , page, frame)

    def setRowInSwapping(self,pid, page, bool):
        self.pageTable().setPageInSwapping(pid, page, bool)


