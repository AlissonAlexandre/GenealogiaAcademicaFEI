from playwright.sync_api import sync_playwright
import urllib.parse
import time
from dotenv import load_dotenv, dotenv_values 
import re
import os
from pesquisador import Pesquisador
from bs4 import BeautifulSoup


def handle_route_block_script(route, request):
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
    
    #class clear (orientador,area,subarea)            
    objetoParamDoutorado = elementosAcademicos.nth(index)

    #criar parse aqui para extrair area, orientador, etc
    lista = objetoParamDoutorado.text_content().replace("\t",'')
    try:
        orientadorId = objetoParamDoutorado.locator('a.icone-lattes').get_attribute('href').split('/')[-1]
    except:
        orientadorId = ''
    return lista, orientadorId 
    
def buscaPesquisador(idLattes): 
    with sync_playwright() as p:
        # Configurar as opções do Chrome (caso deseje que a janela do navegador fique oculta)
        browser = p.chromium.launch(headless=False, args=["--enable-automation"], timeout=5000)
        context = browser.new_context()
        # Inicializar o WebDriver
        page = context.new_page()
        
        # Abrir uma página web
        patternLattesLink = re.compile(r"[a-zA-Z]+")
        if(patternLattesLink.match(idLattes)):
            page.goto(os.getenv("URL_LATTES_10") + idLattes)
        else:
            page.goto(os.getenv("URL_LATTES") + idLattes)
        lid10 = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id'][0]
        
        URL_PREVIEW = os.getenv("URL_PREVIEW_LATTES")        
        page.goto(URL_PREVIEW + lid10) 

        timeout = 5000  # Timeout in milliseconds
        try:
            page.locator(".name").wait_for(timeout=timeout)
        except:
            print("Erro ao esperar pela pagina de middleware entre Captcha e Curriculo Lattes")
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

        #page.route("**buscatextual/js/v2*", handle_route)
        print("Carregou pagina lattes do curriculo: ")
        context.route("**/*", handle_route_block_nothing)

        #criar parse aqui para extrair area, orientador, etc
        lista, orientadorIdLattes = getParametrosDoutorado(page)
        print(lista)
        areaDoutorado = lista.split('.')[0]
        instituicaoDoutorado = lista.split('.')[1].strip().split(',')[0]
        tituloDoutorado = list(filter(None, lista.split('Título:')))[1].strip().split('\n')[0].split(',')[0]
        anoDoutorado = list(filter(None, re.split(r'Ano de obtenção: |\.|  , ', lista)))[0]
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
        #id lattes apenas 1 orientador por enquanto
        print("LINK LATTES ORIENTADOR: " + orientadorIdLattes)


        print("LISTA COMPLETA SEM PARSER: ")
        print(lista)
    
        time.sleep(1000)
        
        # Fechar o navegador
        browser.close()
        return Pesquisador("","","",[],[],instituicao,"","","","","",[],"","")

load_dotenv()
buscaPesquisador("5337976093923686")