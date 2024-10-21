from neo4j import GraphDatabase
from dotenv import load_dotenv, dotenv_values 
import os
load_dotenv()

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
driver = GraphDatabase.driver(URI, auth=AUTH)

try:
    driver.verify_connectivity()
    print("Conectado ao banco de dados com sucesso!")
except:
    print("Erro ao conectar ao banco de dados")

def create_pesquisador(tx, pesquisador):
    query = """
    MERGE (p:Pesquisador {idLattes: $idLattes})
    SET p.nome = $nome,
        p.nacionalidade = $nacionalidade,
        p.instituicaoLotacao = $instituicaoLotacao,
        p.instituicaoDoutorado = $instituicaoDoutorado,
        p.grandeArea = $grandeArea,
        p.area = $area,
        p.subArea = $subArea,
        p.imagePath = $imagePath,
        p.tituloDoutorado = $tituloDoutorado,
        p.areaDoutorado = $areaDoutorado,
        p.anoDoutorado = $anoDoutorado,
        p.palavrasChaveDoutorado = $palavrasChaveDoutorado
    """
    tx.run(query, 
           idLattes=pesquisador.idLattes.strip(),
           nome=pesquisador.nome,
           nacionalidade=pesquisador.nacionalidade,
           instituicaoLotacao=pesquisador.instituicaoLotacao,
           instituicaoDoutorado=pesquisador.instituicaoDoutorado,
           grandeArea=pesquisador.grandeArea,
           area=pesquisador.area,
           subArea=pesquisador.subArea,
           imagePath=pesquisador.imagePath,
           tituloDoutorado=pesquisador.tituloDoutorado,
           areaDoutorado=pesquisador.areaDoutorado,
           anoDoutorado=pesquisador.anoDoutorado,
           palavrasChaveDoutorado=pesquisador.palavrasChaveDoutorado)
    print("Inseriu pesquisador: ", pesquisador.nome)

def insere_publicacoes(tx, pesquisador):
    for publicacao in pesquisador.publicacoes:
        query = """
        MATCH (p:Pesquisador {idLattes: $idLattes})
        MERGE (pub:Publicacao {titulo: $titulo})
        MERGE (p)-[:PUBLICOU]->(pub)
        """
        tx.run(query, idLattes=pesquisador.idLattes.strip(), titulo=publicacao)

def cria_relacoes(tx, pesquisador):
    for orientado in pesquisador.orientados:
        query = """
        MATCH (p:Pesquisador {idLattes: $idLattes})
        MATCH (o:Pesquisador {idLattes: $orientado})
        MERGE (p)-[:ORIENTOU]->(o)
        """
        tx.run(query, idLattes=pesquisador.idLattes.strip(), orientado=orientado)
    if pesquisador.orientador:
        query = """
        MATCH (p:Pesquisador {idLattes: $idLattes})
        MATCH (o:Pesquisador {idLattes: $orientador})
        MERGE (o)-[:ORIENTOU]->(p)
        """
        tx.run(query, idLattes=pesquisador.idLattes.strip(), orientador=pesquisador.orientador.idLattes)

def insert_relacoes(pesquisador):
    with driver.session() as session:
        #session.write_transaction(insere_publicacoes, pesquisador)
        session.write_transaction(cria_relacoes, pesquisador)

def insert_pesquisador(pesquisador):
    with driver.session() as session:
        session.write_transaction(create_pesquisador, pesquisador)
        indexes = [
       "CREATE INDEX IF NOT EXISTS FOR (p:Pesquisador) ON (p.idLattes)",
       "CREATE INDEX IF NOT EXISTS FOR (p:Pesquisador) ON (p.nome)"
        ]
        for index in indexes:
            session.run(index)