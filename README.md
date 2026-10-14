# Trifillakia autopost (@trifillakiagr)

Αυτόματες κάρτες για όλα τα τμήματα του Παναθηναϊκού σε Instagram (post + story) και Facebook (post + story). Δεν συνδέεται με το site.

| Κάρτα | Πότε |
|---|---|
| **GAME DAY** | 10:00 την ημέρα του αγώνα (ή 3 ώρες πριν, αν ο αγώνας είναι νωρίτερα) |
| **FULL TIME** | στον επόμενο έλεγχο μετά το τέλος (κάθε 5 λεπτά) |
| **ΒΑΘΜΟΛΟΓΙΑ** | όταν τελειώσει η αγωνιστική (το αργότερο 48 ώρες μετά τον αγώνα μας) |
| **MVP** | EuroLeague & Stoiximan GBL: ο παίκτης μας με το μεγαλύτερο PIR, μόλις βγουν τα στατιστικά |

Τμήματα: ποδόσφαιρο, μπάσκετ, βόλεϊ ανδρών, βόλεϊ γυναικών, μπάσκετ γυναικών, ποδόσφαιρο γυναικών, πόλο, σε όλες τις διοργανώσεις.

Πηγές: Flashscore (πρόγραμμα, σκορ, σκόρερ, βαθμολογίες), API της EuroLeague και esake.gr (MVP).

## Εγκατάσταση (μία φορά)

1. **GitHub**: φτιάξε ένα repository (μπορεί να είναι private), π.χ. `trifillakia-autopost`, και ανέβασε όλο αυτόν τον φάκελο.
2. **Meta**: η σελίδα Facebook του Trifillakia πρέπει να είναι συνδεδεμένη με το Instagram @trifillakiagr (Business/Creator).
   Στο Meta Business → Χρήστες συστήματος, φτιάξε token με δικαιώματα `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`, `instagram_basic`, `instagram_content_publish`, `business_management` (ίδια διαδικασία με bala24/totalbasket).
3. Στο repository: **Settings → Secrets and variables → Actions → New repository secret**:
   - `META_TOKEN`: το token
   - `FB_PAGE_ID`: το ID της σελίδας Facebook
   - `IG_USER_ID` (προαιρετικό): το Instagram Business ID· αν λείπει, βρίσκεται από τη σελίδα
4. **Actions → Trifillakia autopost → Run workflow → mode: check** για να ελέγξεις τη σύνδεση, και **mode: dry** για κάρτες χωρίς ανάρτηση. Κατέβασε το artifact `cards-…` για να δεις τις κάρτες. Μετά δουλεύει μόνο του κάθε 5 λεπτά.

Χωρίς τα `META_TOKEN` και `FB_PAGE_ID` δεν αναρτάται τίποτα· οι κάρτες φτιάχνονται μόνο ως artifact.

Την πρώτη φορά που τρέχει, ό,τι έχει ήδη παιχτεί σημειώνεται ως «έγινε», ώστε να μην αναρτηθούν παλιοί αγώνες.

## Ρυθμίσεις

Στο `bot/config.py`:
- hashtags και mentions ανά τμήμα (π.χ. `@paobcgr`, `@panathinaikos_1908`)
- ονόματα διοργανώσεων στις κάρτες (`COMP_NAMES`)
- ώρα GAME DAY, πόσο περιμένει η βαθμολογία, πόσο ψάχνει για MVP

Καλύτερα σήματα ομάδων: βάλε `logos/<flashscore-id>.png` (π.χ. `logos/hnzvnHPS.png` για τον Ολυμπιακό). Χωρίς αυτό μπαίνει το σήμα του Flashscore μεγεθυμένο.

Logos διοργανώσεων: `logos/comp/<flashscore tour id>.png`. Υπάρχουν ήδη τα επίσημα για EuroLeague, Stoiximan GBL, Stoiximan Super League, Superbet Κύπελλο Ελλάδας, Conference League, Novibet Volley League, CEV Champions League, CEV Challenge Cup, Allwyn WBL1, EuroCup Women, EuroLeague Women. Για τις υπόλοιπες μπαίνει το logo του Flashscore μέχρι να προστεθεί αρχείο (τα ids γράφονται στο log όταν τρέχει).

## Συχνότητα (cron-job.org)

Το GitHub τρέχει το πρόγραμμα του workflow μόνο περίπου κάθε 30 λεπτά. Για έλεγχο κάθε 5 λεπτά, το cron-job.org (job «Trifillakia autopost») στέλνει POST στο
`https://api.github.com/repos/matthaios13/trifillakia-autopost/actions/workflows/autopost.yml/dispatches`
με body `{"ref":"main","inputs":{"mode":"run"}}` και header `Authorization: Bearer <GitHub token>`.

Ο GitHub token (fine-grained, μόνο αυτό το repository, Actions: Read and write) **λήγει 29/9/2027**. Ανανέωση: νέος token στο github.com/settings/personal-access-tokens/new → cron-job.org → Edit → Advanced → Headers → Authorization.

## Τοπικά

```bash
pip install -r requirements.txt
python -m bot preview            # κάρτες δείγματα στο out/preview/
python -m bot preview basketball # μόνο ένα τμήμα
DRY_RUN=1 python -m bot run      # ένας έλεγχος χωρίς ανάρτηση
```

## Σημειώσεις

- Τα scheduled workflows του GitHub μπορεί να καθυστερήσουν λίγα λεπτά σε ώρες αιχμής, οπότε το FULL TIME βγαίνει συνήθως 5–15 λεπτά μετά τη λήξη.
- Το GitHub σταματά τα scheduled workflows μετά από 60 μέρες χωρίς commit. Το bot κάνει commit το `state.json` μετά από κάθε ανάρτηση, οπότε όσο υπάρχουν αγώνες μένει ενεργό.
- Οι φωτογραφίες MVP στην EuroLeague έρχονται από το API της EuroLeague.
