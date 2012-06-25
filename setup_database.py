# coding: utf-8

import sqlite3
from settings import settings

if __name__ == "__main__":
    database = settings.get("database_name", "data.db")
    connection = sqlite3.connect(database)

    F = open("schema.sql")
    connection.cursor().executescript(F.read())
    F.close()

    connection.commit()
    connection.close()
    print "Database created successfully."
