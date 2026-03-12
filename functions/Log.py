from datetime import datetime
from pathlib import Path


class Log:
    @staticmethod
    def _log_dir() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        log_dir = base_dir / 'LOG'
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @staticmethod
    def _write(filepath: Path, data, type="WARNING"):
        time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        try:
            with filepath.open('a', encoding='utf-8') as file:
                file.write(f'\n{type}: {time}\n{data}')
        except Exception:
            pass

    @staticmethod
    def create(data, code_account='', type="WARNING"):
        date = datetime.now().strftime('%d-%m-%Y')
        filepath = Log._log_dir() / f'LOG_{code_account}_{date}.log'
        Log._write(filepath, data, type)

    @staticmethod
    def createIngreso(data, code_account='', type="WARNING"):
        date = datetime.now().strftime('%d-%m-%Y')
        filepath = Log._log_dir() / f'LOG_Ingreso{code_account}_{date}.log'
        Log._write(filepath, data, type)

    @staticmethod
    def createInventario(data, type="WARNING"):
        date = datetime.now().strftime('%d-%m-%Y')
        filepath = Log._log_dir() / f'LOG_{date}_inventario.log'
        Log._write(filepath, data, type)
