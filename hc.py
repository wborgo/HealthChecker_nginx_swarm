import yaml
import urllib2
import io
import os 
import time
import subprocess
from threading import Thread

servicosDisponiveis = {}
requestTimeout = 1

defaultHealthcheckPath = ""

#chama URL e verifica disponibilidade
def VerificaDisponibilidade(server, service):
    #recupera o path do healthcheck, se nao estiver definido, utiliza o default
    try:
        healthPath = service['healcheck_path']
    except:
        healthPath = config['default_healthcheck_path']
    
    #monta endpoint para testar 
    endpoint = "http://" + server + ":" + str(service['port']) + healthPath
    #print(endpoint)
    try:
        urllib2.urlopen(endpoint, timeout=requestTimeout).read()
        AdicionaServicoDisponivel(server, service)
    except urllib2.HTTPError as e:
        if e.code == 404 or e.code == 500:
            AdicionaServicoDisponivel(server, service)
        else:
            pass
            #print("------servico INDISPONIVEL " + endpoint + " - " + service['name'])
    except:
        pass
        #print("------servico INDISPONIVEL " + endpoint + " - " + service['name'])

#adiciona servicos existentes no dictionary para poder listar os servidores disponiveis
def AdicionaServico(service):
    servicosDisponiveis[service['name']] = []

#adiciona servidor na lista de server do servico
def AdicionaServicoDisponivel(server, service):
    #print("servico OK http://" + server + ":" + str(service['port']) + " - " + service['name'])
    servicosDisponiveis[service['name']].append({
            "ip": server,
            "port": service['port'],
            "serviceName": service['name']
        }) 

#grava arquivo de servidores disponiveis
def GravaCacheFile():
    with io.open('/dados/healthCheck/servers.yaml', 'w', encoding='utf8') as outfile:
        yaml.dump(servicosDisponiveis, outfile, default_flow_style=False, allow_unicode=True)

#carrega arquivo de configuracao
def CarregaConfiguracoes():
    with open("/dados/healthCheck/config.yml", 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

def CarregaCacheFile():
    with open("/dados/healthCheck/servers.yaml", 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

#retorna true se houver diferenca entre o arquivo atual e o de cache
def CacheFileEquals():
    #se arquivo de cache nao existir, ja retorna false
    if not os.path.isfile('/dados/healthCheck/servers.yaml'):
        return False

    cacheDisponiveis = CarregaCacheFile()

    #print(cacheDisponiveis)

    #compara se todas as chaves existem em ambos
    for key, value in servicosDisponiveis.items():
        if not key in cacheDisponiveis:
            return False

    for key, value in cacheDisponiveis.items():
        if not key in servicosDisponiveis:
            return False

    #compara os values
    for key, value in servicosDisponiveis.items():
        cacheValue = cacheDisponiveis[key]
        if len(cacheValue) != len(value):
            return False
        for v in value:
            encontrou = False
            for cv in cacheValue:
                if v['ip'] == cv['ip']:
                    encontrou = True
            if not encontrou:
                return False
        
    return True

def AtualizaNginxConf():
    modelFile = open("/dados/healthCheck/nginxModel.conf","r")
    model = modelFile.read()
    modelFile.close()

    #cria placeholder para grupo
    grpPlaceholder = ""
    locationPlaceholder = ""

    for key, value in servicosDisponiveis.items():
        #nao gera se nao tem servidor
        if len(value) == 0:
            continue

        grpPlaceholder += "\n\n"
        grpPlaceholder += "upstream grp_" + key + "{"
        for v in value:
            grpPlaceholder += "\n\tserver " + v['ip'] + ":" + str(v['port']) + ";"
        grpPlaceholder += "\n}"
    
    #cria placeholder para location
    for key, value in servicosDisponiveis.items():
        #nao gera se nao tem servidor
        if len(value) == 0:
            continue

        locationPlaceholder += "\n\n"
        locationPlaceholder += "\tlocation /" + key + "/ {"
        locationPlaceholder += "\n\t\tproxy_pass http://grp_" + key + "/;"
        locationPlaceholder += "\n\t}"

    model = model.replace("#UPSTREAM_PLACEHOLDER", grpPlaceholder)
    model = model.replace("#LOCATION_PLACEHOLDER", locationPlaceholder)

    file = open('/etc/nginx/nginx.conf', 'w')
    file.write(model)
    file.close()

    os.system('nginx -s reload')

def run():
    #                     INICIO                      #

    #le arquivo de configuracao
    config = CarregaConfiguracoes()

    servers = config['servers']
    services = config['services']
    #defaultHealthcheckPath = config['default_healthcheck_path']

    #lista de threads das requisicoes, para aguardar todas finalizarem antes de continuar
    threads = []

    #para cada server e para cada service, executa o get
    for service in services:
        AdicionaServico(service)
        for server in servers:
            req = Thread(target=VerificaDisponibilidade,args=[server,service])
            req.start()
            threads.append(req)


    #aguarda todas as threads finalizarem
    for thread in threads:
        thread.join()

    #print(servicosDisponiveis)

    #neste momento, temos a lista de todos os servidores disponiveis
    #verifica se o arquivo de cache existe
    cacheIgual = CacheFileEquals()

    if cacheIgual:
        print("nenhuma alteracao detectada")
    else:
        print("alteracao detectada")
        print("atualizando nginx")
        AtualizaNginxConf()
        GravaCacheFile()


config = CarregaConfiguracoes()

while 1:
    try:
        run()
    except Exception as e: 
        print(e)
    time.sleep(10)