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
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)

class PCB():

    def __init__(self, pid, db, path, pri):
        self._pid = pid
        self._baseDir = db
        self._pc = 0
        self._state = "New"
        self._path = path
        self._prioridad = pri

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

    def getPrioridad(self):
        return self._prioridad

    # ----------------Setters----------------------------------------------------------

    def setPc(self, pc):
        self._pc = pc

    def setState(self, state):
        self._state = state

    def __repr__(self):
        return "(" + "PDI={pdi}".format(pdi=self._pid) + " PC={pc}".format(pc=self._pc) + " BD={db}".format(
            db=self._baseDir) + " STATE={state}".format(state=self._state)  + " PATCH={path}".format(path=self._path) + " PRIORIDAD={pri}".format(
            pri=self._prioridad) + ")"

class PcbTable():

    def __init__(self):
        self._pcbs = dict()
        self._running = None
        self._contadorPid = 0

    # ----------------------- Getters ------------------------------------------------
    def returnPCB(self, k):
        return self._pcbs.get(k)

    def updetePC(self, k, pc):
        self.returnPCB(k).setPc(pc)

    def returnRunning(self):
        return self._running

    def updeteState(self, k, state):
        self.returnPCB(k).setState(state)

    # ----------------------- Setters ------------------------------------------------
    def crearPcb(self, path , db, pri):
        self.increasePID()
        pcb = PCB(self._contadorPid, db, path, pri)
        self.addPcb(pcb)
        return pcb

    def increasePID(self):
        self._contadorPid += 1

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

    def __init__(self, tabla, planificador, dispatcher, memoryMannger, fileSystem):
        self._planificador = planificador
        self._tablePCB = tabla
        self._dispatcher = dispatcher
        self._memoryMannger = memoryMannger
        self._fileSystem = fileSystem

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    def table(self):
        return self._tablePCB

    def planificador(self):
        return self._planificador

    def memoryMannger(self):
        return self._memoryMannger

    def dispatcher(self):
        return self._dispatcher

    def fileSystem(self):
        return self._fileSystem

    def selectWhereToAdd(self, pcb):
        pageOfPCB = self.memoryMannger().pageTable().returnRowsOfPID(pcb.getPid())
        if self.table().returnRunning() == None:
            self.table().setRunning(pcb)
            self.dispatcher().load(pcb,pageOfPCB)
            self.table().runningPCB(pcb)
        else:
            self.esExpropiativoPlanificador(pcb,pageOfPCB)


    def esExpropiativoPlanificador(self,pcb,pageOfPCB):
        if self.planificador().esExpropiativo():
            self.enCasoExpropiativo(pcb,pageOfPCB)
        else:
            self.planificador().agregar(pcb)

    def enCasoExpropiativo(self, pcb,pageOfPCB):
        if pcb.getPrioridad() < self.table().returnRunning().getPrioridad():
            self.expropiate(pcb,pageOfPCB)
        else:
            self.planificador().agregar(pcb)

    def expropiate(self, pcb,pageOfPCB):
        self.dispatcher().save(self.table().returnRunning())
        self.planificador().agregar(self.table().returnRunning())
        self.dispatcher().load(pcb,pageOfPCB)
        self.table().runningPCB(pcb)

class KillInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher, memoryMannger,fileSystem):
        super(KillInterruptionHandler, self).__init__(tabla, planificador, dispatcher, memoryMannger, fileSystem)

    def saveFrames(self):
        frames = self.memoryMannger().pageTable().returnRowsOfPID(self.table().returnRunning().getPid())
        framesFree = []
        for index in frames:
            framesFree.append(index.frame())
        self.memoryMannger().addFrames(framesFree)

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        HARDWARE.cpu.pc = -1
        self.table().returnRunning().setState("Finished")
        self.saveFrames()
        log.logger.info("FreeFrames: "+ str(self.memoryMannger().freeFrames()))
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        if self.planificador().noIsEmpty():
            pcb = self.planificador().returnNext()
            pageOfPCB = self.memoryMannger().pageTable().returnRowsOfPID(pcb.getPid())
            self.dispatcher().load(pcb, pageOfPCB)
            self.table().runningPCB(pcb)
            log.logger.info("PCB in running" + str(self.table().returnRunning()))
        else:
            self.table().noneRunning()
        log.logger.info("Running PcbTable: " + str(self.table().returnRunning()))

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher, ioDevice, memoryMananger,fileSystem):
        super(IoInInterruptionHandler, self).__init__(tabla, planificador, dispatcher,memoryMananger,fileSystem)
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
        if self.planificador().noIsEmpty():
            pcb = self.planificador().returnNext()
            pageOfPCB = self.memoryMannger().pageTable().returnRowsOfPID(pcb.getPid())
            self.dispatcher().load(pcb, pageOfPCB)
            self.table().runningPCB(pcb)
            log.logger.info("waitin queue" + str(self.ioDeviceController()))
            log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        else:
            HARDWARE.cpu.pc = -1
            log.logger.info("waitin queue" + str(self.ioDeviceController()))
            log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher, ioDevice,memoryMananger,fileSystem):
        super(IoOutInterruptionHandler, self).__init__(tabla, planificador, dispatcher,memoryMananger,fileSystem)
        self._ioDeviceController = ioDevice

    def ioDeviceController(self):
        return self._ioDeviceController

    def execute(self, irq):
        log.logger.info(" Program Out")
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        log.logger.info("PCB in Running : " + str(self.table().returnRunning()))
        pcb = self.ioDeviceController().getFinishedPCB()
        log.logger.info(self.ioDeviceController())
        self.selectWhereToAdd(pcb)

class NewInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, loader, planificador, dispatcher ,memoryManger,fileSystem):
        super(NewInterruptionHandler, self).__init__(tabla, planificador, dispatcher, memoryManger,fileSystem)
        self._loader = loader

    def loader(self):
        return self._loader

    def execute(self, irq):
        log.logger.info(" New PCB ")
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        path = irq.parameters[0]
        pri = irq.parameters[1]

        pcb = self.table().crearPcb(self.loader().getDirBase(), path, pri)

        self.loader().load(path, pcb.getPid())
        self.selectWhereToAdd(pcb)
        log.logger.info(HARDWARE.memory)
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        log.logger.info("PCB in running " + str(self.table().returnRunning()))

class TimeOutInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher,memoryMananger,fileSystem):
        super(TimeOutInterruptionHandler, self).__init__(tabla, planificador, dispatcher,memoryMananger,fileSystem)

    def execute(self, irq):
        log.logger.info("Entro en TimeOut ")
        if self.planificador().noIsEmpty():
            self.changePCB()
        else:
            self.resetQuantum()
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))

    def resetQuantum(self):
        HARDWARE.timer.reset()

    def changePCB(self):
        pcb = self.planificador().returnNext()
        self.dispatcher().save(self.table().returnRunning())
        self.planificador().agregar(self.table().returnRunning())
        pageOfPCB = self.memoryMannger().pageTable().returnRowsOfPID(pcb.getPid())
        self.dispatcher().load(pcb, pageOfPCB)
        self.table().setRunning(pcb)
        self.resetQuantum()

class PageFault(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher,memoryMananger,fileSystem):
        super(PageFault, self).__init__(tabla, planificador, dispatcher,memoryMananger,fileSystem)

    def execute(self, irq):
        log.logger.info("PCB in running " + str(self.table().returnRunning()))



class Loader():

    def __init__(self, memoryManager, fileSystem):
        self._memoryManager = memoryManager
        self._dirBase = 0
        self._nextCell = 0
        self._fileSystem = fileSystem

    def getNextCell(self):
        return self._nextCell

    def getDirBase(self):
        return self._dirBase
    def fileSystem(self):
        return self._fileSystem

    def memoryManager(self):
        return self._memoryManager

    def cuantasPaginasNecesito(self, program):
        progSize = len(program.instructions)
        return progSize//self.memoryManager().frameSize() + self.necesitoUnoMas(program)

    def necesitoUnoMas(self, program):
        progSize = len(program.instructions)
        if progSize % self.memoryManager().frameSize() > 0:
            return 1
        else:
            return 0

    def loadProgram(self, program, frames, pid):
        var = 0
        log.logger.info("Allow frames: " + str(frames))
        log.logger.info("FreFrames: " + str(self._memoryManager.freeFrames()))
        frame = frames.pop(0)
        frameForPage = frame
        page = 0

        self.memoryManager().pageTable().addRow(pid, page, frameForPage)
        for index in range(0, len(program.instructions)):
            if var < self.memoryManager().frameSize():
                var += 1
            else:
                page += 1
                var = 0
                log.logger.info("Frames en frames : " + str(frames))
                log.logger.info("Cantidad de instrucciones : " + str(len(program.instructions)))
                frame = frames.pop(0)
                frameForPage = frame
                self.memoryManager().pageTable().addRow(pid, page, frameForPage)
            inst = program.instructions[index]
            self.memoryManager().getMemory().put((frame * self.memoryManager().frameSize()) + (var-1), inst)

        log.logger.info("TablePage: " + str(self.memoryManager().pageTable()))

    def load(self, path, pid):
        log.logger.info("FreFrames: " + str(self._memoryManager.freeFrames()))
        program = self.fileSystem().read(path)
        frames = self.memoryManager().allocFrames(self.cuantasPaginasNecesito(program))
        if len(frames) > 0:
            self.loadProgram(program, frames, pid)

class Dispatcher():

    def load(self, pcb, pageTableOfPCB):
        HARDWARE.mmu.resetTLB()
        for page in pageTableOfPCB :
            HARDWARE.mmu.setPageFrame(page.page(), page.frame())
        #value1 = pcb.getBaseDir()
        value2 = pcb.getPc()
        #HARDWARE.mmu.baseDir = value1
        HARDWARE.cpu.pc = value2

    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu.pc)
        pcb.setState("Waiting")
        HARDWARE.cpu.pc = -1

class Nivel():

    def __init__(self):
        self._list = []
        for i in range(0, 3):
            self._list.append([])

    def nivel(self):
        return self._list

    def addPCB(self, pcb):
        self.nivel()[len(self.nivel()) - 1].append(pcb)

    def elemNivel(self):
        res = 0
        for i in self.nivel():
            res += len(i)
        return res

    def returnFirstList(self):
        return self.nivel()[0]

    def clearFirstList(self):
        self.nivel()[0].clear()

    def addList(self, list):
        self.nivel()[len(self.nivel()) - 1].extend(list)

    def getOlderNivel(self):
        for i in range(0, len(self.nivel()) - 1):
            self.nivel()[i].extend(self.nivel()[i + 1])
            self.nivel()[i + 1].clear()

    def returnPop(self):
        for index in self.nivel():
            if len(index) > 0:
                return index.pop(0)

    def __repr__(self):
        return "(Nivel = {queue})".format(queue=self.nivel())

class Planificador():

    def __init__(self):
        self._queue = []
        self._expropiar = False

    def readyQueue(self):
        return self._queue

    def returnNext(self):
        return self.readyQueue().pop(0)

    def esExpropiativo(self):
        return self._expropiar

    def agregar(self, pcb):
        self.readyQueue().append(pcb)

    def noIsEmpty(self):
        return len(self.readyQueue()) > 0

    def __repr__(self):
        return "(ReadyQueue = {queue})".format(queue=self.readyQueue())

class PlanificadorPrioridad(Planificador):

    def __init__(self, niveles, esExpropiativo):
        super(PlanificadorPrioridad, self).__init__()
        self._expropiar = esExpropiativo
        for i in range(0, niveles):
            self._queue.append(Nivel())

    def envejecer(self):
        for index in range(1, len(self.readyQueue())):
            self.readyQueue()[index].getOlderNivel()
            if index < len(self.readyQueue()) - 1:
                self.readyQueue()[index].addList(self.readyQueue()[index + 1].returnFirstList())
                self.readyQueue()[index + 1].clearFirstList()

    def agregar(self, pcb):
        self.readyQueue()[pcb.getPrioridad()].addPCB(pcb)

    def noIsEmpty(self):
        var = 0
        for index in self.readyQueue():
            var += index.elemNivel()
        return var > 0

    def returnNext(self):
        for index in self.readyQueue():
            if index.elemNivel() > 0:
                pcbReturn = index.returnPop()
                self.envejecer()
                return pcbReturn

class PlanificadorRRPrioridad(PlanificadorPrioridad):

    def __init__(self, niveles, esExpropiativo, quantum):
        super(PlanificadorPrioridad, self).__init__()
        self._expropiar = esExpropiativo
        HARDWARE.timer.quantum = quantum
        for i in range(0, niveles):
            self._queue.append(Nivel())

class PlanificadorRR(Planificador):

    def __init__(self, quantum):
        super(PlanificadorRR, self).__init__()
        HARDWARE.timer.quantum = quantum

class Row():
    def __init__(self, pid, page, frame):
        self._pid = pid
        self._page = page
        self._frame = frame

    def pid(self):
        return self._pid

    def page(self):
        return self._page

    def frame(self):
        return self._frame

    def __repr__(self):
        return "(" + "PDI={pdi}".format(pdi=self._pid) + " PAGE={page}".format(page=self._page) + " FRAME={frame}".format(
            frame=self._frame)+ ")"

class TablePage():

    def __init__(self):
        self._queuePage = []

    def addRow(self, pid, page, frame):
        self._queuePage.append(Row(pid, page, frame))

    def returnRowsOfPID(self, pid):
        res = []
        for elem in self._queuePage:
            if elem.pid() == pid:
                res.append(elem)

        return res

    def __repr__(self):
        return "(" + "TABLEPAGE ={table}".format(table=self._queuePage) + ")"

class MemoryMannger():

    def __init__(self, memory, frameSize, tablePage):
        self._memory = memory
        self._pageTable = tablePage
        self._frameSize = frameSize
        self._freeFrames = []
        for index in range(0, (memory.getSize() // frameSize)):
           self._freeFrames.append(index)
        #log.logger.info("FreFrames: " + str(self._freeFrames))

    def frameSize(self):
        return self._frameSize

    def getMemory(self):
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

class FileSystem():

    def __init__(self):
        self._disk = Disk()

    def write(self,path, instructions):  ##cambiar program por instrucciones
        self._disk.writeProgram(path, instructions)

    def read(self, patch):
        return self._disk.getProgram(patch)

class Kernel():

    def __init__(self):
        HARDWARE.mmu.frameSize = 4
        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._tablePCB = PcbTable()
        self._fileSystem = FileSystem()
        self._memoryMannger = MemoryMannger(HARDWARE.memory,4,TablePage())
        self._loader = Loader(self._memoryMannger, self._fileSystem)
        self._dispatcher = Dispatcher()

        #self._planificador = PlanificadorPrioridad(3, True)
        self._planificador = PlanificadorRR(2)
        #self._planificador = PlanificadorRRPrioridad(3, True, 2)

        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher,self._memoryMannger, self._fileSystem)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        newHandler = NewInterruptionHandler(self._tablePCB, self._loader, self._planificador, self._dispatcher,self._memoryMannger, self._fileSystem)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        ioInHandler = IoInInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher,
                                              self._ioDeviceController,self._memoryMannger, self._fileSystem)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher,
                                                self._ioDeviceController,self._memoryMannger, self._fileSystem)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        timeoutHandler = TimeOutInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher,self._memoryMannger, self._fileSystem)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    def table(self):
        return self._tablePCB

    def planificador(self):
        return self._planificador

    def dispatcher(self):
        return self._dispatcher

    def fileSystem(self):
        return self._fileSystem

    def loader(self):
        return self._loader

    def setPlanificador(self, _planificador):
        self._planificador = _planificador

    def run(self, path, priority=0):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, [path, priority])
        HARDWARE.interruptVector.handle(newIRQ)

    def __repr__(self):
        return "Kernel "
