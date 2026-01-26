from functions.general import get_format_response
from functions.responses import set_response
from configs.connection import conn
from functions.DataBase import DataBase
from datetime import datetime


def get_dbases(account: str) -> list:
    """
    Retorna las bases del cliente
    """
    result = []

    sql = f"""
    SELECT id,nombre,dbname FROM bases where idcliente='{account}'
    """
    result, _ = get_format_response(sql, " las bases del cliente", True)
    return result


def set_db(account: str, id: int, token: str):
    """
    Establece una base de datos en la sesión
    """

    try:
        db_info = get_db_info(id)[0]
        # print(db_info)
    except Exception as e:
        print(f"Ocurrió un error al obtener los datos de la base")
        db_info = {}

    sql = f"""
    UPDATE sessions SET dbname='{db_info['dbname']}',dbuser='{db_info['dbuser']}',
    dbpassword='{db_info['dbpassword']}',dbserver='{db_info['dbserver']}', 
    company_name='{db_info['nombre']}',path='{db_info['path']}'
    WHERE idcliente='{account}' AND token='{token.replace(".","")}'
    """

    try:
        conn.cursor().execute(sql)
        conn.commit()

        # Verifico si tengo que actualizar la base de datos, lo hago cada 1 hora.
        update_database = False
        last_update = db_info['last_update']
        if last_update == None or last_update == '':
            update_database = True
        else:
            now = datetime.now()
            dif = now - last_update

            if dif.total_seconds() / 60 > 180:
                update_database = True

        # Actualizo la base de datos
        if update_database:
            DataBase.update(db_info['dbserver'], db_info['dbname'], db_info['dbuser'], db_info['dbpassword'])
            set_last_update_db(id)

        return True
    except Exception as e:
        print(f"Ocurrió un error al setear la base: ", e)
        return False


def set_last_update_db(database_id: int):

    now = datetime.now()
    now = now.strftime("%d-%m-%Y %H:%M:%S")

    sql = f"UPDATE bases SET last_update='{now}' WHERE id={database_id}"

    try:
        conn.cursor().execute(sql)
        conn.commit()
    except Exception as e:
        print(f"Ocurrió un error al actualizar la fecha de ultima actualizacion de la base: ", e)


def get_db_info(id: int):
    """
    Retorna la información de una base de datos especifica
    """
    sql = f"""
    SELECT id,nombre,dbserver,dbname,dbuser,dbpassword,path,last_update 
    FROM bases where id={id}
    """
    result, _ = get_format_response(sql, " las base del cliente", True)
    return result


def get_info_session(token: str):
    """
    Retorna la información de una sesión
    """

    result = []

    sql = f"""
    SELECT id,idcliente,dbname,dbuser,dbpassword,dbserver,nombre, company_name,isnull(path,'') as path 
    FROM sessions WHERE token='{token.replace(".","")}'
    """

    result, _ = get_format_response(sql, " la información de la sesión", True)

    return result
