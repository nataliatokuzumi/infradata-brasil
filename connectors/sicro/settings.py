from datetime import datetime

database_path = "/Users/nataliaeruan/Documents/Nat/projetos/infradata_brasil/connectors/sicro/downloads.db"

sicro_base_url = r"https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/custos-referenciais/sistemas-de-custos/sicro/relatorios/relatorios-sicro"


sicro_regions = ["sudeste", "norte", "nordeste", "centro-oeste", "sul"]

sicro_states = {
    "sudeste": {"saopaulo": "sp", "riodejaneiro": "rj", "minasgerais": "mg", "espiritosanto": "es"},
    "norte": {"acre": "ac", "amapa": "ap", "amazonas": "am", "para": "pa", "rondonia": "ro", "roraima": "rr", "tocantins": "to"},
    "nordeste": {"alagoas": "al", "bahia": "ba", "ceara": "ce", "maranhao": "ma", "paraiba": "pb", "pernambuco": "pe", "piaui": "pi", "riosgrandedo norte": "rn", "sergipe": "se"},
    "centro-oeste": {"distritofederal": "df", "goias": "go", "matogrosso": "mt", "matogrossodosul": "ms"},
    "sul": {"parana": "pr", "riograndedosul": "rs", "santacatarina": "sc"}
}

current_year = datetime.now().year
sicro_years = [str(year) for year in range(2017, current_year)]

sicro_months = {"janeiro": "01", "fevereiro": "02", "marco": "03", "abril": "04", "maio": "05", "junho": "06", 
                "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"}

exemplo = "https://www.gov.br/dnit/pt-br/assuntos/planejamento-e-pesquisa/custos-referenciais/sistemas-de-custos/sicro/relatorios/relatorios-sicro/sudeste/espirito-santo/2025/outubro-2025/es-10-2025-Revisado1.7z"

