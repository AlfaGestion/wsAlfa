from datetime import datetime
from configs.connection import get_master_connection, conn
from config import DB_SERVER, SA_PASSWORD, SA_USER, API_ROOT
import subprocess
import os
from functions.Log import Log
SERVER_DEFAULT = DB_SERVER


class DataBase:

    def __init__(self, customer):
        self.customer = customer

    def create(self, server: str = '', dbname: str = '', name: str = '') -> bool:

        now = datetime.now()
        now = now.strftime("%m%d%Y")

        if dbname == '':
            dbname = f"{self.customer.code}_{now}"

        if server == '':
            server = SERVER_DEFAULT

        if name == '':
            name = self.customer.name

        self.name = name
        self.dbname = dbname
        self.server = server

        try:
            connection = get_master_connection()
            cursor = connection.cursor()

            cursor.execute(f"CREATE DATABASE [{dbname}]")

            # Creo las tablas, vistas, stores y funciones
            sql = f"sqlcmd -S {server} -d {dbname} -i {API_ROOT}stores\\db_create.sql -P {SA_PASSWORD} -U {SA_USER} -o {API_ROOT}logs\\{now}_db_create_{dbname}.txt"
            p = subprocess.run(sql)

            # Creo las stores web
            sql = f"sqlcmd -S {server} -d {dbname} -i {API_ROOT}stores\\Stores_alfaweb.sql -P {SA_PASSWORD} -U {SA_USER} -o {API_ROOT}logs\\{now}_db_create_stores_{dbname}.txt"
            p = subprocess.run(sql)

            # Inserto información básica
            cursor.execute(f"""
            USE [{dbname}]

            UPDATE TA_CONFIGURACION SET VALOR='{name}' WHERE CLAVE='NOMBRE'
            UPDATE TA_CONFIGURACION SET VALOR='{self.customer.phone}' WHERE CLAVE='TELEFONO'
            UPDATE TA_CONFIGURACION SET VALOR='{self.customer.email}' WHERE CLAVE='EMAIL_DE'
            UPDATE TA_CONFIGURACION SET VALOR='{self.customer.cuit}' WHERE CLAVE='CUIT'
            UPDATE TA_CONFIGURACION SET VALOR='{self.customer.iva}' WHERE CLAVE='CONDIVA'
            """)

            self.__register_in_db()
        except Exception as e:
            Log.create(e, '', 'ERROR')
            return False

        return True

    def __register_in_db(self):
        cursor = conn.cursor().execute(
            f"""
            INSERT INTO [bases] (idcliente,nombre,dbserver,dbname,dbuser,dbpassword, path)
            VALUES ('{self.customer.code}','{self.name}','{self.server}','{self.dbname}','{SA_USER}','{SA_PASSWORD}','.')
            """)
        conn.commit()

    @staticmethod
    def update(server, dbname, dbuser, dbpassword):
        try:
            stores_sql = os.path.join(API_ROOT, "stores", "Stores_alfaweb.sql")
            command = [
                "sqlcmd",
                "-S", server,
                "-d", dbname,
                "-i", stores_sql,
                "-U", dbuser,
                "-P", dbpassword,
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=False,
            )

            if result.returncode != 0:
                Log.create(
                    (
                        f"ERROR UPDATE DATABASE: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
                        f"BASE: {dbname}\n"
                        f"SERVER: {server}\n"
                        f"DETALLE ERROR: {(result.stderr or result.stdout or 'sqlcmd devolvio un error').strip()}"
                    ),
                    "",
                    "ERROR",
                )
        except Exception as e:
            Log.create(f"{e}")
