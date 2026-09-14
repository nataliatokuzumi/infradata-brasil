"""Conexão compartilhada com a gold do SICRO — mesma receita já validada no
setup do Superset (superset/bootstrap_gold_catalog.py) e do antigo app
Streamlit (streamlit/gold.py): segredo Azure persistente + uma view por
model, lendo direto do Parquet exportado em Blob Storage por
transform/macros/export_to_gold.sql. Nunca loga a connection string.
"""
import os
import time
from functools import wraps

import duckdb
import pandas as pd

DUCKDB_HOME = "/app/duckdb_home"
CATALOG_PATH = f"{DUCKDB_HOME}/gold_catalog.duckdb"
SECRET_DIR = f"{DUCKDB_HOME}/secrets"

GOLD_MODELS = [
    "dim_uf",
    "dim_data_referencia",
    "dim_insumo",
    "fato_preco_material",
    "fato_custo_equipamento",
    "fato_custo_mao_de_obra",
    "fato_medicao",
    "vw_preco_atual",
    "vw_evolucao_preco",
    "vw_comparacao_regime",
    "vw_comparacao_uf",
    "vw_indice_reajuste",
    "vw_maiores_variacoes",
    "vw_breakdown_equipamento",
    "vw_breakdown_mao_de_obra",
    "vw_cobertura",
]

TIPOS = ["materiais", "equipamentos", "mao_de_obra"]

TIPO_LABELS = {
    "materiais": "Materiais",
    "equipamentos": "Equipamentos",
    "mao_de_obra": "Mão de Obra",
}

# medida "principal"/headline de cada tipo — usada como padrão em gráficos e
# cartões, porque as demais medidas (componentes de custo) têm escalas muito
# diferentes entre si (ex: valor_aquisicao de equipamento fica na casa dos
# milhares, custo_produtivo do mesmo item fica nas dezenas) e plotadas juntas
# sem filtro deixam as menores achatadas em zero.
MEDIDA_PRINCIPAL = {
    "materiais": "preco_unitario",
    "equipamentos": "custo_produtivo",
    "mao_de_obra": "custo",
}

# medida cobre tanto os valores da coluna `medida` (fato_medicao/vw_*) quanto
# os nomes de coluna dos componentes de custo nas views de breakdown
# (vw_breakdown_equipamento/mao_de_obra) — é o mesmo vocabulário nos dois
# lugares, então um dicionário só serve pra ambos.
MEDIDA_LABELS = {
    "preco_unitario": "Preço Unitário",
    "custo_produtivo": "Custo Produtivo",
    "custo_improdutivo": "Custo Improdutivo",
    "valor_aquisicao": "Valor de Aquisição",
    "depreciacao": "Depreciação",
    "oportunidade_capital": "Oportunidade de Capital",
    "seguros_impostos": "Seguros e Impostos",
    "manutencao": "Manutenção",
    "operacao": "Operação",
    "mao_de_obra_operacao": "Mão de Obra de Operação",
    "salario": "Salário",
    "encargos_totais": "Encargos Totais",
    "custo": "Custo",
    "periculosidade_insalubridade": "Periculosidade e Insalubridade",
}

REGIAO_LABELS = {
    "centro-oeste": "Centro-Oeste",
    "nordeste": "Nordeste",
    "norte": "Norte",
    "sudeste": "Sudeste",
    "sul": "Sul",
}

MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def rotulo_medida(medida: str) -> str:
    return MEDIDA_LABELS.get(medida, medida)


def rotulo_regiao(regiao: str) -> str:
    return REGIAO_LABELS.get(regiao, regiao)


def rotulo_sim_nao(v: bool) -> str:
    return "Sim" if v else "Não"


def rotulo_schema_version(v: str) -> str:
    return {"pre_2025": "Até 2025", "2025_plus": "2025 em diante"}.get(v, v)


def formatar_periodo(data) -> str:
    """'Abril/2026' — como o DNIT nomeia as publicações do SICRO (mês/ano),
    em vez de uma data dd/mm/aaaa que não tem esse significado pra quem lê."""
    return f"{MESES_PT[data.month]}/{data.year}"


def _numero_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda_grafico(valor: float) -> str:
    """R$ no padrão brasileiro — pra rótulos/hover de gráficos Plotly."""
    return f"R$ {_numero_brl(valor)}"


def formatar_moeda(valor: float) -> str:
    """R$ no padrão brasileiro (separador de milhar '.', decimal ',').
    Mantido separado de formatar_moeda_grafico (que era o formato "seguro pra
    Streamlit" no app antigo, escapando '$' pra não virar LaTeX) porque os
    cartões de métrica aqui são HTML puro — não há parser Markdown/LaTeX no
    meio, então os dois formatos já são idênticos."""
    return f"R$ {_numero_brl(valor)}"


def formatar_faixa_moeda(minimo: float, maximo: float) -> str:
    return f"{formatar_moeda(minimo)} – {formatar_moeda(maximo)}"


_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    # Singleton de processo — o papel que st.cache_resource cumpria no app
    # Streamlit (que também é global por processo, não por sessão).
    global _connection
    if _connection is not None:
        return _connection

    os.makedirs(DUCKDB_HOME, exist_ok=True)
    # azure_transport_option_type=curl: sem isso, "Problem with the SSL CA
    # cert" neste tipo de container (ver superset/register_gold_database.py
    # pro histórico completo do debug).
    con = duckdb.connect(CATALOG_PATH, config={"azure_transport_option_type": "curl"})
    con.execute(f"SET secret_directory = '{SECRET_DIR}'")
    con.execute(
        "CREATE OR REPLACE PERSISTENT SECRET azure_gold (TYPE azure, CONNECTION_STRING ?)",
        [os.environ["AZURE_STORAGE_CONNECTION_STRING"]],
    )

    container = os.environ["AZURE_STORAGE_CONTAINER"]
    for model in GOLD_MODELS:
        con.execute(f"""
            CREATE OR REPLACE VIEW {model} AS
            SELECT * FROM read_parquet('azure://{container}/gold/{model}/*.parquet')
        """)

    _connection = con
    return con


def _ttl_cache(ttl_seconds: int):
    """Substitui st.cache_data(ttl=...): mesmo papel (cache por processo,
    compartilhado entre todas as sessões/abas), só que Dash não tem
    equivalente embutido. Chave por (args, kwargs) — todo chamador aqui usa
    só tipos hasháveis (str, tuple, None)."""

    def decorator(fn):
        cache: dict[tuple, tuple[float, object]] = {}

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            cached = cache.get(key)
            if cached is not None and now - cached[0] < ttl_seconds:
                return cached[1]
            value = fn(*args, **kwargs)
            cache[key] = (now, value)
            return value

        return wrapper

    return decorator


@_ttl_cache(ttl_seconds=600)
def _query_cached(sql: str, params: tuple) -> pd.DataFrame:
    # cursor(), não a conexão crua: a conexão de get_connection() é uma
    # única instância compartilhada entre todas as requisições do Dash (que
    # atende múltiplas sessões concorrentemente via threads/workers), e
    # conexões DuckDB não são seguras pra uso concorrente por múltiplas
    # threads — duas requisições quase simultâneas podiam fazer uma query
    # pisar na outra. cursor() cria um handle independente pra essa
    # chamada, compartilhando o mesmo banco.
    con = get_connection().cursor()
    return con.execute(sql, list(params)).df()


def query(sql: str, params: list | None = None) -> pd.DataFrame:
    return _query_cached(sql, tuple(params) if params else ())


@_ttl_cache(ttl_seconds=3600)
def list_ufs() -> pd.DataFrame:
    df = query("select state_slug, state_code, state_name, region from dim_uf order by state_name")
    if df is None:
        return pd.DataFrame(columns=["state_slug", "state_code", "state_name", "region"])
    return df


@_ttl_cache(ttl_seconds=3600)
def list_insumos(tipo: str | None = None) -> pd.DataFrame:
    """tipo=None lista insumos de todos os tipos juntos — funciona porque
    codigo é único entre materiais/equipamentos/mao_de_obra (confirmado:
    2951 códigos, 0 duplicados entre tipos)."""
    if tipo is None:
        df = query("select codigo, descricao from dim_insumo order by descricao")
    else:
        df = query(
            "select codigo, descricao from dim_insumo where tipo = ? order by descricao",
            [tipo],
        )
    if df is None:
        return pd.DataFrame(columns=["codigo", "descricao"])
    return df
