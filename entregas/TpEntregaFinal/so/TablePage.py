import sys

from so.Row import *
import log
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
