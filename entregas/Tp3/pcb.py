class PCB():

    def __init__(self, pid, db, instructions, path):
        self._pid = pid
        self._baseDir = db
        self._pc = -1
        self._limit = db + instructions
        self._state = "New"
        self._path = path

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

    # ----------------Setters----------------------------------------------------------
    def setPc(self, pc):
        self._pc = pc

    def setState(self, state):
        self._state = state

    def __repr__(self):
        return "("+"PDI={pdi}".format(pdi=self._pid)+" PC={pc}".format(pc=self._pc)+" BD={db}".format(
            db=self._baseDir)+" STATE={state}".format(state=self._state)+" LIMIT={limit}".format(
            limit=self._limit) + " PATCH={path}".format(path=self._path)+")"

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

    def returnValores(self):
        return self._pcbs.values()

    def returnKeys(self):
        return self._pcbs.keys()

    def returnRunning(self):
        return self._running

    def updeteState(self, k, state):
        self.returnPCB(k).setState(state)

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
# # -------------------------------------------------------------------------------------------------
"""""
print("Creo los PCB de prueba:")
mas = PCB(0,10,5,"prg1")
print(mas)
maxx = PCB(1,16,4,"prog2")
print(maxx)
table = PcbTable()
print("Table recien creada")
print(table)
print("RUNNING en el estado inicial de la table: ")
print(table.returnRunning())
table.agregarPcb(mas,mas.getPid())
table.agregarPcb(maxx, maxx.getPid())
table.updeteState(0, "Runing")
table.updetePC(0, 10)
table.setRunning(mas)
print("Table con PCBS agregados:")
print(table)
print("RUNNING:")
print(table.returnRunning())

## -----------------------------------------------------------------------
print("Creo los PCB de prueba:")
table = PcbTable()
mas = table.crearPcb(10,5,"prg1")
print(mas)
maxx = table.crearPcb(16,4,"prog2")
print(maxx)
##print("Table recien creada")
##print(table)
print("RUNNING en el estado inicial de la table: ")
print(table.returnRunning())
table.agregarPcb(mas,mas.getPid())
table.agregarPcb(maxx, maxx.getPid())
table.updeteState(0, "Runing")
table.updetePC(0, 5)
table.updetePC(1, 8)
table.setRunning(mas)
print("Table con PCBS agregados:")
print(table)
print("RUNNING:")
print(table.returnRunning())"""

unaLista = []
if unaLista:
    print(6)
else:
    print(8)
