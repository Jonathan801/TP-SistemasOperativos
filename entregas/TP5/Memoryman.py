class memoryMan():
    def __init__(self, memory, frameSize, tablePage):
        self._memory = memory
        self._pageTable = tablePage
        self._frameSize = frameSize
        self._freeFrames = []
        for index in range(0, (memory // frameSize)):
           self._freeFrames.append(index)

    def frameSize(self):
        return self._frameSize

    def memory(self):
        return self._memory

    def freeFrames(self):
        return self._freeFrames

    def addFrames(self, listFrames):
        self.freeFrames().extend(listFrames)

    def allocFrames(self, cant):
        list = []
        if len(self.freeFrames()) >= cant:
            for index in range(0, cant):
                list.append(self.freeFrames().pop(0))
        return list

    def pageTable(self):
        return self._pageTable


memo = memoryMan(40)