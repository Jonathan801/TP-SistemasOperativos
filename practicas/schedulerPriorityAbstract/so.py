#!/usr/bin/env python
import sys

from hardware import *
import log


## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

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

    def __init__(self, pid, db, instructions, path):
        self._pid = pid
        self._baseDir = db
        self._pc = 0
        self._limit = db + instructions - 1
        self._state = "New"
        self._path = path
        self._prioridad = 0

    # ----------------Getters---------------------------------------------------------
    def getPc(self):
        return self._pc

    def getPid(self):
        return self._pid

    def getPath(self):
        return self._path

    def getBaseDir(self):
        return self._baseDir

    def getLimit(self):
        return self._limit

    def getState(self):
        return self._state

    def getPrioridad(self):
        return self._prioridad

    # ----------------Setters----------------------------------------------------------
    def setPrioridad(self, prioridad):
        if prioridad != None:
            self._prioridad = prioridad

    def setPc(self, pc):
        self._pc = pc

    def setState(self, state):
        self._state = state

    def __repr__(self):
        return "(" + "PDI={pdi}".format(pdi=self._pid) + " PC={pc}".format(pc=self._pc) + " BD={db}".format(
            db=self._baseDir) + " STATE={state}".format(state=self._state) + " LIMIT={limit}".format(
            limit=self._limit) + " PATCH={path}".format(path=self._path) + " PRIORIDAD={pri}".format(
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
    def crearPcb(self, program, db):
        self.increasePID()
        pcb = PCB(self._contadorPid, db, len(program._instructions), program.name)
        self.addPcb(pcb, pcb.getPid())
        return pcb

    def increasePID(self):
        self._contadorPid += 1

    def setRunning(self, pcb):
        # self.updeteState(pcb.getPid(),"Running")
        self._running = pcb

    def addPcb(self, pcb, pid):
        self._pcbs[pid] = pcb

    def runningPCB(self, pcb):
        self._running = pcb

    def setPrioridad(self, k, pri):
        self.returnPCB(k).setPrioridad(pri)

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
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            # print(pair)
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

    def __init__(self, tabla, planificador, dispatcher):
        self._planificador = planificador
        self._tablePCB = tabla
        self._dispatcher = dispatcher

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    def table(self):
        return self._tablePCB

    def planificador(self):
        return self._planificador

    def dispatcher(self):
        return self._dispatcher

    """def siEstaVaciaONo(self):
        if self.planificador().readyQueue():
            pcbToAdd = self.planificador().returnNext()
            self.dispatcher().load(pcbToAdd)
            self.table().setRunning(pcbToAdd)
        else:
            HARDWARE.cpu.pc = -1"""

    def esExpropiativoPlanificador(self,pcb):
        if (not self.planificador().esExpropiativo()):
            self.planificador().agregar(pcb)
        else:
            self.enCasoExpropiativo(pcb)

    def enCasoExpropiativo(self,pcb):
        if pcb.getPrioridad() < self.table().returnRunning().getPrioridad():
            self.expropiate(pcb)

    def selectWhereToAdd(self, pcb):
        if self.table().returnRunning() == None:
            self.table().setRunning(pcb)
            self.dispatcher().load(pcb)
            self.table().runningPCB(pcb)
        else:
            self.esExpropiativoPlanificador(pcb)

    def expropiate(self, pcb):
        self.dispatcher().save(self.table().returnRunning())
        self.planificador().agregar(self.table().returnRunning())
        self.dispatcher().load(pcb)
        self.table().runningPCB(pcb)

class KillInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher):
        super(KillInterruptionHandler, self).__init__(tabla, planificador, dispatcher)

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        HARDWARE.cpu.pc = -1
        self.table().returnRunning().setState("Finished")
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        if (self.planificador().noIsEmpty()):
            pcb = self.planificador().returnNext()
            self.dispatcher().load(pcb)
            self.table().runningPCB(pcb)
            log.logger.info("PCB in running" + str(self.table().returnRunning()))
        else:
            HARDWARE.cpu.pc = -1
            self.table().noneRunning()
        log.logger.info("Running PcbTable: " + str(self.table().returnRunning()))



class IoInInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher, ioDevice):
        super(IoInInterruptionHandler, self).__init__(tabla, planificador, dispatcher)
        self._ioDeviceController = ioDevice

    def ioDeviceController(self):
        return self._ioDeviceController

    def execute(self, irq):
        operation = irq.parameters
        self.dispatcher().save(self.table().returnRunning())
        self.ioDeviceController().runOperation(self.table().returnRunning(), operation)
        self.table().noneRunning()
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        log.logger.info("PCB in running " + str(self.table().returnRunning()))
        log.logger.info("queue is empty " + str(self.planificador().noIsEmpty()))
        if self.planificador().noIsEmpty():
            pcb = self.planificador().returnNext()
            self.dispatcher().load(pcb)
            self.table().runningPCB(pcb)
            log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
            log.logger.info("PCB in running" + str(self.table().returnRunning()))
        else:
            HARDWARE.cpu.pc = -1
            log.logger.info("waitin queue" + str(self.ioDeviceController()))
            log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
            log.logger.info("PCB in running" + str(self.table().returnRunning()))

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher, ioDevice):
        super(IoOutInterruptionHandler, self).__init__(tabla, planificador, dispatcher)
        self._ioDeviceController = ioDevice

    def ioDeviceController(self):
        return self._ioDeviceController

    def execute(self, irq):
        pcb = self.ioDeviceController().getFinishedPCB()
        log.logger.info(self.ioDeviceController())
        self.selectWhereToAdd(pcb)
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
        log.logger.info("PCB in running" + str(self.table().returnRunning()))

class NewInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, loader, planificador, dispatcher):
        super(NewInterruptionHandler, self).__init__(tabla, planificador, dispatcher)
        self._loader = loader

    def loader(self):
        return self._loader

    def execute(self, irq):
        program = irq.parameters[0]
        pri = irq.parameters[1]
        pcb = self.table().crearPcb(program, self.loader().getDirBase())
        pcb.setPrioridad(pri)

        self.loader().load(program)
        self.selectWhereToAdd(pcb)
        log.logger.info(HARDWARE.memory)
        log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))

class TimeOutInterruptionHandler(AbstractInterruptionHandler):

    def __init__(self, tabla, planificador, dispatcher):
        super(TimeOutInterruptionHandler, self).__init__(tabla, planificador, dispatcher)

    def execute(self, irq):
        log.logger.info("Entro en timeOut")
        if self.table().returnRunning() == None:
            self.dispatcher().resetQuantum()
        else:
            pcbRunning = self.table().returnRunning()
            self.dispatcher().save(pcbRunning)
            self.planificador().agregar(pcbRunning)
            log.logger.info("ReadyQueue" + str(self.planificador().readyQueue()))
            self.siEstaVaciaONo()

    def siEstaVaciaONo(self):
        if self.planificador().readyQueue():
            pcbToAdd = self.planificador().returnNext()
            self.dispatcher().load(pcbToAdd)
            self.table().setRunning(pcbToAdd)
        else:
            HARDWARE.cpu.pc = -1
            self.dispatcher().resetQuantum()


class Loader():

    def __init__(self):
        self._dirBase = 0
        self._nextCell = 0

    def getNextCell(self):
        return self._nextCell

    def getDirBase(self):
        return self._dirBase

    def load(self, program):
        progSize = len(program.instructions)
        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.put(index + self.getDirBase(), inst)
            self._nextCell += 1
        self._dirBase += progSize

class Dispatcher():

    def load(self, pcb):
        value1 = pcb.getBaseDir()
        value2 = pcb.getPc()
        HARDWARE.mmu.baseDir = value1
        HARDWARE.cpu.pc = value2
        self.resetQuantum()

    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu.pc)
        pcb.setState("Waiting")
        HARDWARE.cpu.pc = -1

    def resetQuantum(self):
        HARDWARE.timer.reset()

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

# emulates the core of an Operative System
class Kernel():

    def __init__(self, ):
        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._tablePCB = PcbTable()
        self._loader = Loader()
        self._dispatcher = Dispatcher()
        #self._planificador = PlanificadorPrioridad(3, True)
        self._planificador = PlanificadorRR(2)
        #self._planificador = PlanificadorRRPrioridad(3, True,2)

        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        newHandler = NewInterruptionHandler(self._tablePCB, self._loader, self._planificador, self._dispatcher)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        ioInHandler = IoInInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher,
                                              self._ioDeviceController)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher,
                                                self._ioDeviceController)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        timeoutHandler = TimeOutInterruptionHandler(self._tablePCB, self._planificador, self._dispatcher)
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

    def loader(self):
        return self._loader

    def setPlanificador(self, _planificador):
        self._planificador = _planificador

    def run(self, program, priority=0):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, [program, priority])
        HARDWARE.interruptVector.handle(newIRQ)

    def __repr__(self):
        return "Kernel "
