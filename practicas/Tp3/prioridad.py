from hardware import HARDWARE


class PCB():

    def __init__(self, pid, db, instructions, path):
        self._pid = pid
        self._baseDir = db
        self._pc = 0
        self._limit = db + instructions -1
        self._state = "New"
        self._path = path
        self._prioridad = None

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
        self._prioridad = prioridad

    def setPc(self, pc):
        self._pc = pc

    def setState(self, state):
        self._state = state

    def __repr__(self):
        return "("+"PDI={pdi}".format(pdi=self._pid)+" PC={pc}".format(pc=self._pc)+" BD={db}".format(
            db=self._baseDir)+" STATE={state}".format(state=self._state)+" LIMIT={limit}".format(
            limit=self._limit) + " PATCH={path}".format(path=self._path) + " PRIORIDAD={pri}".format(pri=self._prioridad)+")"

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

    def updetePrioridad(self, k, prioridad):
        self.returnPCB(k).setPrioridad(prioridad)

    # ----------------------- Setters ------------------------------------------------
    def setRunning(self, pcb):
        self._running = pcb

    def agregarPcb(self, pcb, pid):
        self._pcbs[pid] = pcb

    def crearPcb(self, db, instructions, path):
        pcb = PCB(self._contadorPid,db,instructions,path)
        self._contadorPid+=1
        return pcb

    def __repr__(self):
        return "("+"TABLE ={table}".format(table=self._pcbs)+")"

class Prioridad():

    def __init__(self, dispacher, niveles):
        self._dispacher = dispacher
        self._queue = []
        for i in range(0, niveles):
            self._queue.append(Nivel())

    def readyQueue(self):
        return self._queue

    def dispacher(self):
        return self._dispacher

    def addNewPCB(self, pcb):
        self.agregar(pcb)

    def agregar(self, pcb):
        self.readyQueue()[pcb.getPrioridad()].addPCB(pcb)

    def agregarListas(self, x, ys):
        self.readyQueue()[x].addList(ys)

    def envejecer(self):
        for index in range(0, len(self.readyQueue())):
            self.readyQueue()[index].getOlderNivel()
            if index < len(self.readyQueue())-1:
                self.agregarListas(index, self.readyQueue()[index+1].returnFirstList())
                self.readyQueue()[index + 1].clearFirstList()

    def returnNext(self):
        for index in self.readyQueue():
           if index.elemNivel() > 0:
               return index.returnPop()


    def __repr__(self):
        return "(ReadyQueue = {queue})".format(queue=self.readyQueue())

class Nivel():

    def __init__(self):
        self._list = []
        for i in range(0, 3):
            self._list.append([])

    def nivel(self):
        return self._list

    def addPCB(self, pcb):
        self.nivel()[len(self.nivel())-1].append(pcb)

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
        self.nivel()[len(self.nivel())-1].extend(list)

    def getOlderNivel(self):
        for i in range(0, len(self.nivel()) -1):
            self.nivel()[i].extend(self.nivel()[i+1])
            self.nivel()[i+1].clear()

    def returnPop(self):
        for index in self.nivel():
            if len(index)>0:
                return index.pop()

    def __repr__(self):
        return "(Nivel = {queue})".format(queue=self.nivel())

class Dispatcher():

    def load(self, pcb):
        value1 = pcb.getBaseDir()
        value2 = pcb.getPc()
        HARDWARE.mmu.baseDir = value1
        HARDWARE.cpu.pc = value2

    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu.pc)
        pcb.setState("Waiting")
        HARDWARE.cpu.pc = -1

# -------------------------------------------------------------------------------------------------------------

uno = PCB(0,10,8,"uno")
dos = PCB(0,10,8,"dos")
dos.setPrioridad(0)
cinco= PCB(3,10,8,"cinco")
cinco.setPrioridad(0)
cuatro= PCB(2,10,8,"cuatro")
cuatro.setPrioridad(2)
tres= PCB(1,10,8,"tres")
tres.setPrioridad(1)
seis= PCB(3,10,8,"seis")
seis.setPrioridad(1)
siete= PCB(3,10,8,"siete")
siete.setPrioridad(2)

dispacher = Dispatcher()
planif = Prioridad(dispacher, 3)
print(planif)
print(planif.returnNext())
planif.agregar(tres)
print(planif)
planif.agregar(dos)
planif.agregar(cuatro)
print(planif)

print(planif.returnNext())
planif.envejecer()
print(planif)
print(planif.returnNext())
planif.envejecer()
print(planif)
planif.agregar(cinco)
print(planif)
print(planif.returnNext())
planif.envejecer()
print(planif)
planif.envejecer()
print(planif)
planif.envejecer()
print(planif)
planif.envejecer()
print(planif)
planif.envejecer()
print(planif)

planif.agregar(seis)
planif.agregar(siete)
planif.envejecer()
print(planif)

