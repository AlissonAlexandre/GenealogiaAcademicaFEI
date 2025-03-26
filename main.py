from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
import urllib.parse
import time
from dotenv import load_dotenv, dotenv_values 
import re
import os
from pesquisador import Pesquisador
from bs4 import BeautifulSoup
from database import insert_pesquisador, insert_relacoes
from logger_util import get_logger

logger = get_logger()

def handle_route_block_script(route, request):
    # NOTE: Necessário bloquear tags de script para capturar HTML original do lattes, já que se caso os scripts executem, todos os links de orientador/orientado são removidos
    if request.resource_type == "script":
        route.abort()
    else:
        route.continue_()

def handle_route_block_nothing(route, request):
    route.continue_()

def checaDataParam(elementos):
    pattern = re.compile(r".*nivelCurso=D.*")
    
    if pattern.match(elementos.get_attribute('data-param')):
        return elementos
    return None

def getParametrosDoutorado(page):
    elementosAcademicos = page.locator(f'.layout-cell-pad-5')

    index = 0
    for i in range(elementosAcademicos.count()):
        if elementosAcademicos.nth(i).locator('span.ajaxCAPES').count() > 0:
            elemento = checaDataParam(elementosAcademicos.nth(i).locator('span.ajaxCAPES'))
            if(elemento != None):
                index = i
                break
    
    objetoParamDoutorado = elementosAcademicos.nth(index)
    page.set_default_timeout(1000)

    try:
        anoDoutorado = objetoParamDoutorado.locator("..").locator("..").locator("..").locator(".layout-cell-12").locator(".layout-cell-pad-5").first.inner_text()
    except Exception:
        anoDoutorado = ''

    lista = objetoParamDoutorado.text_content().replace("\t",'')
    try:
        orientadorId = objetoParamDoutorado.locator('a.icone-lattes').get_attribute('href').split('/')[-1]
    except:
        orientadorId = ''
    
    page.set_default_timeout(500)
    return lista, orientadorId, anoDoutorado  

def buscaOrientados(page):
    try:

        # NOTE: Não procurar pela div diretamente utilizando b>> text="...", a performance desse locator é pessima
        page.set_default_timeout(2000)

        htmlDepoisDoCitaArtigo = page.locator('div.inst_back:has-text("Orientações e supervisões concluídas")').locator("//following-sibling::*").get_by_text("Tese de doutorado").locator("..").locator("..").first.inner_html()
        htmlDepoisDoCitaArtigo = htmlDepoisDoCitaArtigo.replace("\n", "").replace("\t", "")

        soup = BeautifulSoup(htmlDepoisDoCitaArtigo, 'html.parser')
        start_div = soup.find('b', string='Orientações e supervisões concluídas')
        if not start_div:
            return []

        # NOTE: Pegar o HTML após o ponto de início
        htmlDepoisDoCitaArtigo = ''.join(str(tag) for tag in start_div.find_all_next())

        soup = BeautifulSoup(htmlDepoisDoCitaArtigo, 'html.parser')

        # NOTE: Encontrar a div com a classe 'cita-artigos' que contém o texto 'Tese de doutorado'
        start_div = soup.find('div', class_='cita-artigos', string='Tese de doutorado')

        # NOTE: Iterar pelos elementos seguintes até encontrar a próxima div com a classe 'cita-artigos'
        spans = []
        for sibling in start_div.find_next_siblings():
            if sibling.name == 'div' and 'cita-artigos' in sibling.get('class', []):
                break
            spans.extend(sibling.find_all('span', class_='transform'))

        # NOTE: Extrair o href dentro da tag <a> com a classe icone-lattes dentro dos spans encontrados
        hrefs = []
        for span in spans:
            a_tag = span.find('a', class_='icone-lattes')
            if a_tag and a_tag.has_attr('href'):
                tag = a_tag['href'].split('/')[-1]
                hrefs.append(tag)
        return hrefs
    except:
        return []
    finally:
        page.set_default_timeout(500)

    
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1, max_delay=8, *args, **kwargs):
    """
    Função auxiliar para realizar retry com exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay) + random.uniform(0, 0.5)
                logger.warning(f"Tentativa {attempt + 1} falhou. Retentando em {delay:.2f} segundos...")
                time.sleep(delay)
            else:
                logger.error(f"Todas as tentativas falharam após {max_retries} tentativas.")
                raise e

def pesquisadorVazio():
    return Pesquisador(nome='', nacionalidade='')

def buscaInformacoesPesquisador(idLattes, context, page, grauMaximoOrientador, grauAtualOrientador, grauMinimoOrientados, grauAtualOrientados, orientadores, orientado, pesquisadores, idLattesPesquisadores, executandoOrientacoes, limitadorOrientados, setor, indicador_semente):
    if idLattes not in idLattesPesquisadores:
        idLattesPesquisadores.append(idLattes)
    else:
        for i in range(len(pesquisadores)):
            if pesquisadores[i].idLattes == idLattes:
                return pesquisadores[i]

    patternLattesLink = re.compile(r"[a-zA-Z]+")
    try:
        if patternLattesLink.match(idLattes):
            retry_with_backoff(page.goto, max_retries=3, base_delay=1, max_delay=8, url=os.getenv("URL_LATTES_10") + idLattes)
        else:
            retry_with_backoff(page.goto, max_retries=3, base_delay=1, max_delay=8, url=os.getenv("URL_LATTES") + idLattes)
        lid10 = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id'][0]

        URL_PREVIEW = os.getenv("URL_PREVIEW_LATTES")
        retry_with_backoff(page.goto, max_retries=3, base_delay=1, max_delay=8, url=URL_PREVIEW + lid10)
    except Exception as e:
        logger.error(f"Erro ao processar página do pesquisador: {str(idLattes)}. Erro: {e}")
        return None

    try:
        page.locator(".name").wait_for(timeout=5000)
    except Exception as e:
        logger.error("Erro ao esperar pela página de middleware entre Captcha e Currículo Lattes. Erro: {e}")
    context.route("**/*", handle_route_block_script)

    cmd_open_cv = 'abreCV()'
    with context.expect_page() as new_page:
        page.evaluate(cmd_open_cv)
    pages = new_page.value.context.pages
    pattern = re.compile(r".*visualizacv.*")
    for new_page in pages:
        new_page.wait_for_load_state()
        if pattern.match(new_page.url):
            page = new_page

    context.route("**/*", handle_route_block_nothing)

    page.set_default_timeout(500)
    time.sleep(8) # NOTE: Necessário para evitar bloqueio devido a muitas requisições seguidas


    # NOTE: Parse Página principal Lattes
    lista, orientadorIdLattes, anoDoutorado = getParametrosDoutorado(page)
    try:
        areaDoutorado = lista.split('.')[0]
    except:
        areaDoutorado = ''
    try:
        instituicaoDoutorado = lista.split('.')[1].strip().rsplit(",", 2)[0].strip()
    except:
        instituicaoDoutorado = ''
    try:
        tituloDoutorado = list(filter(None, lista.split('Título:')))[1].strip().split('\n')[0].split(',')[0]
    except:
        tituloDoutorado = ''
    try:
        palavrasChaveDoutorado = lista.split("Palavras-chave: ")[1].split('.')[0].split("; ")
    except:
        palavrasChaveDoutorado = []
    try:
        grandeArea = lista.split("Área: ")[1].split(" /")[0].strip()
        area = lista.split("Área: ")[2].split(" /")[0].strip()
        subArea = lista.split("Subárea: ")[1].split(".")[0]
    except:
        grandeArea = ''
        area = ''
        subArea = ''
    nome = page.locator(".nome").first.inner_text()
    urlPhoto = page.locator(".foto").get_attribute("src")
    try:
        instituicaoLotacaoList = page.locator("a[name=\"Endereco\"]").locator("..").locator(".layout-cell-12").locator(".layout-cell-9").locator(".layout-cell-pad-5").inner_html()
        endereco = instituicaoLotacaoList.split(".")[0].split(",")[0]
    except:
        endereco = ''

    try:
        nacionalidade = page.get_by_text("País de Nacionalidade").locator("..").locator("..").locator('//following-sibling::div').last.inner_text()
    except:
        nacionalidade = ''

    # NOTE: Correção para idLattes que iniciam com K, caso seja semente e seja orientado por uma semente, sem essa tratativa, duplicaria o pesquisador devido a dois IdLattes diferentes
    if indicador_semente:
        idLattes = page.get_by_text("Endereço para acessar este CV:").first.inner_text().replace("Endereço para acessar este CV: ","").replace("http://lattes.cnpq.br/","")

    pesquisador = Pesquisador(
        nome=nome,  # Nome obtido pela função
        nacionalidade=nacionalidade,  # Exemplo de nacionalidade
        idLattes=idLattes,  # ID do Lattes obtido
        orientador=pesquisadorVazio(),
        orientados=[],  # Lista de orientados
        instituicaoLotacao=endereco,  # Instituição de lotação obtida
        instituicaoDoutorado=instituicaoDoutorado,  # Instituição do doutorado
        grandeArea=grandeArea,  # Grande área de atuação
        area=area,  # Área de atuação
        subArea=subArea,  # Subárea de atuação
        tituloDoutorado=tituloDoutorado,  # Título do doutorado
        areaDoutorado=areaDoutorado,  # Área do doutorado
        anoDoutorado=anoDoutorado,  # Ano do doutorado
        palavrasChaveDoutorado=palavrasChaveDoutorado,  # Palavras-chave do doutorado
        imagePath=urlPhoto,  # URL da foto do pesquisador
        setor=setor,
        indicador_semente=indicador_semente
    )
    contador = 0

    # NOTE: Recursão para buscar vários pesquisadores
    logger.debug(f"Processamento concluído para o pesquisador: {nome}, com o Id: {str(idLattes)}, setor: {setor}")

    if grauAtualOrientados != grauMinimoOrientados:
        orientadosAux = buscaOrientados(page)
        for orientadoIdLattes in orientadosAux:
            if limitadorOrientados != 0:
                if contador == limitadorOrientados:
                    break
            page.set_default_timeout(40000)
            pesquisadorOrientado = buscaInformacoesPesquisador(orientadoIdLattes, context, page, grauMaximoOrientador, grauAtualOrientador, grauMinimoOrientados, grauAtualOrientados + 1, orientadores, pesquisador, pesquisadores, idLattesPesquisadores, 1, limitadorOrientados, setor, indicador_semente=False)
            pesquisador.orientados.append(pesquisadorOrientado)
            contador += 1

    if executandoOrientacoes == 0:
        if grauAtualOrientador == grauMaximoOrientador or orientadorIdLattes == '':
            pesquisadores.append(pesquisador)
            return pesquisador
        pesquisador.orientados.append(orientado)
        page.set_default_timeout(40000)
        pesquisador.orientador = buscaInformacoesPesquisador(orientadorIdLattes, context, page, grauMaximoOrientador, grauAtualOrientador + 1, grauMinimoOrientados, grauAtualOrientados, orientadores, pesquisador, pesquisadores, idLattesPesquisadores, 0, limitadorOrientados, setor, indicador_semente=False)
    elif executandoOrientacoes == 1:
        pesquisador.orientador = orientado

    orientadores.insert(0, pesquisador.orientador)
    pesquisadores.append(pesquisador)

    return pesquisador

def inserePesquisadores(pesquisadores):
    for pesquisador in pesquisadores:
        insert_pesquisador(pesquisador)
    for pesquisador in pesquisadores:
        insert_relacoes(pesquisador)

def buscaPesquisador(idLattes, setor): 
    '''NOTE: LIMITADOR PARA QUANTIDADE DE ORIENTADOS
    Exemplo: se for 2, limita as listas de orientados em 2, caso 0, traz todos os orientados'''
    
    limitadorOrientados = 0
    grauMaximoOrientador = 2
    grauMinimoOrientados = 2
    grauAtualOrientador = 0
    grauAtualOrientados = 0
    
    orientadores = []
    orientado = pesquisadorVazio()
    pesquisadores = []
    idLattesPesquisadores = []

    ''' NOTE: Variavel para controlar recursao
    #1 executa fluxo orientados -> ignora busca pelo orientador
    #0 executa fluxo completo, incluindo orientados'''
    executandoOrientacoes = 0

    with sync_playwright() as p:
        # NOTE: Configurar as opções do Chrome (caso deseje que a janela do navegador fique oculta), habilitar headless para performance fora de debug
        browser = p.chromium.launch(headless=False, args=["--enable-automation"])
        context = browser.new_context()
        context.set_default_timeout(40000)
        context.set_default_navigation_timeout(40000)
        page = context.new_page()
    
        buscaInformacoesPesquisador(idLattes, context, page, grauMaximoOrientador, grauAtualOrientador, grauMinimoOrientados, grauAtualOrientados, orientadores, orientado, pesquisadores, idLattesPesquisadores, executandoOrientacoes, limitadorOrientados, setor, indicador_semente = True)
        browser.close()
       
    inserePesquisadores(pesquisadores)

def leArquivo():
    pesquisadores = []
    arquivos = [f for f in os.listdir('.') if f.endswith('.list')]
    for arquivo in arquivos:
        file_name = arquivo.split(".")[0]
        with open(arquivo, "r") as file:
            for linha in file.readlines():
                idLattes = linha.split(",")[0]
                if idLattes != "" and idLattes is not None:
                    pesquisadores.append((idLattes.strip(), file_name))
    return pesquisadores
        
def processa_pesquisador(idLattes, setor):
    buscaPesquisador(idLattes, setor)

def main():
    load_dotenv()
    inicio = time.time()
    
    pesquisadores = leArquivo() 
    num_threads = int(1)
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(processa_pesquisador, pesquisador[0], pesquisador[1]) for pesquisador in pesquisadores]
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Erro ao processar pesquisador: {e}")

    fim = time.time()
    tempo_execucao = fim - inicio

    logger.info(f"Tempo de execução: {tempo_execucao} segundos")

if __name__ == "__main__":
    main()