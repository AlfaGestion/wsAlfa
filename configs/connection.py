import pyodbc

from config import DB_SERVER, DB_NAME, DB_PASS, DB_USER, DB_VERSION, SA_PASSWORD, SA_USER

try:
    conn = pyodbc.connect('Driver={SQL Server Native Client '+DB_VERSION+'};Server='+DB_SERVER+';Database=' +
                          DB_NAME+';uid='+DB_USER+';pwd='+DB_PASS+';MARS_Connection=Yes')
except Exception as e:
    print("Ocurrió un error al conectar a SQL Server : ", e)
    conn = ''


def get_master_connection():
    try:
        master_conn = pyodbc.connect('Driver={SQL Server Native Client '+DB_VERSION+'};Server='+DB_SERVER +
                                     ';Database=master;uid='+SA_USER+';pwd='+SA_PASSWORD+';', autocommit=True)
    except Exception as e:
        print("Ocurrió un error al conectar a SQL Server (Master): ", e)
        master_conn = ''

    return master_conn
