import csv
import datetime
import io

from openpyxl import load_workbook

from .models import Profissao

CAMPOS_CSV = {
    "nome completo": "nome",
    "nome": "nome",
    "cpf": "cpf",
    "data de nascimento": "data_nascimento",
    "data nascimento": "data_nascimento",
    "nascimento": "data_nascimento",
    "genero": "genero",
    "gênero": "genero",
    "e-mail": "email",
    "email": "email",
    "telefone": "telefone",
    "cidade": "cidade",
    "uf": "uf",
    "cep": "cep",
    "escolaridade": "escolaridade",
    "profissao": "profissao",
    "profissão": "profissao",
    "especialidade": "especialidade",
    "faixa de renda": "faixa_renda",
    "faixa_renda": "faixa_renda",
}

GENERO_MAP = {
    "feminino": "FEMININO",
    "f": "FEMININO",
    "masculino": "MASCULINO",
    "m": "MASCULINO",
    "outro": "OUTRO",
    "nao informa": "NAO_INFORMA",
    "não informa": "NAO_INFORMA",
    "prefere nao informar": "NAO_INFORMA",
    "prefere não informar": "NAO_INFORMA",
}
ESCOLARIDADE_MAP = {
    "fundamental": "FUNDAMENTAL",
    "medio": "MEDIO",
    "médio": "MEDIO",
    "superior": "SUPERIOR",
    "pos": "POS",
    "pós": "POS",
    "pos-graduacao": "POS",
    "pós-graduação": "POS",
}
FAIXA_RENDA_MAP = {
    "a": "A_B",
    "b": "A_B",
    "a/b": "A_B",
    "classes a/b": "A_B",
    "a_b": "A_B",
    "c": "C",
    "classe c": "C",
    "d": "D_E",
    "e": "D_E",
    "d/e": "D_E",
    "classes d/e": "D_E",
    "d_e": "D_E",
}

CABECALHO_MODELO = [
    "Nome completo",
    "CPF",
    "Data de nascimento",
    "Gênero",
    "E-mail",
    "Telefone",
    "Cidade",
    "UF",
    "CEP",
    "Escolaridade",
    "Profissão",
    "Especialidade",
    "Faixa de renda",
]

LINHA_EXEMPLO = [
    "Maria da Silva",
    "111.444.777-35",
    "1990-05-10",
    "Feminino",
    "maria@example.com",
    "11999998888",
    "São Paulo",
    "SP",
    "01000-000",
    "Superior",
    "Designer",
    "UX/UI",
    "Classes A/B",
]


def _mapear(valor, mapa):
    return mapa.get((valor or "").strip().lower(), "")


def _mapa_profissoes():
    """Nome (minúsculo) → PK, montado com uma única consulta e reaproveitado
    pra todas as linhas do arquivo — evita uma query por célula."""
    return {p.nome.lower(): str(p.pk) for p in Profissao.objects.all()}


def _normalizar_campo(campo, valor, mapa_profissoes=None):
    if campo == "genero":
        return _mapear(valor, GENERO_MAP)
    if campo == "escolaridade":
        return _mapear(valor, ESCOLARIDADE_MAP)
    if campo == "faixa_renda":
        return _mapear(valor, FAIXA_RENDA_MAP)
    if campo == "profissao":
        return _mapear(valor, mapa_profissoes or {})
    return valor


def variaveis_do_formulario(formulario):
    """Lista ordenada de `FormularioVariavel` de um formulário — mesma
    consulta que `formularios/respostas.py::construir_form_resposta` usa,
    reaproveitada aqui pra montar o cabeçalho/exemplo do modelo de planilha
    e pra saber quais colunas extras esperar na hora de ler o arquivo."""
    return list(
        formulario.formulario_variaveis.select_related("variavel__tipo_resposta")
        .prefetch_related("variavel__opcoes")
        .order_by("ordem")
    )


def _exemplo_variavel(variavel):
    """Valor de exemplo pra célula dessa variável no modelo de planilha —
    mesma lógica de tipo que `formularios/respostas.py::_campo_para_variavel`,
    só que devolvendo um texto pronto pra célula em vez de um widget."""
    tipo = variavel.tipo_resposta.codigo
    if tipo in ("select", "radio"):
        opcao = variavel.opcoes.first()
        return opcao.valor if opcao else ""
    if tipo == "multipla_escolha":
        opcoes = list(variavel.opcoes.all()[:2])
        return ", ".join(o.valor for o in opcoes) if opcoes else ""
    if tipo == "booleano":
        return "Sim"
    if tipo == "data":
        return "2000-01-01"
    if tipo in ("inteiro", "decimal"):
        return "0"
    return "Exemplo"


def _normalizar_valor_dinamico(variavel, valor):
    """Normaliza o texto de uma célula pro formato que
    `construir_form_resposta()` espera validar — só mexe nos tipos que têm
    um vocabulário fixo (booleano/opções); texto, número e data passam como
    a pessoa digitou (o próprio `Field` do formulário dinâmico valida)."""
    tipo = variavel.tipo_resposta.codigo
    valor = (valor or "").strip()
    if tipo == "booleano":
        chave = valor.lower()
        if chave in ("sim", "s", "yes", "verdadeiro", "true", "1"):
            return "sim"
        if chave in ("nao", "não", "n", "no", "falso", "false", "0"):
            return "nao"
        return valor
    if tipo in ("select", "radio", "multipla_escolha"):
        opcoes = {o.valor.strip().lower(): o.valor for o in variavel.opcoes.all()}
        if tipo == "multipla_escolha":
            partes = [p.strip() for p in valor.split(",") if p.strip()]
            return [opcoes.get(p.lower(), p) for p in partes]
        return opcoes.get(valor.lower(), valor)
    return valor


def _normalizar_cabecalho(texto):
    """"Nome Completo *" (o `*` marca obrigatório no modelo baixado) vira
    "nome completo" — sem isso a coluna nunca bate com a variável na hora
    de ler o arquivo de volta."""
    texto = str(texto or "").strip().lower()
    if texto.endswith("*"):
        texto = texto[:-1].strip()
    return texto


def _mapa_variaveis(formulario):
    """Nome da variável (minúsculo) → (chave, Variavel) — usado pra casar o
    cabeçalho da planilha com a variável certa do formulário do perfil."""
    if not formulario:
        return {}
    return {
        fv.variavel.nome.strip().lower(): fv.variavel
        for fv in variaveis_do_formulario(formulario)
    }


def _texto_celula(valor):
    """Normaliza o valor de uma célula do Excel pra texto. Datas viram
    'AAAA-MM-DD' (o `openpyxl` já devolve `datetime.date` pra células
    formatadas como data) e números inteiros guardados como float (ex.: CPF
    digitado só com dígitos, que o Excel trata como número) voltam a virar
    string sem casas decimais, senão "11144477735" vira "11144477735.0"."""
    if valor is None:
        return ""
    if isinstance(valor, (datetime.date, datetime.datetime)):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def ler_csv(arquivo, formulario=None):
    """Lê um arquivo CSV enviado via upload e devolve uma lista de dicionários com as
    chaves já normalizadas para os nomes de campo do modelo Participante. Datas devem
    estar no formato AAAA-MM-DD; valores de gênero/escolaridade/faixa de renda aceitam
    variações comuns em português (ex.: "Superior", "Médio", "Classes A/B"). Se
    `formulario` for passado (o formulário do perfil escolhido no wizard), colunas
    que baterem com o nome de uma variável desse formulário também entram no
    resultado, com a chave da variável — prontas pra `construir_form_resposta()`."""
    bruto = arquivo.read()
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = bruto.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    else:
        texto = bruto.decode("utf-8", errors="replace")

    try:
        dialect = csv.Sniffer().sniff(texto[:2000], delimiters=",;")
    except csv.Error:
        dialect = csv.excel

    leitor = csv.DictReader(io.StringIO(texto), dialect=dialect)
    mapa_profissoes = _mapa_profissoes()
    mapa_variaveis = _mapa_variaveis(formulario)
    linhas = []
    for linha_bruta in leitor:
        dados = {}
        for chave_coluna, valor in linha_bruta.items():
            chave_coluna = _normalizar_cabecalho(chave_coluna)
            valor = (valor or "").strip()
            campo = CAMPOS_CSV.get(chave_coluna)
            if campo:
                dados[campo] = _normalizar_campo(campo, valor, mapa_profissoes)
                continue
            variavel = mapa_variaveis.get(chave_coluna)
            if variavel:
                dados[variavel.chave] = _normalizar_valor_dinamico(variavel, valor)
        if any(dados.values()):
            linhas.append(dados)
    return linhas


def ler_xlsx(arquivo, formulario=None):
    """Lê a primeira planilha de um arquivo .xlsx enviado via upload — mesma
    saída de `ler_csv()` (lista de dicionários com os campos já normalizados,
    incluindo as colunas do `formulario` do perfil quando houver), só que
    lendo célula a célula em vez de linha de texto."""
    pasta = load_workbook(arquivo, data_only=True, read_only=True)
    aba = pasta.active
    linhas_brutas = aba.iter_rows(values_only=True)
    try:
        cabecalho_bruto = next(linhas_brutas)
    except StopIteration:
        return []
    cabecalho = [_normalizar_cabecalho(c) for c in cabecalho_bruto]

    mapa_profissoes = _mapa_profissoes()
    mapa_variaveis = _mapa_variaveis(formulario)
    linhas = []
    for linha_bruta in linhas_brutas:
        dados = {}
        for chave_coluna, valor in zip(cabecalho, linha_bruta):
            campo = CAMPOS_CSV.get(chave_coluna)
            if campo:
                dados[campo] = _normalizar_campo(campo, _texto_celula(valor), mapa_profissoes)
                continue
            variavel = mapa_variaveis.get(chave_coluna)
            if variavel:
                dados[variavel.chave] = _normalizar_valor_dinamico(variavel, _texto_celula(valor))
        if any(dados.values()):
            linhas.append(dados)
    return linhas


def ler_planilha(arquivo, formulario=None):
    """Ponto de entrada único do wizard de importação: aceita tanto .csv
    quanto .xlsx e despacha pro leitor certo com base na extensão do
    arquivo enviado. `formulario` (opcional) é o formulário do perfil
    escolhido no wizard — quando presente, as respostas dele também são
    lidas da planilha."""
    nome = (arquivo.name or "").lower()
    if nome.endswith(".xlsx"):
        return ler_xlsx(arquivo, formulario)
    return ler_csv(arquivo, formulario)
