"""
Scrape full draw rankings for all junior tournaments (last 12 months).
Processes one tournament at a time and saves each to data/draws/{key}.csv.
Skips tournaments already saved (safe to resume after interruption).
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
import re, csv, os, time

BASE = "https://www.tournamentsoftware.com"

# ── Tournament list ────────────────────────────────────────────────────────────
# tid=None means ID not yet found; those entries will be skipped with a warning.
TOURNAMENTS = [
    # ── 2020-2021 season ─────────────────────────────────────────────────────
    {"key": "2021_Junior_Nationals",     "name": "2021 U.S. Junior Nationals",           "dates": "2021-06-21/2021-06-28", "tid": "2D2FC227-4ADA-46F7-AB81-6D317BE065EB"},
    {"key": "2021_PanAm_Selection",      "name": "2021 Pan Am Junior Selection",         "dates": "2021-08-06/2021-08-08", "tid": "2E0F476B-6A60-43D5-A5EB-067B0A43261F"},
    {"key": "2021_South_OLC",            "name": "2021 USAB South OLC",                  "dates": "2021-08-07/2021-08-08", "tid": "FE6CE881-C6BA-4D12-ACCA-2C2C4D3687E1"},

    # ── 2021-2022 season ─────────────────────────────────────────────────────
    {"key": "2021_Egret_MW_OLC",         "name": "2021 Egret Midwest OLC",               "dates": "2021-11-06/2021-11-07", "tid": "122A5677-AC44-4D7F-8805-5BD299103C82"},
    {"key": "2021_NorCal_CRC",           "name": "2021 NorCal CRC",                      "dates": "2021-11-11/2021-11-14", "tid": "162A5244-5E15-4991-A673-F934A7DCD6E9"},
    {"key": "2021_NW_CRC",               "name": "2021 NW CRC",                          "dates": "2021-11-20/2021-11-21", "tid": "840622A6-46B1-4C0E-A1C0-716967736F7F"},
    {"key": "2021_NE_ORC_U11U13",        "name": "2021 NE ORC (U11-U13)",                "dates": "2021-11-26/2021-11-28", "tid": "9F86740D-8443-47A1-93AA-CB1CFC6C8F97"},
    {"key": "2021_NE_ORC_U15U19",        "name": "2021 NE ORC (U15-U19)",                "dates": "2021-11-26/2021-11-28", "tid": "B826AD25-E5CF-494F-A244-B27596184A19"},
    {"key": "2021_HPBC_NW_ORC",          "name": "2021 HPBC NW ORC",                     "dates": "2021-12-18/2021-12-20", "tid": "9538C0B6-8BA1-4446-B900-821DD2AD5D1D"},
    {"key": "2021_SoCal_ORC",            "name": "2021 SoCal SGVBC ORC",                 "dates": "2021-12-27/2021-12-29", "tid": "AC640A87-C191-4A6C-964C-EEEDE448B5A2"},
    {"key": "2022_South_Frisco_ORC",     "name": "2022 South Frisco ORC",                "dates": "2022-01-15/2022-01-17", "tid": "A2E49C64-3C68-46DA-B4A3-2AF1D2C758CB"},
    {"key": "2022_NE_CRC",               "name": "2022 NE CRC",                          "dates": "2022-02-12/2022-02-13", "tid": "E31BC008-0B26-435B-B007-DCAA2B111C67"},
    {"key": "2022_Synergy_NorCal_ORC",   "name": "2022 Synergy NorCal ORC",              "dates": "2022-02-19/2022-02-21", "tid": "E61953B0-2EDB-418D-9FE7-AA7893723087"},
    {"key": "2022_Midwest_CRC",          "name": "2022 Midwest CRC",                     "dates": "2022-02-26/2022-02-27", "tid": "461D5C31-33DE-41C2-BF3C-AF53FA59F58C"},
    {"key": "2022_Dave_Freeman_OLC",     "name": "2022 Dave Freeman OLC",                "dates": "2022-02-26/2022-02-27", "tid": "7D736C11-8572-4BA4-AF92-558021586DCE"},
    {"key": "2022_SoCal_Arena_CRC",      "name": "2022 SoCal Arena CRC",                 "dates": "2022-03-12/2022-03-13", "tid": "A9E88A79-6344-4A00-B154-E76A0D304DA0"},
    {"key": "2022_South_Houston_CRC",    "name": "2022 South Houston CRC",               "dates": "2022-03-19/2022-03-20", "tid": "7CCA3375-4F51-431D-89A2-BF6A80727DE8"},
    {"key": "2022_NE_OLC",               "name": "2022 NE NJBC OLC",                     "dates": "2022-03-26/2022-03-27", "tid": "7DB07BDF-87DE-4061-B0DA-E5C391A62B89"},
    {"key": "2022_US_Selection",         "name": "2022 U.S. Selection Event",            "dates": "2022-04-15/2022-04-18", "tid": "D049FB41-9E0F-4741-AF06-3C1A61E981A4"},
    {"key": "2022_South_Frisco_U11_OLC", "name": "2022 South Frisco U11 OLC",            "dates": "2022-04-16/2022-04-17", "tid": "733C0B86-6C3A-48DC-8353-A11D5E181FC6"},
    {"key": "2022_NW_Oregon_OLC",        "name": "2022 NW Oregon OLC",                   "dates": "2022-05-07/2022-05-08", "tid": "A4F63553-4106-46DA-954F-6AB2794E1498"},
    {"key": "2022_SPBA_MW_ORC",          "name": "2022 SPBA Midwest ORC",                "dates": "2022-05-28/2022-05-30", "tid": "15617B9A-42E2-4961-9D2D-ED9ABA8041BB"},

    # ── 2022-2023 season ─────────────────────────────────────────────────────
    {"key": "2022_NW_ORC",               "name": "2022 NW ORC",                          "dates": "2022-09-03/2022-09-05", "tid": "73413AC4-DE0B-42F0-9BDD-8C1B5652F37D"},
    {"key": "2022_NE_ORC_U11U13",        "name": "2022 NE ORC (U11/U13)",                "dates": "2022-10-08/2022-10-10", "tid": "6FFAB52D-C9F9-4966-98D6-F817942A0BB3"},
    {"key": "2022_NE_ORC_U15U19",        "name": "2022 NE ORC (U15/U17/U19)",            "dates": "2022-10-08/2022-10-10", "tid": "DBCBE1A0-A09B-43C4-BF7E-17EB3E827AF2"},
    {"key": "2022_NorCal_ORC",           "name": "2022 NorCal ORC",                      "dates": "2022-11-11/2022-11-13", "tid": "F45D3E83-9C4D-462E-A7BA-FC0C633936DF"},
    {"key": "2022_SoCal_CRC",            "name": "2022 SoCal CRC",                       "dates": "2022-12-03/2022-12-04", "tid": "A3A96C7F-ADD3-42AA-839B-BFF55EEA1202"},
    {"key": "2022_Midwest_CRC2",         "name": "2022 Egret Midwest CRC",               "dates": "2022-12-03/2022-12-04", "tid": "B6B8B4C8-5844-4867-A8C5-16163423A79B"},
    {"key": "2023_South_ORC",            "name": "2023 South ORC",                       "dates": "2023-01-14/2023-01-16", "tid": "5E3FCB8C-5655-4CAA-B9C9-9B247022A79F"},
    {"key": "2023_NE_OLC",               "name": "2023 NE OLC",                          "dates": "2023-02-04/2023-02-05", "tid": "7B9BA7B8-4A50-4007-96F8-1C79BB1D2A9C"},
    {"key": "2023_SoCal_ORC",            "name": "2023 SoCal ORC",                       "dates": "2023-02-18/2023-02-20", "tid": "69535E3A-281A-4C8F-8F08-5CC1CEDEF3AB"},
    {"key": "2023_Dave_Freeman_OLC",     "name": "2023 Dave Freeman Jr OLC",             "dates": "2023-02-25/2023-02-26", "tid": "58905B24-6955-47B0-B93B-EB43EDF22B3F"},
    {"key": "2023_Midwest_OLC",          "name": "2023 Midwest OLC",                     "dates": "2023-02-25/2023-02-26", "tid": "05A8EC8C-10E8-467C-A652-FEDCD4F9F73F"},
    {"key": "2023_South_CRC",            "name": "2023 South CRC",                       "dates": "2023-03-11/2023-03-12", "tid": "E7C833DA-AD99-4728-A59A-71D90E259331"},
    {"key": "2023_MassBad_NE_OLC",       "name": "2023 MassBad NE OLC",                  "dates": "2023-03-24/2023-03-26", "tid": "1EA74CD3-26FE-4F93-A2BE-47D52A3728C8"},
    {"key": "2023_US_Selection",         "name": "2023 U.S. Selection Event",            "dates": "2023-04-07/2023-04-10", "tid": "DB1BE00A-872B-46E5-A88B-74E867541E6D"},
    {"key": "2023_NW_OLC",               "name": "2023 NW OLC",                          "dates": "2023-04-28/2023-04-30", "tid": "4D2E4B32-55B9-409C-AA90-57482B88DD31"},
    {"key": "2023_South_OLC",            "name": "2023 South OLC",                       "dates": "2023-05-06/2023-05-07", "tid": "4AC4CE72-C1BA-46FF-8322-0775CCFFDAA8"},
    {"key": "2023_Midwest_ORC",          "name": "2023 Midwest ORC",                     "dates": "2023-05-27/2023-05-29", "tid": "F00EFC16-68DC-4AEB-A82D-05F6D49E66EC"},
    {"key": "2023_Junior_Nationals",     "name": "2023 U.S. Junior Nationals",           "dates": "2023-06-25/2023-07-02", "tid": "01556CED-F10F-405F-B773-5F32DE6B22B7"},

    # ── 2023-2024 season ─────────────────────────────────────────────────────
    {"key": "2023_NE_ORC_U11",           "name": "2023 NE ORC (U11)",                    "dates": "2023-10-07/2023-10-09", "tid": "1D619BDD-7289-4F4E-922E-33B9A23B0859"},
    {"key": "2023_NE_ORC_U13U15",        "name": "2023 NE ORC (U13/U15)",                "dates": "2023-10-07/2023-10-09", "tid": "68B85739-9672-495A-874F-C34127CAFD1E"},
    {"key": "2023_NE_ORC_U17U19",        "name": "2023 NE ORC (U17/U19)",                "dates": "2023-10-07/2023-10-09", "tid": "B1E7415F-FE25-48E4-B55B-902C70BA9CDC"},
    {"key": "2023_TBTT_South_OLC",       "name": "2023 South OLC (TBTT)",                "dates": "2023-12-02/2023-12-03", "tid": "C5331C39-089A-4691-AF78-E0750A7D3132"},
    {"key": "2023_SGVBC_SoCal_CRC",      "name": "2023 SoCal CRC (SGVBC)",               "dates": "2023-12-02/2023-12-03", "tid": "966DF4CC-379E-4401-9CF3-7419759AC028"},
    {"key": "2023_Egret_MW_OLC",         "name": "2023 Egret Midwest OLC",               "dates": "2023-12-09/2023-12-10", "tid": "E9AEADD8-0B9F-4626-801C-9A3F600D144D"},
    {"key": "2023_NVBC_NE_OLC",          "name": "2023 NE OLC (NVBC)",                   "dates": "2023-12-15/2023-12-17", "tid": "76A3DD6B-7EA1-4B41-8841-317EF58023C8"},
    {"key": "2024_South_ORC",            "name": "2024 Frisco South ORC",                "dates": "2024-01-13/2024-01-15", "tid": "50F7886A-E267-46E3-ACB0-47EECB226031"},
    {"key": "2024_SoCal_JrDev",          "name": "2024 SoCal Jr Dev Championships",      "dates": "2024-01-20/2024-01-21", "tid": "326B8050-F60D-462D-9DD1-6573845322B9"},
    {"key": "2024_DFW_South_OLC",        "name": "2024 DFW South OLC",                   "dates": "2024-02-03/2024-02-04", "tid": "E140BEF5-2C4E-4F77-840D-2218AE03879D"},
    {"key": "2024_SoCal_ORC",            "name": "2024 SoCal ORC / Shonai",              "dates": "2024-02-17/2024-02-19", "tid": "D47E7D45-BE8E-4BDD-B09E-21DCA2E509E2"},
    {"key": "2024_NE_MassBad_OLC",       "name": "2024 NE MassBad OLC",                  "dates": "2024-02-23/2024-02-25", "tid": "457E16EA-F589-470C-B317-CED853EEEBAA"},
    {"key": "2024_Midwest_CRC",          "name": "2024 Midwest CRC",                     "dates": "2024-02-24/2024-02-25", "tid": "88F17126-9D0E-4153-A9D6-4FA118131FFF"},
    {"key": "2024_ABC_Open",             "name": "2024 ABC Open",                        "dates": "2024-03-08/2024-03-10", "tid": "845A0F44-934B-4DE8-9725-0EA70AC842D9"},
    {"key": "2024_ABC_OLC",              "name": "2024 ABC OLC",                         "dates": "2024-03-08/2024-03-10", "tid": "7D57F24E-5346-4540-B486-19DB5750C014"},
    {"key": "2024_TBTT_South_CRC",       "name": "2024 South CRC (TBTT)",                "dates": "2024-03-09/2024-03-10", "tid": "B3633DE6-69B3-4BDC-B6A4-E61F4907E353"},
    {"key": "2024_US_Selection",         "name": "2024 U.S. Selection Event",            "dates": "2024-03-29/2024-04-01", "tid": "DB1BE00A-872B-46E5-A88B-74E867541E6D"},
    {"key": "2024_NE_CRC",               "name": "2024 NE CRC (NJBC)",                   "dates": "2024-04-19/2024-04-21", "tid": "4C6AEB86-9EEA-42D0-907F-964AB20EB6CF"},
    {"key": "2024_Dave_Freeman_OLC",     "name": "2024 Dave Freeman Jr OLC",             "dates": "2024-04-27/2024-04-28", "tid": "EE2741A5-A966-4C9E-A095-29F7FDE42D3E"},
    {"key": "2024_OBA_NW_OLC",           "name": "2024 OBA NW OLC",                      "dates": "2024-05-10/2024-05-12", "tid": "E6CDA88C-9C0E-4A22-921F-89EB4045362D"},
    {"key": "2024_SPBA_MW_ORC",          "name": "2024 SPBA Midwest ORC",                "dates": "2024-05-25/2024-05-27", "tid": "13BFD913-52BF-4986-84F1-08ECE4B947BA"},
    {"key": "2024_South_OLC",            "name": "2024 South OLC (Nets & Turf)",         "dates": "2024-06-07/2024-06-09", "tid": "A23410CB-9045-4CB9-AD62-C0AFE797F4C5"},
    {"key": "2024_NE_OLC",               "name": "2024 NE OLC (NVBC)",                   "dates": "2024-06-14/2024-06-16", "tid": "D2BDAC36-F32F-43ED-A90E-15F43E4CF90F"},
    {"key": "2024_Junior_Nationals",     "name": "2024 U.S. Junior Nationals",           "dates": "2024-07-02/2024-07-08", "tid": "BE1D8386-1356-4B85-91F8-F6D547B2C7B1"},

    # ── 2024-2025 season ─────────────────────────────────────────────────────
    {"key": "2024_Bellevue_NW_ORC",      "name": "2024 Bellevue NW ORC",                 "dates": "2024-08-31/2024-09-02", "tid": "A7A8ADBC-267C-4A11-AB5F-65CF7135CEEC"},
    {"key": "2024_Capital_NE_ORC",       "name": "2024 Capital NE ORC (U11/U17/U19)",    "dates": "2024-10-12/2024-10-14", "tid": "969F86FC-F184-476B-BAC7-D0D8DCB9D4DB"},
    {"key": "2024_NVBC_NE_ORC",          "name": "2024 NVBC NE ORC (U13/U15)",           "dates": "2024-10-12/2024-10-14", "tid": "72B4FE42-7C81-4A2D-BF71-6BFEEA76BE68"},
    {"key": "2024_Synergy_NorCal_ORC",   "name": "2024 Synergy NorCal ORC",              "dates": "2024-11-09/2024-11-11", "tid": "06F5E427-B35C-4357-8F9C-AF31E4D3602B"},
    {"key": "2024_MBC_MW_OLC",           "name": "2024 MBC Midwest OLC",                 "dates": "2024-11-23/2024-11-24", "tid": "1C0EF623-420D-42E8-BBEB-06953C77FE71"},
    {"key": "2024_SBC_NW_CRC",           "name": "2024 SBC NW CRC",                      "dates": "2024-12-07/2024-12-08", "tid": "B1B12EBB-5F9F-419F-9807-20348BD5CE1C"},
    {"key": "2024_SGVBC_SoCal_CRC",      "name": "2024 SGVBC SoCal CRC",                 "dates": "2024-12-07/2024-12-08", "tid": "3437BDDD-5D97-4A38-805C-D934949ACAAB"},
    {"key": "2024_NE_NJBC_CRC",          "name": "2024 NE NJBC CRC",                     "dates": "2024-12-13/2024-12-15", "tid": "8E022A4D-C618-498A-A6CD-5DA1DB92D92E"},
    {"key": "2025_Arena_SoCal_ORC",      "name": "2025 Arena SoCal ORC",                 "dates": "2025-01-18/2025-01-20", "tid": "99B06E11-7C7F-41DF-9DB6-7087B29FD72A"},
    {"key": "2025_Egret_MW_CRC",         "name": "2025 Egret MW CRC",                    "dates": "2025-01-25/2025-01-26", "tid": "5465A21A-CA81-4571-BE22-1957930E2C58"},
    {"key": "2025_DFW_South_ORC",        "name": "2025 DFW South ORC / Shonai",          "dates": "2025-02-15/2025-02-17", "tid": "BB09B547-0989-49FE-A3FA-710669CD3D9B"},
    {"key": "2025_NE_MassBad_OLC",       "name": "2025 NE MassBad OLC",                  "dates": "2025-02-28/2025-03-02", "tid": "E6C0A995-9E65-427B-87AB-468A31B36384"},
    {"key": "2025_PanAm_Selection",      "name": "2025 Junior Pan Am Selection",         "dates": "2025-02-28/2025-03-02", "tid": "38882A3E-16F7-4A15-B108-32475CA67B90"},
    {"key": "2025_ABC_Open",             "name": "2025 ABC Open",                        "dates": "2025-03-21/2025-03-23", "tid": "EC3304EB-15BB-4D2B-9D6D-AB46064E312C"},
    {"key": "2025_ABC_OLC",              "name": "2025 ABC NorCal OLC",                  "dates": "2025-03-21/2025-03-23", "tid": "4795C1C3-9F40-4DFA-88C6-FC7659DC087D"},
    {"key": "2025_Austin_South_CRC",     "name": "2025 Austin Leander South CRC",        "dates": "2025-03-22/2025-03-23", "tid": "5F149ED1-2D29-4EBF-AE9A-4B3D87D22A2B"},
    {"key": "2025_Schafer_SLG_OLC",      "name": "2025 Schafer SLG South OLC",           "dates": "2025-04-05/2025-04-06", "tid": "487763D5-0AD2-4378-9B51-6E1BD3F84CE5"},
    {"key": "2025_Dave_Freeman_OLC",     "name": "2025 YONEX Dave Freeman Jr. SoCal OLC","dates": "2025-04-12/2025-04-13", "tid": "CF544139-F12A-4B99-A9B9-41E28C9F8266"},
    {"key": "2025_Peak_Sports_OLC",      "name": "2025 Peak Sports South OLC",           "dates": "2025-04-12/2025-04-13", "tid": "66D14DB5-408F-4C65-8400-9E916F6FA5DD"},
    {"key": "2025_US_Selection",         "name": "2025 YONEX U.S. Selection Event",      "dates": "2025-04-18/2025-04-21", "tid": "E5F301F7-ADE5-4AEF-8941-FAD832AEF8F8"},
    {"key": "2025_OBA_NW_OLC",           "name": "2025 OBA NW OLC",                      "dates": "2025-04-26/2025-04-27", "tid": "02D88A67-9666-4648-BE4E-8169AC28A321"},
    {"key": "2025_SPBA_Midwest_ORC",     "name": "2025 YONEX SPBA Midwest ORC",          "dates": "2025-05-24/2025-05-26", "tid": "46A4D2FD-F074-4F11-A86B-34F1ED3E6EC4"},
    {"key": "2025_CanAm_NorCal_OLC",     "name": "2025 CAN-AM Elite NorCal OLC",         "dates": "2025-06-13/2025-06-15", "tid": "56C224B4-0D68-40C6-A8F6-AB16F524C80A"},
    {"key": "2025_Junior_Nationals",     "name": "2025 YONEX U.S. Junior Nationals",     "dates": "2025-07-01/2025-07-07", "tid": "A2DD0F5E-24A4-4875-B053-8F25F31AC357"},

    # ── 2025-2026 season ─────────────────────────────────────────────────────
    {"key": "2025_Bellevue_NW_ORC",      "name": "2025 YONEX Bellevue NW ORC",           "dates": "2025-08-30/2025-09-01", "tid": "D96AD8D0-A9D8-4679-939E-82E9963A49A7"},
    {"key": "2025_Austin_South_OLC",     "name": "2025 Austin Leander South OLC",        "dates": "2025-09-20/2025-09-21", "tid": "376A120B-F979-495B-9799-ED548D9A1E7E"},
    {"key": "2025_LIBC_NE_ORC",          "name": "2025 YONEX LIBC NE ORC",               "dates": "2025-10-11/2025-10-13", "tid": "40CE63A2-430A-4C56-80C7-2DBD701A9019"},
    {"key": "2025_Synergy_NorCal_ORC",   "name": "2025 YONEX Synergy NorCal ORC",        "dates": "2025-11-08/2025-11-10", "tid": "A3D197AE-C74C-41BF-9C66-F91B7576B77A"},
    {"key": "2025_Egret_Midwest_OLC",    "name": "2025 Egret Midwest OLC",               "dates": "2025-11-22/2025-11-23", "tid": "F1D5FE50-3A8A-4C5A-8A55-71BE130B6EC3"},
    {"key": "2025_Schafer_SLG_OLC2",     "name": "2025 Schafer SLG South OLC (2025-26)", "dates": "2025-11-29/2025-11-30", "tid": "75548892-B29A-420B-9951-973C8C9F2D68"},
    {"key": "2025_Fortius_South_CRC",    "name": "2025 Fortius South CRC",               "dates": "2025-12-05/2025-12-07", "tid": "22C92233-478E-4239-BCF3-A3A9A054BA2C"},
    {"key": "2025_SGVBC_SoCal_CRC",      "name": "2025 SGVBC SoCal CRC",                 "dates": "2025-12-06/2025-12-07", "tid": "FEAC4C02-C295-4225-AA82-CFCBA83B2834"},
    {"key": "2025_Capital_NE_OLC",       "name": "2025 Capital NE OLC",                  "dates": "2025-12-12/2025-12-14", "tid": "86C3EAAF-BA94-42DB-9110-7CD31A5810FD"},
    {"key": "2025_Peak_Sports_OLC2",     "name": "2025 Peak Sports South OLC (Dec)",     "dates": "2025-12-20/2025-12-21", "tid": "78DDAE7C-34D9-4775-81F2-23C18EAC9265"},
    {"key": "2026_Wayside_NE_CRC",       "name": "2026 Wayside NE CRC",                  "dates": "2026-01-03/2026-01-04", "tid": "937ACE29-5F1C-4E39-B3FC-DE5DC9F67A6E"},
    {"key": "2026_CBA_Midwest_OLC",      "name": "2026 CBA Midwest OLC",                 "dates": "2026-01-10/2026-01-11", "tid": "58FD9D91-2FE9-4613-9E59-6D56ADE8BF5B"},
    {"key": "2026_Arena_SoCal_ORC",      "name": "2026 YONEX Arena SoCal ORC",           "dates": "2026-01-17/2026-01-19", "tid": "239635E4-C300-4F6A-A364-7062F0430F30"},
    {"key": "2026_DFW_South_ORC",        "name": "2026 YONEX DFW South ORC",             "dates": "2026-02-14/2026-02-16", "tid": "4C4A21C2-E62B-4448-8B0D-12AEE6263B99"},
    {"key": "2026_Dave_Freeman_OLC",     "name": "2026 Dave Freeman Jr. SoCal OLC",      "dates": "2026-02-20/2026-02-22", "tid": "45D5792F-78E5-43B1-8D72-898357052913"},
    {"key": "2026_Seattle_NW_CRC",       "name": "2026 Seattle NW CRC",                  "dates": "2026-02-21/2026-02-22", "tid": "EF556B64-3B34-438D-853D-8812143EC357"},
    {"key": "2026_PlayNThrive_MW_CRC",   "name": "2026 Play N Thrive MW CRC",            "dates": "2026-02-28/2026-03-01", "tid": "AB29A304-A807-4A9B-8B2F-DD33BD545B91"},
]

OUT_DIR = "data/draws"
os.makedirs(OUT_DIR, exist_ok=True)

FIELDS = ['tournament','dates','event','player','seed','state','draw_pos','rank_lo','rank_hi','elim_round']

# ── Session ────────────────────────────────────────────────────────────────────
def make_session(tid):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    s.get(f"{BASE}/cookiewall/?returnurl=%2Ftournament%2F{tid}")
    s.post(f"{BASE}/cookiewall/Save", data={
        "ReturnUrl": f"/tournament/{tid}",
        "SettingsOpen": "false",
        "CookiePurposes": ["1", "2", "4", "16"],
    })
    return s

# ── Draw parser (max-column approach from v3) ──────────────────────────────────
def strip_seed(raw):
    raw = re.sub(r',?\s*WDN', '', raw).strip()
    m = re.search(r'\[([^\]]+)\]$', raw)
    if m:
        return raw[:m.start()].strip(), m.group(1)
    return raw, ''

def parse_draw(html, event_name, tournament_name, dates, use_consolation=False):
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        return []

    table = tables[0]
    rows  = table.find_all("tr")
    if not rows:
        return []

    hdr       = [c.get_text(strip=True) for c in rows[0].find_all(["th","td"])]

    # Detect name_col from the header: player name sits in the first column
    # whose header looks like a round (Round N, Finals, Winner, etc.).
    # Columns labeled 'Club', 'State', '' etc. are metadata before the name.
    ROUND_HDR = re.compile(r'round|final|semi|quarter|winner|group|match|pool', re.I)
    name_col = 2  # fallback
    for i, h in enumerate(hdr):
        if i == 0:
            continue
        if h and ROUND_HDR.search(h):
            name_col = i
            break

    rcols      = {i: h for i, h in enumerate(hdr) if i >= name_col and h}
    if not rcols:
        return []
    winner_col = max(rcols.keys())

    # Pass 1: player metadata from draw-position rows
    player_info = {}
    for row in rows[1:]:
        cells = row.find_all(["td","th"])
        vals  = [c.get_text(strip=True) for c in cells]
        while len(vals) < len(hdr):
            vals.append('')
        if not vals[0].isdigit():
            continue
        draw_pos = int(vals[0])
        state    = vals[name_col - 1] if name_col >= 2 and len(vals) > name_col - 1 else ''
        raw_name = vals[name_col]     if len(vals) > name_col else ''
        if not raw_name or raw_name.lower() == 'bye':
            continue
        pname, seed = strip_seed(raw_name)
        if not pname:
            continue
        if pname not in player_info:
            player_info[pname] = {'seed': seed, 'state': state, 'draw_pos': draw_pos}

    # Pass 2: max column per player across all cells
    player_max_col = {n: name_col for n in player_info}
    for row in rows[1:]:
        cells = row.find_all(["td","th"])
        vals  = [c.get_text(strip=True) for c in cells]
        while len(vals) < len(hdr):
            vals.append('')
        for ci, val in enumerate(vals):
            if ci < name_col or not val:
                continue
            pname, _ = strip_seed(val)
            if pname in player_max_col and ci > player_max_col[pname]:
                player_max_col[pname] = ci

    # 3rd/4th place match: a small table (~ 6 rows) with 2 players from the
    # main draw semi-finals.  The player who appears in the last column wins
    # (rank 3); the other gets rank 4.
    third_place_winner = None
    for extra_table in tables[1:]:
        erows = extra_table.find_all("tr")
        if not (4 <= len(erows) <= 8):
            continue
        # Collect player names and find who reaches the last column
        tbl_players = []
        tbl_winner  = None
        ncols = max(len(row.find_all(["td","th"])) for row in erows)
        for row in erows[1:]:
            vals = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
            # Row with draw position number → find player name in any cell
            if vals and vals[0].isdigit():
                for v in vals[1:]:
                    if not v:
                        continue
                    pname, _ = strip_seed(v)
                    if pname and pname in player_info:
                        tbl_players.append(pname)
                        break
            # Check the last column for the winner (player name, not score)
            if len(vals) >= ncols:
                v = vals[-1]
                if v:
                    pname, _ = strip_seed(v)
                    if pname and pname in player_info:
                        tbl_winner = pname
        if len(tbl_players) == 2 and tbl_winner and tbl_winner in tbl_players:
            third_place_winner = tbl_winner
            break
        # Bye/walkover: only 1 player found → they get 3rd
        if len(tbl_players) == 1:
            third_place_winner = tbl_players[0]
            break

    # Consolation bracket (JN full-seeding style): look for a table whose
    # first header cell is a round label (no leading draw-pos/State columns).
    # Data rows have an extra leading section# cell so data-col = header-col + 1.
    cons_max_col    = {}   # player -> max data-col in consolation table
    cons_min_col    = {}   # player -> min data-col (entry point)
    cons_winner_col = None
    crcols          = {}   # data-col -> round label (using header-col + 1 offset)

    for extra_table in tables[1:]:
        erows = extra_table.find_all("tr")
        if len(erows) < 20:
            continue
        ehdr = [c.get_text(strip=True) for c in erows[0].find_all(["th","td"])]
        if not ehdr or not ROUND_HDR.search(ehdr[0]):
            continue
        # Build label map: data-col index -> round label
        local_crcols = {i + 1: h for i, h in enumerate(ehdr) if h}
        # Scan all data rows for known player names
        cmax = {}
        cmin = {}
        for row in erows[1:]:
            vals = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
            for ci, val in enumerate(vals):
                if not val:
                    continue
                pname, _ = strip_seed(val)
                if pname in player_info:
                    if pname not in cmax or ci > cmax[pname]:
                        cmax[pname] = ci
                    if pname not in cmin or ci < cmin[pname]:
                        cmin[pname] = ci
        if cmax:
            cons_max_col    = cmax
            cons_min_col    = cmin
            cons_winner_col = max(cmax.values())
            crcols          = local_crcols
            break  # use first matching consolation table

    # Build mapping: main-draw rfe -> consolation entry column
    # (for assigning ranks to players not found in consolation)
    cons_entry_by_rfe = {}
    if cons_winner_col is not None:
        from collections import defaultdict
        rfe_entries = defaultdict(list)
        for pname in cons_min_col:
            main_rfe = winner_col - player_max_col[pname]
            rfe_entries[main_rfe].append(cons_min_col[pname])
        for rfe, cols in rfe_entries.items():
            cons_entry_by_rfe[rfe] = min(cols)  # use earliest entry col

    # Compute byes per player for rank adjustment
    bracket_size = 2 ** (winner_col - name_col)
    filled_positions = {info['draw_pos'] for info in player_info.values()}
    player_byes = {}
    for pname_b, info_b in player_info.items():
        pos = info_b['draw_pos']
        byes = 0
        group_size = 2
        while group_size <= bracket_size:
            group_start = ((pos - 1) // group_size) * group_size + 1
            group_end = group_start + group_size - 1
            opponents = [p for p in range(group_start, group_end + 1)
                        if p != pos and p in filled_positions]
            if not opponents:
                byes += 1
                group_size *= 2
            else:
                break
        player_byes[pname_b] = byes

    # Rank assignment
    total_rounds = winner_col - name_col
    results = []
    for pname, info in player_info.items():
        mc  = player_max_col[pname]
        rfe = winner_col - mc
        # Bye correction: if all column advancement is from byes (zero actual wins),
        # treat as first-round loser (rfe = total_rounds)
        cols_advanced = mc - name_col
        byes = player_byes.get(pname, 0)
        if byes > 0 and cols_advanced <= byes:
            rfe = total_rounds

        if rfe == 0:
            rank_lo, rank_hi = 1, 1
            elim_round = 'Winner'
        elif rfe == 1:
            rank_lo, rank_hi = 2, 2
            elim_round = rcols.get(mc, f'col{mc}')
        elif rfe == 2 and third_place_winner is not None:
            # 3rd/4th place match exists — split rank 3 vs 4
            if pname == third_place_winner:
                rank_lo, rank_hi = 3, 3
            else:
                rank_lo, rank_hi = 4, 4
            elim_round = rcols.get(mc, f'col{mc}')
        else:
            rank_lo    = 2 ** (rfe - 1) + 1
            rank_hi    = 2 ** rfe
            elim_round = rcols.get(mc, f'col{mc}')

        # Override with consolation rank if consolation bracket exists
        # Double-elimination: band sizes from winner are 1,1,2,4,4,8,8,16,16,...
        # i.e. band_size = 2^((c_rfe+1)//2) for c_rfe >= 2
        def _cons_rank(c_rfe):
            if c_rfe == 0: return 5, 5
            if c_rfe == 1: return 6, 6
            c_lo = 7
            for r in range(2, c_rfe):
                c_lo += 2 ** ((r + 1) // 2)
            band = 2 ** ((c_rfe + 1) // 2)
            return c_lo, c_lo + band - 1

        if use_consolation and cons_winner_col is not None and rfe >= 2:
            if pname in cons_max_col:
                # Player found in consolation — use their exit column
                cmc   = cons_max_col[pname]
                c_rfe = cons_winner_col - cmc
                c_lo, c_hi = _cons_rank(c_rfe)
                c_label = crcols.get(cmc, f'Cons col{cmc}')
                rank_lo    = c_lo
                rank_hi    = c_hi
                elim_round = f'C:{c_label}'
            elif rfe in cons_entry_by_rfe:
                # Player not in consolation (withdrew) — rank as if they
                # lost at their consolation entry point
                entry_col = cons_entry_by_rfe[rfe]
                c_rfe = cons_winner_col - entry_col
                c_lo, c_hi = _cons_rank(c_rfe)
                c_label = crcols.get(entry_col, f'Cons col{entry_col}')
                rank_lo    = c_lo
                rank_hi    = c_hi
                elim_round = f'C:{c_label} (W/O)'

        results.append({
            'tournament': tournament_name,
            'dates':      dates,
            'event':      event_name,
            'player':     pname,
            'seed':       info['seed'],
            'state':      info['state'],
            'draw_pos':   info['draw_pos'],
            'rank_lo':    rank_lo,
            'rank_hi':    rank_hi,
            'elim_round': elim_round,
        })

    return sorted(results, key=lambda x: (x['rank_lo'], x['draw_pos']))

# ── Main loop ──────────────────────────────────────────────────────────────────
skipped_no_tid  = []
skipped_done    = []
processed       = []
failed          = []

for t in TOURNAMENTS:
    key   = t["key"]
    name  = t["name"]
    dates = t["dates"]
    tid   = t["tid"]
    out   = f"{OUT_DIR}/{key}.csv"

    print(f"\n{'='*70}")
    print(f"Tournament: {name}  ({dates})")

    if tid is None:
        print(f"  SKIP — tournament ID not yet known")
        skipped_no_tid.append(name)
        continue

    if os.path.exists(out):
        import csv as _csv
        with open(out, encoding='utf-8') as f:
            n = sum(1 for _ in f) - 1  # subtract header
        print(f"  SKIP — already saved ({n} rows in {out})")
        skipped_done.append(name)
        continue

    try:
        session = make_session(tid)

        r = session.get(f"{BASE}/sport/draws.aspx?id={tid}", timeout=20)
        soup2 = BeautifulSoup(r.text, "lxml")
        draws = []
        for a in soup2.find_all("a", href=True):
            m = re.search(r'draw\.aspx\?id=.+&draw=(\d+)', a["href"])
            if m:
                draws.append((int(m.group(1)), a.get_text(strip=True)))

        if not draws:
            print(f"  WARNING — no draws found")
            failed.append(name)
            continue

        print(f"  Found {len(draws)} draws")
        all_results = []

        for draw_num, event_name in draws:
            r2 = session.get(f"{BASE}/sport/draw.aspx?id={tid}&draw={draw_num}", timeout=20)
            time.sleep(0.3)
            is_jn = "Junior_Nationals" in key
            results = parse_draw(r2.text, event_name, name, dates, use_consolation=is_jn)
            all_results.extend(results)

            rnk1 = [p['player'] for p in results if p['rank_lo'] == 1]
            print(f"  {event_name:<30} {len(results):>4} players   winner: {', '.join(rnk1) if rnk1 else '?'}")

        # Save
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            w.writeheader()
            w.writerows(all_results)

        print(f"  Saved {len(all_results)} rows -> {out}")
        processed.append((name, len(all_results)))

    except Exception as e:
        print(f"  ERROR: {e}")
        failed.append(name)

    time.sleep(1)  # polite pause between tournaments

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"DONE")
print(f"  Processed:      {len(processed)}")
print(f"  Already done:   {len(skipped_done)}")
print(f"  No ID yet:      {len(skipped_no_tid)}")
print(f"  Failed:         {len(failed)}")
if skipped_no_tid:
    print(f"\nMissing IDs:")
    for n in skipped_no_tid:
        print(f"  - {n}")
if failed:
    print(f"\nFailed:")
    for n in failed:
        print(f"  - {n}")
