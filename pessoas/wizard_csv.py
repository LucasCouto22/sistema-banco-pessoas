import csv
import io

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
    "Classes A/B",
]


def _mapear(valor, mapa):
    return mapa.get((valor or "").strip().lower(), "")


def ler_csv(arquivo):
    """Lê um arquivo CSV enviado via upload e devolve uma lista de dicionários com as
    chaves já normalizadas para os nomes de campo do modelo Participante. Datas devem
    estar no formato AAAA-MM-DD; valores de gênero/escolaridade/faixa de renda aceitam
    variações comuns em português (ex.: "Superior", "Médio", "Classes A/B")."""
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
    linhas = []
    for linha_bruta in leitor:
        dados = {}
        for chave, valor in linha_bruta.items():
            campo = CAMPOS_CSV.get((chave or "").strip().lower())
            if not campo:
                continue
            valor = (valor or "").strip()
            if campo == "genero":
                valor = _mapear(valor, GENERO_MAP)
            elif campo == "escolaridade":
                valor = _mapear(valor, ESCOLARIDADE_MAP)
            elif campo == "faixa_renda":
                valor = _mapear(valor, FAIXA_RENDA_MAP)
            dados[campo] = valor
        if any(dados.values()):
            linhas.append(dados)
    return linhas
