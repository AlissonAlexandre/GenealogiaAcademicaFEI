class Pesquisador:
    def __init__(self, nome, nacionalidade, idLattes='', orientador=[], orientados=[], 
                 instituicaoLotacao='', instituicaoDoutorado='', grandeArea='',area = '',
                 subArea = '', publicacoes=[], imagePath='', tituloDoutorado='', areaDoutorado='', anoDoutorado=0, palavrasChaveDoutorado=[], setor='',indicador_semente=False):
        self.nome = nome
        self.nacionalidade = nacionalidade
        self.idLattes = idLattes
        self.orientador = orientador
        self.orientados = orientados
        self.instituicaoLotacao = instituicaoLotacao
        self.instituicaoDoutorado = instituicaoDoutorado
        self.grandeArea = grandeArea
        self.area = area
        self.subArea = subArea
        self.publicacoes = publicacoes
        self.imagePath = imagePath
        self.tituloDoutorado = tituloDoutorado
        self.areaDoutorado = areaDoutorado
        self.anoDoutorado = anoDoutorado
        self.palavrasChaveDoutorado = palavrasChaveDoutorado
        self.setor = setor
        self.indicador_semente = indicador_semente