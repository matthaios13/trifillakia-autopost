"""Ρυθμίσεις: τμήματα του Παναθηναϊκού, hashtags, mentions, ώρες ανάρτησης."""
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Athens")

# Τα τμήματα: κλειδί => Flashscore id ομάδας, sport path, ετικέτα κάρτας, emoji, σήμα ΠΑΟ, hashtags, mentions.
TEAMS = {
    "football": {
        "fs": "panathinaikos/SENMmweG",
        "sport": "football",
        "label": "ΠΟΔΟΣΦΑΙΡΟ",
        "name": "Ποδόσφαιρο",
        "emoji": "⚽",
        "crest": "pao_fc.png",
        "tags": "#PAOFC #Panathinaikos #PanathinaikosFC #PAO #Παναθηναϊκός #Τριφύλλι #trifillakiagr",
        "mentions": "@fcpanathinaikos",
    },
    "basketball": {
        "fs": "panathinaikos/bqRyXX9C",
        "sport": "basketball",
        "label": "ΜΠΑΣΚΕΤ",
        "name": "Μπάσκετ",
        "emoji": "🏀",
        "crest": "pao_bc.png",
        "tags": "#PAOBC #PAOBCAktor #Panathinaikos #PanathinaikosBC #Παναθηναϊκός #Τριφύλλι #trifillakiagr",
        "mentions": "@paobcgr",
    },
    "volley_m": {
        "fs": "panathinaikos/d0FeiWQ6",
        "sport": "volleyball",
        "label": "ΒΟΛΕΪ ΑΝΔΡΩΝ",
        "name": "Βόλεϊ Ανδρών",
        "emoji": "🏐",
        "crest": "pao_ao.png",
        "tags": "#Panathinaikos #PAOVolley #Παναθηναϊκός #Τριφύλλι #trifillakiagr",
        "mentions": "@panathinaikos_1908",
    },
    "volley_w": {
        "fs": "panathinaikos/QN7ZELZa",
        "sport": "volleyball",
        "label": "ΒΟΛΕΪ ΓΥΝΑΙΚΩΝ",
        "name": "Βόλεϊ Γυναικών",
        "emoji": "🏐",
        "crest": "pao_ao.png",
        "tags": "#Panathinaikos #PAOVolley #WomensVolleyball #Παναθηναϊκός #trifillakiagr",
        "mentions": "@panathinaikos_1908",
    },
    "basketball_w": {
        "fs": "panathinaikos/plqPE4do",
        "sport": "basketball",
        "label": "ΜΠΑΣΚΕΤ ΓΥΝΑΙΚΩΝ",
        "name": "Μπάσκετ Γυναικών",
        "emoji": "🏀",
        "crest": "pao_ao.png",
        "tags": "#Panathinaikos #WomensBasketball #Παναθηναϊκός #Τριφύλλι #trifillakiagr",
        "mentions": "@panathinaikos_1908",
    },
    "football_w": {
        "fs": "panathinaikos/U133kB5D",
        "sport": "football",
        "label": "ΠΟΔΟΣΦΑΙΡΟ ΓΥΝΑΙΚΩΝ",
        "name": "Ποδόσφαιρο Γυναικών",
        "emoji": "⚽",
        "crest": "pao_fc.png",
        "tags": "#Panathinaikos #WomensFootball #PAO #Παναθηναϊκός #trifillakiagr",
        "mentions": "@panathinaikos_1908 @panathinaikoswomen",
    },
    "waterpolo": {
        "fs": "panathinaikos-wpc/8WFCnEH1",
        "sport": "water-polo",
        "label": "ΠΟΛΟ ΑΝΔΡΩΝ",
        "name": "Πόλο Ανδρών",
        "emoji": "🤽",
        "crest": "pao_ao.png",
        "tags": "#Panathinaikos #WaterPolo #Παναθηναϊκός #Τριφύλλι #trifillakiagr",
        "mentions": "@panathinaikos_1908",
    },
}

# Ονόματα διοργανώσεων όπως θέλουμε να φαίνονται (Flashscore => κάρτα). Ό,τι λείπει μένει όπως έρχεται.
COMP_NAMES = {
    "Ευρωλίγκα": "EuroLeague",
    "Κόνφερενς Λιγκ": "Conference League",
    "Γιουρόπα Λιγκ": "Europa League",
    "Τσάμπιονς Λιγκ": "Champions League",
    "ΓιούροΚαπ Γυναικών": "EuroCup Women",
    "Τσάλεντζ Καπ Γυναίκες": "CEV Challenge Cup",
    "Βόλεϊ Λιγκ Γυναίκες": "Volley League Γυναικών",
    "Σούπερ Καπ Γυναίκες": "Super Cup Γυναικών",
    "Σούπερ Καπ": "Super Cup",
    "WBL1 Γυναίκες": "Basket League Γυναικών",
    "Α Κατηγορία Γυναίκες": "Α' Εθνική Γυναικών",
    "Α1": "Α1 Πόλο",
    "Κύπελλο": "Κύπελλο Ελλάδας",
}

# Game Day: στις 10:00 της ημέρας του αγώνα, ή 3 ώρες πριν αν ο αγώνας είναι νωρίς.
GAMEDAY_HOUR = 10
GAMEDAY_MIN_LEAD_H = 3

# Full Time: μόνο για αγώνες που τελείωσαν τις τελευταίες τόσες ώρες.
FULLTIME_MAX_AGE_H = 12

# Βαθμολογία: όταν τελειώσει η αγωνιστική· αλλιώς το αργότερο τόσες ώρες μετά τον αγώνα μας.
STANDINGS_FALLBACK_H = 48

# MVP (EuroLeague / Stoiximan GBL): αν δεν βρεθούν στατιστικά μέσα σε τόσες ώρες, παραλείπεται.
MVP_GIVE_UP_H = 8
