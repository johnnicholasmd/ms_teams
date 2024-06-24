import constants
from langchain.sql_database import SQLDatabase
from function import Function, Property
from dotenv import load_dotenv
from assistant import AIAssistant
from sqlalchemy import create_engine, inspect
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


load_dotenv()

#db connection
connection = f"postgresql://{constants.DB_CONFIG['user']}:{constants.DB_CONFIG['password']}@{constants.DB_CONFIG['host']}:{constants.DB_CONFIG['port']}/{constants.DB_CONFIG['dbname']}?options=-csearch_path=gpt_data"
connection_uri = f"postgresql://{constants.DB_CONFIG['user']}:{constants.DB_CONFIG['password']}@{constants.DB_CONFIG['host']}:{constants.DB_CONFIG['port']}/{constants.DB_CONFIG['dbname']}"
db = SQLDatabase.from_uri(connection_uri,
                          schema='gpt_data',
                          include_tables=['qna','it_qas_data','test_table'])

class GetDBSchema(Function):
    def __init__(self):
        super().__init__(
            name="get_db_schema",
            description="Get the schema of the database",
        )

    def function(self):
        engine = create_engine(connection_uri)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        schema_statements = []

        for table_name in table_names:
            table = inspector.get_columns(table_name)
            create_statement = f"CREATE TABLE {table_name} (\n"
            create_statement += ",\n".join(
                f"{col['name']} {col['type']}" for col in table
            )
            create_statement += "\n);"
            schema_statements.append(create_statement)

        return "\n\n".join(schema_statements)
    
class RunSQLQuery(Function):
    def __init__(self):
        super().__init__(
            name="run_sql_query",
            description="Run a SQL query on the database",
            parameters=[
                Property(
                    name="query",
                    description="The SQL query to run",
                    type="string",
                    required=True,
                ),
            ],
        )

    def function(self, query):
        engine = create_engine(connection_uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            results = session.execute(text(query)).fetchall()
            return '\n'.join([str(result) for result in results])
        except Exception as e:
            return str(e)
        finally:
            session.close()

    
if __name__ == "__main__":
    assistant = AIAssistant(
    instruction="""
You are a SQL expert. User asks you questions about the database.
First obtain the schema of the database to check the tables and columns, then generate SQL queries to answer the questions.
""",
    model="gpt-3.5-turbo-0613",
    functions=[GetDBSchema(), RunSQLQuery()],
    use_code_interpreter=True,
    )
    assistant.chat()