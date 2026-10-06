import unittest
from datetime import date

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from src.transform.denue import (
    activity_group,
    build_business,
    build_economic_activity,
    parse_alta_date,
    sector_code,
)


class DenueMappingTests(unittest.TestCase):
    def test_sector_code_combines_official_multi_sector_groups(self):
        self.assertEqual(sector_code("311111"), "31-33")
        self.assertEqual(sector_code("491110"), "48-49")
        self.assertEqual(sector_code("461110"), "46")

    def test_activity_group_classifies_retail_services_and_other(self):
        self.assertEqual(activity_group("46"), "Retail")
        self.assertEqual(activity_group("54"), "Services")
        self.assertEqual(activity_group("31-33"), "Other")

    def test_parse_alta_date_uses_first_day_and_coerces_invalid_values(self):
        result = parse_alta_date(pd.Series(["2026-04", "", None, "bad"]))

        self.assertEqual(result.iloc[0], pd.Timestamp("2026-04-01"))
        self.assertTrue(result.iloc[1:].isna().all())


class DenueTableTests(unittest.TestCase):
    def setUp(self):
        self.source = gpd.GeoDataFrame(
            {
                "id": ["1", "2", "3"],
                "clee": ["A", "B", "C"],
                "nom_estab": ["Shop", "Office", None],
                "codigo_act": ["461110", "541110", "311111"],
                "nombre_act": ["Retail activity", "Legal services", "Manufacturing"],
                "per_ocu": ["0 a 5 personas", "6 a 10 personas", "11 a 30 personas"],
                "fecha_alta": ["2020-01", "2021-02", "bad"],
                "cve_ent": ["31", "31", "31"],
                "cve_mun": ["050", "050", "050"],
                "cve_loc": ["0001", "0001", "0001"],
                "ageb": ["001A", "002B", "003C"],
                "cvegeo": ["310500001001A", "310500001002B", "310500001003C"],
            },
            geometry=[Point(1, 1), Point(2, 2), Point(3, 3)],
            crs="EPSG:6372",
        )

    def test_economic_activity_has_exact_contract_and_unique_scian_codes(self):
        duplicated = pd.concat([self.source, self.source.iloc[[0]]], ignore_index=True)

        result = build_economic_activity(duplicated)

        self.assertEqual(
            result.columns.tolist(),
            [
                "scian_code",
                "activity_name",
                "subsector_code",
                "sector_code",
                "sector_name",
                "activity_group",
            ],
        )
        self.assertEqual(len(result), 3)
        self.assertTrue(result["scian_code"].is_unique)
        indexed = result.set_index("scian_code")
        self.assertEqual(indexed.loc["461110", "sector_name"], "Retail trade")
        self.assertEqual(indexed.loc["541110", "activity_group"], "Services")
        self.assertEqual(indexed.loc["311111", "sector_code"], "31-33")

    def test_business_has_exact_contract_and_projected_geometry(self):
        result = build_business(self.source)

        self.assertEqual(
            result.columns.tolist(),
            [
                "denue_id",
                "clee",
                "establishment_name",
                "scian_code",
                "per_ocu_label",
                "alta_date",
                "cvegeo",
                "cvegeo_reported",
                "geometry",
            ],
        )
        self.assertEqual(str(result["denue_id"].dtype), "int64")
        self.assertEqual(result.crs.to_epsg(), 6372)
        self.assertEqual(result.loc[0, "cvegeo_reported"], "310500001001A")
        self.assertIs(type(result.loc[0, "alta_date"]), date)
        self.assertEqual(result.loc[0, "alta_date"], date(2020, 1, 1))
        self.assertTrue(result["denue_id"].is_unique)

    def test_business_rejects_unknown_employment_bands(self):
        source = self.source.copy()
        source.loc[0, "per_ocu"] = "unknown"

        with self.assertRaisesRegex(ValueError, "employment band"):
            build_business(source)


if __name__ == "__main__":
    unittest.main()
