"""Inicialização do pacote jurimetria.

Registra o PyMySQL como driver MySQLdb para que o backend
``django.db.backends.mysql`` funcione sem a necessidade de compilar o
``mysqlclient`` (que exige bibliotecas do sistema).
"""

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    # PyMySQL não está instalado (ex.: ambiente local usando SQLite).
    pass
