import re
from dataclasses import dataclass

REPORT_TYPES = ("materiais", "equipamentos", "mao_de_obra")

# Real filenames in blob storage include mojibake from before an encoding fix
# (e.g. "M╞o de Obra", "desoneraç╞o") — ftfy.fix_text() does not repair these,
# so matching is done on ASCII-anchored substrings/wildcards that survive the
# corruption instead of relying on exact accented strings.
_MAO_DE_OBRA_RE = re.compile(r"m.{0,2}o\s+de\s+obra", re.IGNORECASE)
_DESONERADO_RE = re.compile(r"desonera.{0,2}o", re.IGNORECASE)


@dataclass(frozen=True)
class BlobClassification:
    blob_name: str
    region: str
    state_slug: str
    year: str
    month: str
    archive_stem: str
    report_type: str  # one of REPORT_TYPES
    desonerado: bool
    revisado: bool


def classify_blob(blob_name: str) -> BlobClassification | None:
    """Classifies a raw blob path, returning None for anything that isn't a
    Relatório Sintético Materiais/Equipamentos/Mão de Obra xlsx (Relatório
    Analítico, Composições de Custos, Encargos Sociais, Origem de Preços,
    PDFs, etc. are all excluded)."""

    if not blob_name.lower().endswith(".xlsx"):
        return None

    # Path shape is {region}/{state_slug}/{year}/{month}/{archive_stem}/...
    # with variable nesting after archive_stem depending on how the original
    # archive was structured, so only the first 5 segments are reliable.
    parts = blob_name.split("/")
    if len(parts) < 6:
        return None

    region, state_slug, year, month, archive_stem = parts[:5]
    filename = parts[-1].lower()

    if "relat" not in filename or "sint" not in filename:
        return None

    if "materiais" in filename:
        report_type = "materiais"
    elif "equipamentos" in filename:
        report_type = "equipamentos"
    elif _MAO_DE_OBRA_RE.search(filename):
        report_type = "mao_de_obra"
    else:
        return None

    return BlobClassification(
        blob_name=blob_name,
        region=region,
        state_slug=state_slug,
        year=year,
        month=month,
        archive_stem=archive_stem,
        report_type=report_type,
        desonerado=bool(_DESONERADO_RE.search(filename)),
        revisado="revisado" in blob_name.lower(),
    )
