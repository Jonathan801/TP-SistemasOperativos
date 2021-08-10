#!/usr/bin/env python
import sys

from hardware import *
import log

## emulates a compiled program
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

class PCB():

    def __init__(self, pid,  path, priority):
        self._pid = pid
        #self._baseDir = db
        self._pc = 0
        self._state = "New"
        self._path = path
        self._priority = priority

    # ----------------Getters---------------------------------------------------------
    def getPc(self):
        return self._pc

    def getPid(self):
        return self._pid

    def getPath(self):
        return self._path

    def getBaseDir(self):
        return self._baseDir


    def getState(self):
        return self._state

    def getPriority(self):
        return self._priority

    # ----------------Setters----------------------------------------------------------

    def setPc(self, pc):
        self._pc = pc

    def setState(self, state):
        self._state = state

    def __repr__(self):
        return "(" + "PDI={pdi}".format(pdi=self._pid) + " PC={pc}".format(pc=self._pc) + " STATE={state}".format(state=self._state)  + " PATCH={path}".format(path=self._path) + " PRIORIDAD={pri}".format(
            pri=self._priority) + ")"

class PcbTable():

    def __init__(self):
        self._pcbs = dict()
        self._running = None
        self._countPid = 0

    # ----------------------- Getters ------------------------------------------------
    def returnPCB(self, k):
        return self._pcbs.get(k)

    def updatePC(self, k, pc):
        self.returnPCB(k).setPc(pc)

    def returnRunning(self):
        return self._running

    def updateState(self, k, state):
        self.returnPCB(k).setState(state)

    # ----------------------- Setters ------------------------------------------------
    def createPcb(self, path, priority):
        pcb = PCB(self._countPid,  path, priority)
        self.addPcb(pcb)
        self.increasePID()
        return pcb

    def increasePID(self):
        self._countPid += 1

    def setRunning(self, pcb):
        self._running = pcb

    def addPcb(self, pcb):
        self._pcbs[pcb.getPid()] = pcb

    def runningPCB(self, pcb):
        self._running = pcb

    def noneRunning(self):
        self._running = None

    def __repr__(self):
        return "(" + "TABLE ={table}".format(table=self._pcbs) + ")"

## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def waitingQueue(self):
        return self._waiting_queue

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            pair = self._waiting_queue.pop(0)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)

    def loadToWaitingQueue(self, pcb):
        self._waiting_queue.append(pcb)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(
            deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)

## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():

    def __init__(self, table, scheduler, dispatcher, memoryManager, fileSystem):
        self._scheduler = scheduler
        self._tablePCB = table
        self._dispatcher = dispatcher
        self._memoryManager = memoryManager
        self._fileSystem = fileSystem

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    def table(self):
        return self._tablePCB

    def scheduler(self):
        return self._scheduler

    def memoryManager(self):
        return self._memoryManager

    def dispatcher(self):
        return self._dispatcher

    def fileSystem(self):
        return self._fileSystem

    def selectWhereToAdd(self, pcb):
        pageOfPCB = self.memoryManager().pageTable().returnRowsOfPID(pcb.getPid())

        if self.table().returnRunning() == None:
            self.table().setRunning(pcb)
            self.dispatcher().load(pcb,pageOfPCB)
            self.table().runningPCB(pcb)
        else:
            self.isExpropiationScheduler(pcb, pageOfPCB)

    def isExpropiationScheduler(self,pcb,pageOfPCB):
        if self.scheduler().isExpropiation():
            self.caseExpropiation(pcb,pageOfPCB)
        else:
            self.scheduler().add(pcb)

    def caseExpropiation(self, pcb,pageOfPCB):
        if pcb.getPriority() < self.table().returnRunning().getPriority():
            self.expropiate(pcb,pageOfPCB)
        else:
            self.scheduler().add(pcb)

    def expropiate(self, pcb,pageOfPCB):
        self.dispatcher().save(self.table().returnRunning())
        self.scheduler().add(self.table().returnRunning())
        self.dispatcher().load(pcb,pageOfPCB)
        self.table().runningPCB(pcb)

class KillInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, table, scheduler, dispatcher, memoryManager,fileSystem):
        super(KillInterruptionHandler, self).__init__(table, scheduler, dispatcher, memoryManager, fileSystem)

    def saveFrames(self, pid):
        frames = self.memoryManager().pageTable().\
            returnRowsOfPID(self.table().returnRunning().getPid())
        framesFree = []
        for row in frames:
            if row.frame() != None:
                framesFree.append(row.frame())
                self.memoryManager().listVictim().removeVictim(row)
        self.memoryManager().addFrames(framesFree)
        self.fileSystem().clearSwapping(pid)


    def execute(self, irq):
        log.logger.info(" Program Finished ")
        self.dispatcher().save(self.table().returnRunning())
        HARDWARE.cpu.pc = -1
        ###Elimino las paginas del proceso en el swapping
        pid = self.table().returnRunning().getPid()
        self.saveFrames(pid)
        log.logger.info("List of victim in KILL: " + str(self.memoryManager().listVictim()))
        self.table().returnRunning().setState("Finished")
        log.logger.info("FREE FRAMES: " + str(self.memoryManager().freeFrames()))

        if self.scheduler().noIsEmpty():
            pcb = self.scheduler().returnNext()
            pageOfPCB = self.memoryManager().pageTable().returnRowsOfPID(pcb.getPid())
            self.dispatcher().load(pcb, pageOfPCB)
            self.table().runningPCB(pcb)

        else:
            self.table().noneRunning()

        log.logger.info("SWAPPING: " + str(self.fileSystem().swapping()))
        log.logger.info("PCB TABLE: " + str(self.table()))

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, table, scheduler, dispatcher, ioDevice, memoryManager,fileSystem):
        super(IoInInterruptionHandler, self).__init__(table, scheduler, dispatcher, memoryManager, fileSystem)
        self._ioDeviceController = ioDevice

    def ioDeviceController(self):
        return self._ioDeviceController

    def execute(self, irq):
        log.logger.info(" Program IN ")
        log.logger.info("waitin queue" + str(self.ioDeviceController()))
        operation = irq.parameters
        self.dispatcher().save(self.table().returnRunning())
        self.ioDeviceController().runOperation(self.table().returnRunning(), operation)
        self.table().noneRunning()
        HARDWARE.cpu.pc = -1
        if self.scheduler().noIsEmpty():
            pcb = self.scheduler().returnNext()
            pageOfPCB = self.memoryManager().pageTable().returnRowsOfPID(pcb.getPid())
            self.dispatcher().load(pcb, pageOfPCB)
            self.table().runningPCB(pcb)

        else:
            HARDWARE.cpu.pc = -1

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, table, scheduler, dispatcher, ioDevice, memoryManager, fileSystem):
        super(IoOutInterruptionHandler, self).__init__(table, scheduler, dispatcher,memoryManager,fileSystem)
        self._ioDeviceController = ioDevice

    def ioDeviceController(self):
        return self._ioDeviceController

    def execute(self, irq):
        log.logger.info(" Program Out")
        log.logger.info("PCB : " + str(self.table().returnRunning()))
        pcb = self.ioDeviceController().getFinishedPCB()
        log.logger.info(self.ioDeviceController())
        self.selectWhereToAdd(pcb)

class NewInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, table, loader, scheduler, dispatcher , memoryManager, fileSystem):
        super(NewInterruptionHandler, self).__init__(table, scheduler, dispatcher, memoryManager, fileSystem)
        self._loader = loader

    def loader(self):
        return self._loader

    def execute(self, irq):
        log.logger.info(" New PCB ")
        path = irq.parameters[0]
        cant = len(self.fileSystem().read(path).instructions)
        log.logger.info("Len del Programa: " + str(cant))
        pri = irq.parameters[1]
        pcb = self.table().createPcb( path, pri) #self.loader().getDirBase(),
        ##Cargo las paginas en la pageTable
        self.loader().load(path, pcb.getPid())
        #Pongo a correr al pcb
        self.selectWhereToAdd(pcb)
        ##Prints
        log.logger.info(HARDWARE.memory)
        log.logger.info("PAGETABLE: " + str(self.memoryManager().pageTable()))

class TimeOutInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, table, scheduler, dispatcher, memoryMananger, fileSystem):
        super(TimeOutInterruptionHandler, self).__init__(table, scheduler, dispatcher, memoryMananger, fileSystem)

    def execute(self, irq):
        log.logger.info("Entro en TimeOut ")
        if self.scheduler().noIsEmpty():
            self.changePCB()
        else:
            self.resetQuantum()
        log.logger.info("ReadyQueue" + str(self.scheduler().readyQueue()))

    def resetQuantum(self):
        HARDWARE.timer.reset()

    def changePCB(self):
        pcb = self.scheduler().returnNext()
        self.dispatcher().save(self.table().returnRunning())
        self.scheduler().add(self.table().returnRunning())
        pageOfPCB = self.memoryManager().pageTable().returnRowsOfPID(pcb.getPid())
        self.dispatcher().load(pcb, pageOfPCB)
        self.table().setRunning(pcb)
        self.resetQuantum()

class PageFaultInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, table, scheduler, dispatcher, memoryMananger, fileSystem, loader):
        super(PageFaultInterruptionHandler, self).__init__(table, scheduler, dispatcher, memoryMananger, fileSystem)
        self._loader = loader

    def loader(self):
        return self._loader

    def frameOfVictim(self):
        victim = self.memoryManager().nextVictim()
        pageVic = victim.page()
        pidVic = victim.pid()
        frame = victim.frame()
        instructions = self.loader().instructionsForSwapIn\
            (victim.frame() * self.memoryManager().frameSize(),
                                    self.memoryManager().frameSize())
        stateOfPcb = self.table().returnPCB(pidVic).getState()
        ###Se agrega las instrucciones de la pagina al swap
        self.fileSystem().swapIn(pageVic, pidVic, instructions,
                                 stateOfPcb)
        ###Seteo la pagina indicando que esta en memoria swapping
        self.memoryManager().setRowInSwapping(pidVic, pageVic, True)
        ###Seteo el frame de la pagina indicando que es None
        self.memoryManager().setFrameInPage(pidVic, pageVic, None)

        return frame

    def instructionsForRow(self, pid, page, path):
        row = self.memoryManager().pageTable().pageOfPid(pid, page)
        instructions = None
        if row.isLoadedInSwapping():
            instructions = self.fileSystem().swapOut(pid, page)

            self.memoryManager().setRowInSwapping(pid, page, False)
        else:
            instructions = self.fileSystem().readInstructions\
                (path, page * self.memoryManager().frameSize(),
                                         self.memoryManager().frameSize())
        return instructions

    def execute(self, irq):
        ###Pido el pcb que corre actualmente
        pcbInRuning = self.table().returnRunning()
        pid = pcbInRuning.getPid()
        path = pcbInRuning.getPath()

        pc = HARDWARE.cpu.pc
        pageId = pc // self.memoryManager().frameSize()
        offset = pc % self.memoryManager().frameSize()
        if offset < self.memoryManager().frameSize():
            pageId +1
        page = pageId
        frameId = self.memoryManager().allocFrame()
        if frameId == None:
            frameId = self.frameOfVictim()
        #busca las instrucciones en Disco o en swapping, de la pagina
        instructions = self.instructionsForRow(pid, page, path)
        ###Cargo la pagina en memoria y setea el frame
        self.memoryManager().setFrameInPage(pid, page, frameId)
        self.loader().loadPageInMemory(instructions,
                            frameId * self.memoryManager().frameSize())
        ###Agrego la pagina como proxima victima
        row = self.memoryManager().pageTable().pageOfPid(pid, page)
        self.memoryManager().addVictim(row)
        HARDWARE.mmu.setPageFrame(page, frameId)
        ### Prints
        log.logger.info(HARDWARE.memory)
        log.logger.info("SWAPPING: " + str(self.fileSystem().swapping()))

#Revisado
class Loader():

    def __init__(self, memoryManager, fileSystem, memory):
        self._memoryManager = memoryManager
        self._memory = memory
        self._dirBase = 0
        self._nextCell = 0
        self._fileSystem = fileSystem

    def memoryManager(self):
        return self._memoryManager

    def getMemory(self):
        return self._memory

    def getDirBase(self):
        return self._dirBase

    def getNextCell(self):
        return self._nextCell

    def fileSystem(self):
        return self._fileSystem

###--------------------------------------------------------------------------------------------------------------

    def createPage(self, cant,  pid):
        var = 0
        page = 0
        self.memoryManager().pageTable().addRow(pid, page)
        log.logger.info("Cantidad de instrucciones: "+ str(cant))
        for index in range(0, cant):
            if var < self.memoryManager().frameSize()-1 :
                var = var + 1

            else:
                page += 1
                var = 0
                self.memoryManager().pageTable().addRow(pid, page)
        log.logger.info("Paginas del pid: " + str(self.memoryManager().pageTable().returnRowsOfPID( pid)))

    ###Genera las rows de cada proceso
    def load(self, path, pid):
        cant = len(self.fileSystem().read(path).instructions)
        #program = self.fileSystem().read(path).instructions
        self.createPage(cant, pid)

    ###Carga las instrucciones en memoria
    def loadPageInMemory(self, instructions, index):
        for ins in instructions:
            inst = ins
            self.getMemory().put(index, inst)
            index +=1

    ###Busca las instrucciones en memoria para ser guardadas
    def instructionsForSwapIn(self, index, cant):
        res = []
        cantMax = index + cant
        for i in range(index, cantMax):
            ins =  self.getMemory().get(i)
            res.append(ins)
            self.getMemory().put(i, '')
        return res

#Revisado
class Dispatcher():

    def load(self, pcb, pageTableOfPCB):
        HARDWARE.mmu.resetTLB()
        for page in pageTableOfPCB :
            HARDWARE.mmu.setPageFrame(page.page(), page.frame())
        value2 = pcb.getPc()
        HARDWARE.cpu.pc = value2

    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu.pc)
        pcb.setState("Waiting")
        HARDWARE.cpu.pc = -1

#Revisado
class Level():

    ##Solo 3 niveles de prioridad
    def __init__(self):
        self._list = []
        for i in range(0, 3):
            self._list.append([])

    def level(self):
        return self._list

    ##Agrega un pcb a la queue
    def addPCB(self, pcb):
        self.level()[len(self.level()) - 1].append(pcb)

    def elemLevel(self):
        res = 0
        for i in self.level():
            res += len(i)
        return res

    def returnFirstList(self):
        return self.level()[0]

    def clearFirstList(self):
        self.level()[0].clear()

    def addList(self, list):
        self.level()[len(self.level()) - 1].extend(list)

    def getOlderLevel(self):
        for i in range(0, len(self.level()) - 1):
            self.level()[i].extend(self.level()[i + 1])
            self.level()[i + 1].clear()

    def returnPop(self):
        for index in self.level():
            if len(index) > 0:
                return index.pop(0)

    def __repr__(self):
        return "(Nivel = {queue})".format(queue=self.level())

#Revisado
class Scheduler():

    def __init__(self):
        self._queue = []
        self._expropiative = False

    def readyQueue(self):
        return self._queue

    def returnNext(self):
        return self.readyQueue().pop(0)

    def isExpropiation(self):
        return self._expropiative

    def add(self, pcb):
        self.readyQueue().append(pcb)

    def noIsEmpty(self):
        return len(self.readyQueue()) > 0

    def __repr__(self):
        return "(ReadyQueue = {queue})".format(queue=self.readyQueue())

class SchedulerPriority(Scheduler):

    def __init__(self, levels, isExpropiation):
        super(SchedulerPriority, self).__init__()
        self._expropiative = isExpropiation
        for i in range(0, levels):
            self._queue.append(Level())

    def getOlder(self):
        for index in range(1, len(self.readyQueue())):
            self.readyQueue()[index].getOlderLevel()
            if index < len(self.readyQueue()) - 1:
                self.readyQueue()[index].addList(self.readyQueue()[index + 1].returnFirstList())
                self.readyQueue()[index + 1].clearFirstList()

    def add(self, pcb):
        self.readyQueue()[pcb.getPriority()].addPCB(pcb)

    def noIsEmpty(self):
        var = 0
        for index in self.readyQueue():
            var += index.elemLevel()
        return var > 0

    def returnNext(self):
        for index in self.readyQueue():
            if index.elemLevel() > 0:
                pcbReturn = index.returnPop()
                self.getOlder()
                return pcbReturn

class SchedulerRRPriority(SchedulerPriority):

    def __init__(self, levels, isExpropiation, quantum):
        super(SchedulerPriority, self).__init__()
        self._expropiative = isExpropiation
        HARDWARE.timer.quantum = quantum
        for i in range(0, levels):
            self._queue.append(Level())

class SchedulerRR(Scheduler):

    def __init__(self, quantum):
        super(SchedulerRR, self).__init__()
        HARDWARE.timer.quantum = quantum

class Row():
    def __init__(self, pid, page):
        self._pid = pid
        self._page = page
        self._frame = None
        self._loadedInSwapping = False
        self._isSecondOpportunity = False

    def pid(self):
        return self._pid

    def page(self):
        return self._page

    def isSecondOpportunity(self):
        return self._isSecondOpportunity

    def setSecondOpportunity(self):
         self._isSecondOpportunity = True

    def frame(self):
        return self._frame


    def isLoadedInSwapping(self):
        return self._loadedInSwapping
###------------------------------------------------------------------------------------------------------------------

    def setFrame(self, frame):
        self._frame = frame

    def setLoadInSwapping(self, bool):
        self._loadedInSwapping = bool

    def __repr__(self):
        return "(" + "PDI={pdi}".format(pdi=self._pid) + " PAGE={page}".format(page=self._page) + " FRAME={frame}".format(
            frame=self._frame)+ " ISLOADEDINSWAPPING ={loaded}".format(loaded=self._loadedInSwapping) + \
               " ISSECONDCHANCE ={chance}".format(chance=self._isSecondOpportunity)+ ")"

#Revisado
class TablePage():

    def __init__(self):
        self._queuePage = []

    def queuePage(self):
        return self._queuePage

    def addRow(self, pid, page):
        self._queuePage.append(Row( pid, page))

    def returnRowsOfPID(self, pid):
        res = []
        for row in self.queuePage():
            if row.pid() == pid:
                res.append(row)
        return res

    def setFrameOfPage(self, pid, page, frame):
        row = self.pageOfPid(pid, page)
        row.setFrame(frame)

    def setPageInSwapping(self, pid, page, bool):
        row = self.pageOfPid(pid, page)
        row.setLoadInSwapping(bool)

    ###Retorna la pagina deseada pertenciente a un pid
    def pageOfPid(self, pid, page):
        rows = self.returnRowsOfPID(pid)
        for row in rows:
            if row.page() == page:
                return row

    def __repr__(self):
        return "(" + "TABLEPAGE ={table}".format(table=self._queuePage) + ")"

class VictimFIFO():
    def __init__(self):
        self._listVictim = []

    def addVictim(self, victim):
        self._listVictim.append(victim)

    def listVictim(self):
        return self._listVictim

    def removeVictim(self, victim):
        self.listVictim().remove(victim)

    def returnVictim(self):
        victim = self.listVictim().pop(0)
        return victim

    def __repr__(self):
        return "(" + "LIST VICTIM={list}".format(list=self._listVictim)  + ")"


class SecondChance():

    def __init__(self):
        self._listVictim = []
        self._index = 0


    def index(self):
        return self._index


    def addVictim(self, victim):
        self._listVictim.append(victim)

    def listVictim(self):
        return self._listVictim

    def removeVictim(self, victim):
        self.listVictim().remove(victim)
        if self.index() > len(self.listVictim()):
            self._index -=1


    def returnVictim(self):
        long = len(self._listVictim)
        while not self._listVictim[self.index()].isSecondOpportunity():
            self.listVictim()[self._index].setSecondOpportunity()
            if self.index() < long -1:
                self._index += 1
            else:
                self._index = 0


        victim = self._listVictim[self._index]
        self.listVictim().remove(self._listVictim[self._index])
        if self.index() < long -1:
            self._index += 1
        else:
            self._index = 0
        return victim

    def __repr__(self):
        return "(" + "LIST VICTIM={list}".format(list=self._listVictim)  + ")"

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

class FileSystem():

    def __init__(self):
        self._disk = Disk()
        self._swapping = Swapping()

    def disk(self):
        return self._disk

    def swapping(self):
        return self._swapping

    def read(self, path):
        return self.disk().getProgram(path)

    def swapIn(self, page, pid, instructions, state):
        if state != 'Finished':
            self.swapping().swapIn(pid,page,instructions)

    def swapOut(self, pid, page):
        return self.swapping().swapOut(pid, page)

    def write(self,path, instructions):
        self._disk.writeProgram(path, instructions)

    def readInstructions(self, path, index, cant):
       return  self.disk().returnInstructions(path, index, cant)

    def clearSwapping(self, pid):
        self.swapping().clear(pid)

class Kernel():

    def __init__(self):
        HARDWARE.mmu.frameSize = 4
        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._tablePCB = PcbTable()
        self._fileSystem = FileSystem()
        self._memoryManager = MemoryManager(HARDWARE.memory,4,TablePage())
        self._loader = Loader(self._memoryManager, self._fileSystem, HARDWARE.memory)
        self._dispatcher = Dispatcher()
        self._scheduler = Scheduler()


        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self._tablePCB, self._scheduler, self._dispatcher,self._memoryManager, self._fileSystem)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        pageFault = PageFaultInterruptionHandler(self._tablePCB, self._scheduler, self._dispatcher, self._memoryManager,
                                             self._fileSystem,self._loader)
        HARDWARE.interruptVector.register(PAGEFAULT, pageFault)

        newHandler = NewInterruptionHandler(self._tablePCB, self._loader, self._scheduler, self._dispatcher,self._memoryManager, self._fileSystem)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        ioInHandler = IoInInterruptionHandler(self._tablePCB, self._scheduler, self._dispatcher,
                                              self._ioDeviceController,self._memoryManager, self._fileSystem)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self._tablePCB, self._scheduler, self._dispatcher,
                                                self._ioDeviceController,self._memoryManager, self._fileSystem)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        timeoutHandler = TimeOutInterruptionHandler(self._tablePCB, self._scheduler, self._dispatcher,self._memoryManager, self._fileSystem)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    def table(self):
        return self._tablePCB

    def scheduler(self):
        return self._scheduler

    def dispatcher(self):
        return self._dispatcher

    def fileSystem(self):
        return self._fileSystem

    def loader(self):
        return self._loader

    def setScheduler(self, _scheduler):
        self._planificador = _scheduler

    def run(self, path, priority=0):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, [path, priority])
        HARDWARE.interruptVector.handle(newIRQ)

    def __repr__(self):
        return "Kernel "
