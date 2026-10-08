"""Read-only provenance checks for the pinned Phase 1 integration inputs."""
import hashlib
from pathlib import Path
import zipfile

import geopandas as gpd
import numpy as np

from src.config import CITY_LOC, DATA_PROCESSED, DATA_RAW
from src.transform import geography
from src.transform.census import CENSUS_FILE
from src.transform.denue import DENUE_FILE

# Stable versions, independent of a manifest that download can rewrite.
PINNED_MANIFEST_DIGESTS = {
    "census_ageb_2020_09": "1f5f123b8e9a50991d1847271b5a2bf321e813e924e5bcf958cab612311c765a",
    "denue_09": "ae608f30118f6313e9d537ea22918b2c9e9a3d3f19c2ddf5907f55dbb1642b19",
    "marco_geo_2020_09": "685b912f5458138a70726cff41aff828473e14264c43289d3b21f86a9df00320",
    "crime_fgj_2024": "2ac3f17189a61ab7b2eb95fb21470e46adaba6f92526c7b92d23190ed2431f84",
}
PINNED_CRIME_SHA256 = PINNED_MANIFEST_DIGESTS["crime_fgj_2024"]
ARCHIVE_MEMBERS = {
    "census_ageb_2020_09": (CENSUS_FILE.relative_to(DATA_RAW / "census_ageb_2020_09").as_posix(),),
    "denue_09": (DENUE_FILE.relative_to(DATA_RAW / "denue_09").as_posix(),),
    "marco_geo_2020_09": tuple(
        f"conjunto_de_datos/{stem}{suffix}"
        for stem in (geography.AGEB_FILE.stem, geography.LOCALITY_FILE.stem, geography.MUNICIPALITY_FILE.stem)
        for suffix in (".shp", ".shx", ".dbf", ".prj")
    ),
}


def _hash_stream(stream) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1 << 20), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _hash_file(path: Path) -> str:
    with path.open("rb") as stream:
        return _hash_stream(stream)


def _verify_processed_geography(path: Path, marco_dir: Path) -> None:
    """Compare all geography attributes and polygons to verified source layers.

    Reuse the owner's source projection/scope helpers without calling run(),
    which would overwrite the very Parquet we are trying to verify.
    """
    processed = gpd.read_parquet(path)
    if list(processed.columns) != geography.AGEB_COLUMNS:
        raise ValueError("ageb.parquet: columns/order differ from the geography contract")
    if processed.crs is None or processed.crs.to_epsg() != 6372:
        raise ValueError("ageb.parquet: expected EPSG:6372")
    if not processed["cvegeo"].is_unique:
        raise ValueError("ageb.parquet: duplicate geographic keys")
    if processed.geometry.isna().any() or not processed.geometry.is_valid.all():
        raise ValueError("ageb.parquet: missing or invalid geometry")
    if not processed.geom_type.eq("MultiPolygon").all():
        raise ValueError("ageb.parquet: expected MultiPolygon geometry")

    layers = [
        geography._filter_state(geography._read_projected(marco_dir / source.name))
        for source in (geography.AGEB_FILE, geography.LOCALITY_FILE, geography.MUNICIPALITY_FILE)
    ]
    agebs, localities, municipalities = layers
    if any(layer.empty or not layer["CVEGEO"].is_unique for layer in layers):
        raise ValueError("Marco source layers: empty scope or duplicate geographic keys")
    source = agebs.set_index("CVEGEO").sort_index()
    actual = processed.set_index("cvegeo").sort_index()
    if set(actual.index) != set(source.index):
        raise ValueError("ageb.parquet: key set differs from verified Marco source")
    expected_fields = {
        "cve_ent": source["CVE_ENT"],
        "cve_mun": source["CVE_MUN"],
        "cve_loc": source["CVE_LOC"],
        "cve_ageb": source["CVE_AGEB"],
        "mun_name": source["CVE_MUN"].map(municipalities.set_index("CVE_MUN")["NOMGEO"]),
        "loc_name": source.index.to_series().str[:9].map(localities.set_index("CVEGEO")["NOMGEO"]),
        "is_city_core": source["CVE_LOC"].eq(CITY_LOC),
    }
    for field, expected in expected_fields.items():
        if expected.isna().any() or not actual[field].eq(expected).fillna(False).all():
            raise ValueError(f"ageb.parquet: {field} differs from verified Marco source")
    if not np.allclose(actual["area_km2"], source.geometry.area / 1_000_000, rtol=1e-12, atol=1e-12):
        raise ValueError("ageb.parquet: area_km2 differs from verified projected source")
    # Topological equality permits the owner's Polygon -> MultiPolygon wrapping
    # and ring ordering, but rejects shifted/altered boundaries (no tolerance).
    if not all(left.equals(right) for left, right in zip(actual.geometry, source.geometry)):
        raise ValueError("ageb.parquet: geometry differs from verified Marco source")


def verify_input_provenance(
    raw_dir: Path | None = None, processed_dir: Path | None = None,
) -> dict[str, str]:
    """Require pinned archives, consistent consumed extraction and derived polygons.

    This function never downloads, extracts, writes a manifest or rebuilds data.
    A SHA-valid archive alone does not certify an existing extraction directory.
    """
    raw_dir = DATA_RAW if raw_dir is None else Path(raw_dir)
    processed_dir = DATA_PROCESSED if processed_dir is None else Path(processed_dir)
    verified: dict[str, str] = {}
    failures: list[str] = []
    for key, members in ARCHIVE_MEMBERS.items():
        archive = raw_dir / f"{key}.zip"
        if not archive.is_file():
            failures.append(f"{key}.zip: required archive is missing")
            continue
        digest = _hash_file(archive)
        if digest != PINNED_MANIFEST_DIGESTS[key]:
            failures.append(f"{key}.zip: SHA-256 mismatch (expected {PINNED_MANIFEST_DIGESTS[key]}, got {digest})")
            continue
        try:
            with zipfile.ZipFile(archive) as source:
                needed = set(members)
                if key == "marco_geo_2020_09":
                    # Encoding and any spatial indexes accompanying consumed layers
                    # also affect reads; require them when present in the archive.
                    stems = {Path(member).with_suffix("").as_posix() for member in members}
                    needed.update(
                        name for name in source.namelist()
                        if Path(name).with_suffix("").as_posix() in stems
                    )
                    for stem in stems:
                        for suffix in (".cpg", ".qix", ".sbn", ".sbx"):
                            relative = stem + suffix
                            if (raw_dir / key / relative).exists() and relative not in needed:
                                failures.append(f"{key}/{relative}: unverified extra shapefile sidecar")
                for member in sorted(needed):
                    if member not in source.namelist():
                        failures.append(f"{key}/{member}: required archive member is missing")
                        continue
                    extracted = raw_dir / key / member
                    if not extracted.is_file():
                        failures.append(f"{key}/{member}: required extracted member is missing")
                        continue
                    with source.open(member) as stream:
                        expected = _hash_stream(stream)
                    if _hash_file(extracted) != expected:
                        failures.append(f"{key}/{member}: extracted bytes differ from the pinned archive")
        except (zipfile.BadZipFile, OSError) as error:
            failures.append(f"{key}.zip: cannot verify archive members ({type(error).__name__})")
        verified[key] = digest

    crime_key = "crime_fgj_2024"
    for relative in (Path(f"{crime_key}.csv"), Path(crime_key) / f"{crime_key}.csv"):
        path = raw_dir / relative
        if not path.is_file():
            failures.append(f"{relative.as_posix()}: required FGJ file is missing")
        elif _hash_file(path) != PINNED_CRIME_SHA256:
            failures.append(f"{relative.as_posix()}: FGJ SHA-256 mismatch")
    verified[crime_key] = PINNED_CRIME_SHA256
    ageb_path = processed_dir / "ageb.parquet"
    if not ageb_path.is_file():
        failures.append("ageb.parquet: required processed polygons are missing")
    elif not failures:
        try:
            _verify_processed_geography(ageb_path, raw_dir / "marco_geo_2020_09" / "conjunto_de_datos")
        except (ValueError, KeyError, OSError, TypeError) as error:
            failures.append(str(error))
    if failures:
        raise ValueError(
            "Raw input provenance verification failed:\n  - " + "\n  - ".join(failures)
            + "\nPreserve the current raw files as evidence. In a separate clean checkout, "
            "copy only the approved archives/FGJ file into an empty data/raw directory, "
            "then run 'python -m src.pipeline download transform' to extract and rebuild. "
            "Re-run this preflight before publishing results. Ordinary download skips "
            "existing extraction directories; stage does not rebuild them. "
            "See docs/integration_check.md for prerequisites and recovery."
        )
    return verified
