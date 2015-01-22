import time
from pynetworktables import *

SmartDashboard.init()

table = NetworkTable.GetTable("data_table")

class Listener(ITableListener):
    a = 50
    def __init__(self):
        ITableListener.__init__(self)

    def ValueChanged(self, table, key, value, isNew):
        print('Value changed: key %s, isNew: %s: %s' % (key, isNew, table.GetValue(key)))

listener = Listener()

table.AddTableListener(listener)

ready = False
setup_state = False
connection = True
error_counter = 0

while True:
    while not ready:
        if error_counter > 10:
            print("Error count exceeded. Exiting")
            exit(0)
        try:
            table.PutBoolean("connection_state", connection)
            ready = table.GetBoolean("connection_state")
        except TableKeyNotDefinedException as err:
            print(err.args)
            error_counter += 1
            time.sleep(0.01)

    if not setup_state:
        setup_state = True


    time.sleep(0.1)