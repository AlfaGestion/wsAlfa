from datetime import datetime


class Log:
    @staticmethod
    def create(data, code_account='', type="WARNING"):
        time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        date = datetime.now().strftime('%d-%m-%Y')
        try:
            file = open(f'logs/LOG_{code_account}_{date}.log', 'a')
            file.write(f'\n{type}: {time}\n{data}')
            file.close()
        except:
            pass
    @staticmethod
    def createIngreso(data, code_account='', type="WARNING"):
        time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        date = datetime.now().strftime('%d-%m-%Y')
        try:
            file = open(f'logs/LOG_Ingreso{code_account}_{date}.log', 'a')
            file.write(f'\n{type}: {time}\n{data}')
            file.close()
        except:
            pass