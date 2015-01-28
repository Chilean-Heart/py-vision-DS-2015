import time
from networktables import NetworkTable


table = NetworkTable.getTable("data_table")

def valueChanged(table, key, value, isNew):
    print('Value changed: key %s, isNew: %s: %s' % (key, isNew, value))

table.addTableListener(valueChanged)

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
            table.putBoolean("connection_state", connection)
            ready = table.getBoolean("connection_state")
        except KeyError as err:
            print(err.args)
            error_counter += 1
            time.sleep(0.01)

    if not setup_state:
        setup_state = True


    time.sleep(0.1)
