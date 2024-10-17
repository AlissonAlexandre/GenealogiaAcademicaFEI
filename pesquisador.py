class Pesquisador:
    def __init__(self, nome, nacionalidade, idLattes='', orientador=[], orientados=[], instituicaoLotacao='', instituicaoDoutorado='', grandeArea='', publicacoes=[], imagePath=''):
        self.nome = nome
        self.nacionalidade = nacionalidade
        self.idLattes = idLattes
        self.orientador = orientador
        self.orientados = orientados
        self.instituicaoLotacao = instituicaoLotacao
        self.instituicaoDoutorado = instituicaoDoutorado
        self.grandeArea = grandeArea
        self.publicacoes = publicacoes
        self.imagePath = imagePath