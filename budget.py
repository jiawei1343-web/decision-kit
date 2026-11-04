"""Atomic fixed-ceiling reservations. Unknown charges stay reserved."""
import math
import sqlite3
import uuid

def units(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
        raise ValueError('cost must be finite and nonnegative')
    return math.ceil(value*1000000)

class Budget:
    def __init__(self, path):
        self.db=sqlite3.connect(path,timeout=10)
        self.db.execute('CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, project TEXT, amount INTEGER, state TEXT)')
    def reserve(self, project, ceiling, limit):
        amount,maximum=units(ceiling),units(limit)
        if not isinstance(project,str) or not project.strip(): raise ValueError('project required')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            total=self.db.execute('SELECT COALESCE(SUM(amount),0) FROM reservations WHERE project=?',(project,)).fetchone()[0]
            if total+amount>maximum: return None
            token=uuid.uuid4().hex
            self.db.execute('INSERT INTO reservations VALUES (?,?,?,?)',(token,project,amount,'reserved'))
        return token
    def settle(self, token, actual):
        amount=units(actual)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row=self.db.execute('SELECT state FROM reservations WHERE id=?',(token,)).fetchone()
            if not row or row[0]!='reserved': raise ValueError('reservation unavailable')
            self.db.execute('UPDATE reservations SET amount=?,state=? WHERE id=?',(amount,'settled',token))
    def summary(self, project):
        return {state:amount/1000000 for state,amount in self.db.execute('SELECT state,SUM(amount) FROM reservations WHERE project=? GROUP BY state',(project,))}
    def close(self): self.db.close()
