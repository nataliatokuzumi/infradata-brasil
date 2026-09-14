import dash
import dash_mantine_components as dmc

from components import data_table
from gold import query

dash.register_page(__name__, path="/", name="Início", title="SICRO Gold", order=0)


def layout(**kwargs):
    cobertura = query(
        """
        select tipo, count(*) as n_ufs, max(ultimo_periodo_disponivel) as periodo_mais_recente,
               sum(periodos_faltantes_vs_pares) as total_lacunas
        from vw_cobertura
        group by 1
        order by 1
        """
    )

    return dmc.Stack(
        [
            dmc.Title("SICRO — custos referenciais de obras", order=1),
            dmc.Text(
                "Dados do DNIT (materiais, equipamentos e mão de obra), atualizados a "
                "partir da camada gold em Blob Storage.",
                c="dimmed",
                size="sm",
            ),
            dmc.Text("Use o menu à esquerda pra navegar entre as páginas:"),
            dmc.List(
                [
                    dmc.ListItem([dmc.Text([dmc.Text("Preço por Item + Evolução", span=True, fw=700), " — preço/custo mais recente e série histórica por item, UF e regime."])]),
                ]
            ),
            dmc.Text(
                "As demais páginas (comparação de regime, comparação entre UFs, índice de "
                "reajuste, maiores variações, detalhamento de equipamento/mão de obra, "
                "cobertura) estão temporariamente desativadas enquanto a página acima é "
                "refinada.",
                c="dimmed",
                size="sm",
                fs="italic",
            ),
            dmc.Title("Cobertura — visão geral", order=3, mt="md"),
            data_table(cobertura),
        ],
        gap="xs",
    )
