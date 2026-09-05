# Werkwijze en Richtlijnen voor Clusterlabels (A0 Kaart)

Dit document beschrijft de redactionele principes en de onderzoeksmethodiek voor het bepalen en valideren van de hiërarchische clusterlabels (niveau 0 t/m 4) op de parlementaire A0-kaart.

---

## 1. Redactionele Stijlregels

1. **Bij voorkeur één woord**
   - Kies krachtige, zelfstandige termen (bijv. `Gaza`, `Libanon`, `Sancties`, `Nederzettingen`, `Genocideverdrag`).
   - Vermijd waar mogelijk `A & B` constructies (`Israël & Gaza`), tenzij onvermijdelijk.
2. **Geen doublures op de kaart**
   - Een label komt bij voorkeur slechts **één keer** voor op de gehele kaart. 
   - Generieke termen mogen niet meervoudig rondslingeren (bijv. geen 39x `Moties`, geen 26x `Procedure`, geen dubbele landnamen).
3. **Geen ouder-kind redundantie (Tautologie)**
   - Als een bovenliggend niveau (ouder) al `Oekraïne`, `Stikstof` of `Israël` heet, herhaalt het kind die naam niet.
   - *Fout*: `Oekraïne` $\to$ `Oekraïne-steun`
   - *Goed*: `Oekraïne` $\to$ `Steun`
4. **Geen persoonsnamen of partijnamen**
   - Individuele Kamerleden (zoals *Omtzigt*, *Grinwis*, *Jetten*) en partijnamen (*PVV*, *BBB*, *NSC*) horen niet thuis als thematische beleidslabels.
   - Zij worden vervangen door de beleidsinhoud van het debat of verplaatst naar persoons-/partijcontouren (zie issue #261).
5. **Diplomatieke en neutrale terminologie**
   - Sluit aan bij het officiële taalgebruik van de Staten-Generaal en gevestigde encyclopedische begrippen (Wikipedia), bijvoorbeeld:
     - `Midden-Oosten` als overkoepelend domein (i.p.v. alleen één land).
     - Geen niet-erkende staten of politiek beladen strijdkreten als hoofdetiket.
     - Historisch afgebakende gebeurtenissen benoemen conform encyclopedische standaard (bijv. `Iranoorlog 2026`).

---

## 2. De Empirische Onderzoeksmethodiek

Om te voorkomen dat een taalmodel of TF-IDF een toevallige "one-off" of karikatuur kiest (zoals `Moslimbroederschap` of `Venezuela` onder Iran), hanteren we een vaste empirische cyclus:

### Stap 1: Feitelijke debatten en term-telling
* Tel alle spreekbeurten in het cluster en rangschik de officiële Kamerdebat-titels.
* Tel letterlijk hoe vaak concurrerende termen vallen in de tekst van het cluster (bijv. *Sudan* (38x) vs *Darfur* (1x)).

### Stap 2: Sprekers en politieke dynamiek
* Welke partijen voeren het woord? Is het een breed debat of een eenzijdige interruptie?
* Wat is de politieke spanning? (Bijv. coalitie die uit elkaar gespeeld wordt $\to$ `Kabinetspositie`; of oppositie die verdragsplichten toetst).

### Stap 3: Inverse Lookup (c-TF-IDF & Semantisch Grid)
* Vergelijk de woordfrequenties van het cluster met de rest van de kaart via c-TF-IDF of raadpleeg het continu berekende semantische grid (`data/export/a0-map/inverse_terminology_grid.geojson`).
* Identificeer de unieke signaalwoorden die dit cluster onderscheiden van buurclusters (zoals de vondst van `Genocideverdrag` en `Knesset` bij L4-249).

### Stap 4: Stap-voor-stap menselijk overleg
* Wijzigingen worden nooit 'en bloc' geautomatiseerd doorgevoerd op basis van aannames.
* Elk label wordt één voor één besproken en vastgesteld op basis van de feiten uit de data.

---

## 3. Voorbeeldcasussen uit de praktijk

| Oude label | Probleem | Data-inzicht & Inverse Lookup | Nieuw label |
| :--- | :--- | :--- | :--- |
| **`Moslimbroederschap`** *(L2-55)* | Te activistisch, TF-IDF uitschieter | 143x DENK over discriminatie, integratie en burgerschap | **`Integratie`** |
| **`Venezuela`** *(L4-216, onder Iran)* | Hallucinatie / one-off term | 30x Iran, Christine Teunissen/Jesse Klaver over luchtaanvallen VS/Israël in 2026 | **`Iranoorlog 2026`** |
| **`Conflictgerelateerd seksueel geweld`** *(L3-80)* | Overdreven lang LLM-label | 106x debat over belegering El Fasher; Sudan (38x) vs Darfur (1x) | **`Sudan`** |
| **`Israël-sancties`** *(L4-487)* | Ouder-kind redundantie (onder Israël) | Debat over handelssancties en associatieverdrag | **`Sancties`** |
| **`Israël-Palestina`** *(L4-387)* | Diplomatiek gevoelig, niet-erkende staat | Teunissen & Jetten over illegale nederzettingen en Westbank | **`Nederzettingen`** |
| **`Gaza`** *(L4-249)* | Oneigenlijke 3e doublure van Gaza | Omtzigt, Dassen, Van Baarle over naleving van het Genocideverdrag van 1948 | **`Genocideverdrag`** |
| **`Gaza`** *(L4-357)* | Oneigenlijke 2e doublure van Gaza | Debatten over de Europese Raad en gezamenlijke EU-verklaringen | **`Positie Europa`** |

| **`Stikstof`** *(L0-5)* | Domein te smal voor LNV (omvat ook visserij, diertransport) | 5.597 pts LNV-beleid; visserij (2.424x), gewasbescherming (246x) | **`Landbouw`** |
| **`Stikstof, NPLG`** *(L4-412)* | Generiek duplicaat 'Stikstof' onder PAS-melders | Omtzigt, Bromet, Grinwis, Van der Wal over ammoniakruimte en Schiphol | **`Salderen`** |
| **`Stikstof`** *(L4-447)* | Generiek duplicaat 'Stikstof' | Van Haga (5x onteigenen), Futselaar (dwang vs vrijwillig), Boswijk | **`Onteigenen`** |
| **`Stikstofcrisis`** *(L4-332)* | Generiek label 'Stikstofcrisis' | Debat Wopke Hoekstra ("2030 niet heilig"); impasse (3x in cluster, 16x in Kamer) | **`Impasse`** |
| **`Stikstof`** *(L4-414)* | Generiek duplicaat 'Stikstof' | Boomsma ("stikstofslot"), De Groot ("reparatiewet"), Schouten na Raad van State | **`Stikstofslot`** |
| **`Stikstof`** *(L4-376)* | Generiek duplicaat 'Stikstof' | Jetten (taskforce), Paternotte & Vermeer (stikstofuitstoot industrie) | **`Industrie`** |
| **`Stikstof`** *(L4-389)* | Generiek duplicaat 'Stikstof' | Wiersma (gebiedsgericht maatwerk), Omtzigt (stikstofkaarten), Grinwis | **`Gebiedsgericht`** |
| **`Stikstof`** *(L4-413)* | Generiek duplicaat 'Stikstof' | Van Essen (halvering veestapel), Van der Plas (veestapel -25%), Bromet (2,6 GVE) | **`Veestapel`** |
| **`Stikstof`** *(L4-478)* | Generiek duplicaat 'Stikstof' | Wiersma (KDW schrappen), Van der Plas (drukfactoren), Rutte (habitat) | **`KDW`** |
| **`Stikstofbeleid`** *(L3-73 / L4-78)* | Duplicaat van Stikstofbeleid | Keijzer, Grinwis, Bromet over technische innovaties en voorbeeldboeren | **`Innovatie`** |
| **`Stikstofbeleid`** *(L3-108 / L4-94)* | Duplicaat van Stikstofbeleid | Boer/boeren 71x; Van der Plas vs Bromet ("boerenhaat"), Flach (SGP) | **`Boeren`** |
| **`Rekenkundige ondergrens`** *(L3-116)* | Samengesteld begrip | 55x ondergrens in Kamer; afkapwaarde in rekenmodel behouden als geheel | **`Rekenkundige ondergrens`** |
| **`Dierenwelzijn`** *(L3-58 / L4-54)* | Te algemene doublure onder Overlast | 69x wolf/wolven; 157x debat De wolf in Nederland | **`Wolf`** |
| **`Dierenwelzijn`** *(L3-101)* | Te algemene doublure onder Overlast | Paraplu voor Dierenarts (opkoop praktijken) en Vogelgriep (uitbraken); niet alle dieren worden verzorgd | **`Zieke dieren`** |
| **`Dierenwelzijn`** *(L4-125)* | Te algemene doublure onder L3-101 | 38x dierenarts(en); 63x debat stijgende tarieven en vercommercialisering | **`Dierenarts`** |
| **`Informatieverzoeken`** *(L2-19)* | Hallucinatie; overkoepelt 7 partijlabels op L4 | 75% Kamervoorzitters (Van Campen, Van der Lee, Bosma) die sprekers oproepen | **`Genoemd`** |
| **`Moties`** *(L4-444)* | Generiek 'Moties' duplicaat (16x op L4) | 26x Bromet, Brekelmans, Eerdmans: \"Mijn tweede motie, voorzitter\" | **`Tweede motie`** |
| **`Moties`** *(L4-275)* | Generiek 'Moties' duplicaat | 58x \"Ik heb één motie\" | **`Eén motie`** |
| **`Moties`** *(L4-182)* | Generiek 'Moties' duplicaat | 85x \"Voorzitter, ik heb twee moties\" | **`Twee moties`** |
| **`Moties`** *(L4-219)* | Generiek 'Moties' duplicaat | 74x \"Ik heb een drietal moties, voorzitter\" | **`Drie moties`** |
| **`Moties`** *(L4-488)* | Generiek duplicaat | Motie aanpassen, gewijzigde motie of intrekken | **`Motie aanpassen`** |
| **`Moties`** *(L4-50)* | Generiek duplicaat | 233x formele dank aan bewindspersonen voor de beantwoording | **`Dankwoord`** |
| **`Moties`** *(L4-195)* | Generiek duplicaat | Dobbe e.a.: \"Ik zal mijn tijd gebruiken om moties in te dienen\" | **`Indienen`** |
| **`Moties`** *(L4-388)* | Generiek duplicaat | Van der Burg e.a.: tradities rond motiebehandeling | **`Tradities`** |
| **`Moties`** *(L4-328)* | Generiek duplicaat | Van Meijeren e.a.: \"Ik verzoek uitdrukkelijk niet per motie om...\" | **`Niet per motie`** |
| **`Moties`** *(L4-393)* | Generiek duplicaat | Eerdmans e.a.: \"Ik heb één motie naar aanleiding van het debat...\" | **`Naar aanleiding van`** |
| **`Staatssecretaris`** *(L4-239)* | Behoudenswaardig | 40x mondelinge vragen en interrupties aan de staatssecretaris | **`Staatssecretaris`** |
| **`Staatssecretaris`** *(L4-272)* | Doublure van Staatssecretaris | Paulusma, Podt, Boelsma over toegezegde brieven en rapportages | **`Brief`** |
| **`Toezeggingen`** *(L2-49)* | Oudercluster met te vage naam | 81x brief (\"Krijgen we die brief voor het debat?\") over alle terreinen | **`Brieven`** |
| **`Toezeggingen`** *(L4-179)* | Generiek duplicaat (5x) | 31x ministers (Kaag, Wiersma, Letschert): \"bevestigen in tweede termijn\" | **`Tweede termijn`** |
| **`Toezeggingen`** *(L4-274)* | Behoudenswaardig hoofdcluster | 17x toezeggen/toezegging (Ceder, Hermans, Brekelmans, Van Weel) | **`Toezeggingen`** |
| **`Toezeggingen`** *(L4-415)* | Generiek duplicaat | Adriaansens (\"halfjaarlijkse voortgangsbrief\"), Jetten (\"SDE-brief\") | **`Voortgang`** |
| **`Toezeggingen`** *(L4-458)* | Generiek duplicaat | Wiebes, Sterk, Erkens: \"even checken bij de ambtenaren in de loge\" | **`Navragen`** |
| **`Procedure`** *(L4-233)* | Generieke procedurele naam | Kuzu, Ouwehand, Van Zanten: \"Een punt van orde, voorzitter\" | **`Punt van orde`** |
| **`Procedure`** *(L4-252)* | Generieke procedurele naam | Ouwehand, Van Houwelingen, Paternotte: \"Heel kort, als het mag voorzitter?\" | **`Heel kort`** |
| **`Procedure`** *(L4-112)* | Generieke procedurele naam | Ceder, Kostić, Dijk: \"Ik hoop niet dat dit telt als interruptie?\", \"Had ik er niet meer?\" | **`Telt als interruptie?`** |
| **`Procedure`** *(L4-213)* | Generieke procedurele naam | Grinwis (\"flauwe kenschets\"), Bontenbal (\"raar verwijt\"), Rajkowski (\"persoonlijke aanval\") | **`Aanvaring`** |
| **`Procedure`** *(L4-286)* | Generieke procedurele naam | Beckerman, Hamstra, Belhirch: \"Voor dit punt afdoende\", \"Afrondend, dank voor initiatief\" | **`Afrondend`** |
| **`Procedure`** *(L4-285)* | Generieke procedurele naam | Van der Plas (\"mooie lach\"), Van der Burg (\"denken buiten mijn hoofd\", \"ga wat doen vrienden\") | **`Kwinkslag`** |
| **`Procedure`** *(L4-199)* | Generieke procedurele naam | Dijksma (\"winst binnenhalen\"), Keijzer (\"dat gaan we doen!\"), Faber (\"akkoord, prima\") | **`Instemming`** |
| **`Procedure`** *(L4-299)* | Generieke procedurele naam | Van Toorenburg (\"Ik wil uitpraten\"), Baudet (\"Ik wil stemming\"), Van der Plas (\"Ik wil foto's\") | **`Ik wil`** |
| **`Procedure`** *(L4-410)* | Generieke procedurele naam | Schoof & Tellegen (\"Gezegd wat ik heb gezegd\"), Coenradie (\"Pijn in mijn hart\"), Bontenbal (\"Voor aap staan\") | **`Gezegdes`** |
| **`Procedure`** *(L4-439)* | Generieke procedurele naam | Hermans, Rutte, Sterk, Rijkaart: \"Als ik hier in tweede termijn op terug mag komen, graag\" | **`Op terugkomen`** |
| **`Procedure`** *(L4-500)* | Generieke procedurele naam | Van Essen (\"Ik verkondig waarheden\"), Tijmstra (\"Ik denk dat we het niet eens worden\"), Van Marum (\"Ik vind jammer\") | **`Ik vind`** |
| **`Procedure`** *(L4-370)* | Generieke procedurele naam | 19x debatteren over of met Mona Keijzer (Bontenbal, Van der Plas, Van Essen, Paternotte) | **`Keijzer`** |
| **`Procedure`** *(L4-507)* | Generieke procedurele naam | Bosma (\"O, nog een vraag van Sneller\"), Dassen/Boswijk (felicitaties maidenspeech) | **`Encore`** |
| **`Procedure`** *(L4-495)* | Generieke procedurele naam | Heinen (\"Knippen we het debat?\"), Van der Plas (\"Dan gaan we langer door\"), Markuszower (\"Afspraak 23u\") | **`Doorgaan?`** |
| **`Procedure`** *(L4-23)* | Generieke procedurele naam onder Genoemd | 450x voorzitters (Van Campen, Bosma, Van der Lee): \"Ik geef het woord aan...\" | **`Geef het woord`** |
| **`Procedure`** *(L3-119)* | Generieke procedurele naam (L3) | Flach, Grinwis, Goudzwaard: \"Zit dat in het blokje generiek, of is dat een ander blokje?\" | **`Blokje`** |
| **`Procedure`** *(L3-70)* | Generieke procedurele ouder (L3) | Overkoepelt Telt als interruptie? en Aanvaring aan de microfoon | **`Interrupties`** |
| **`Procedure`** *(L3-155)* | Generieke procedurele naam (L3) | Baudet (\"Te lang, sorry, reken maar als twee\"), Flach (\"Die regels\"), Hirsch (\"Dít is geen interruptie\") | **`Nog een interruptie?`** |
| **`PVV-kritiek`** *(L4-185)* | Synthetisch partijlabel | Koekkoek, Ouwehand, Podt: oppositie die de coalitie zwaar bestookt | **`Onder vuur`** |
| **`ChristenUnie-PVV-samenwerking`** *(L4-346)* | Synthetisch partijlabel | Bromet, Van der Plas, Gündoğan: wiggen drijven tussen regeringspartners | **`Stoken`** |
| **`Motiebehandeling`** *(L1-13)* | Generieke continentnaam | 1.670 beurten over het staatsrechtelijk uitvoeren van moties | **`Uitvoeren`** |
| **`Motiebehandeling`** *(L2-56)* | Generieke doublure | 419 beurten formele appreciaties van het kabinet | **`Appreciatie`** |
| **`Motiebehandeling`** *(L3-132)* | Generieke doublure | 151 beurten bewindspersonen die moties ontijdig verklaren | **`Ontijdig`** |
| **`Motiebehandeling`** *(L4-1)* | Grootste cluster op L4 (sz=6.190) | Voorzitters (Sneller, Bergkamp, Bosma, De Vries): "Dan gaan we naar volgende motie" | **`Volgende motie`** |
| **`Motiebehandeling`** *(L4-12)* | Generiek duplicaat (sz=1.209) | Van Hijum, Vermeer, Hoogeveen: kabinet moet aangenomen moties uitvoeren | **`Moeten`** |
| **`Motiebehandeling`** *(L4-67)* | Generiek duplicaat (sz=249) | Moes, Agema, Heinen: telegrafisch "De motie op stuk nr. X: oordeel Kamer" | **`Motie: oordeel`** |
| **`Motiebehandeling`** *(L4-118)* | Generiek duplicaat (sz=151) | Tieman, Jansen, Van Marum: "De motie op stuk nr. X: ontijdig" | **`Ontijdig`** |
| **`Oordeel Kamer`** *(L4-123)* | Generieke doublure van Oordeel Kamer | Brekelmans, Van Essen, Van der Burg: motie krijgt oordeel mits zo gelezen | **`Toch oordeel kamer`** |
| **`Motiebehandeling`** *(L4-187)* | Generiek duplicaat (sz=94) | 98% ontraden; Hermans, Vijlbrief, Van der Wal: "Die is ontraden" | **`Ontraden`** |
| **`Motiebehandeling`** *(L4-206)* | Generiek duplicaat (sz=83) | Bromet, Van Vroonhoven: "Kamer heeft motie aangenomen, gaat u die uitvoeren?" | **`Toch?`** |
| **`Oordeel Kamer`** *(L4-243)* | Generieke doublure van Oordeel Kamer | Jetten, Van Weel, Van der Wal: "Op stuk nr. X geef ik oordeel Kamer" | **`Op stuk, oordeel Kamer`** |
| **`Motiebehandeling`** *(L4-254)* | Generiek duplicaat (sz=65) | Van der Burg, Hermans, Vijlbrief: moties al oordeel geven voor beantwoording vragen | **`Ik geef oordeel kamer`** |
| **`Motiebehandeling`** *(L4-258)* | Generiek duplicaat (sz=62) | Jansen, Sterk, Van Nispen: moties doorverwijzen naar juiste bewindspersoon | **`De juiste plek?`** |
| **`Motiebehandeling`** *(L4-259)* | Generiek duplicaat (sz=62) | Van Weel, Van Veldhoven, Beljaarts, Van den Brink: "ik moet deze motie dus ontraden" | **`Dus ontraden`** |
| **`Motiebehandeling`** *(L4-277)* | Generiek duplicaat (sz=59) | 100% oordeel Kamer; De Bat, Jetten, Boekholt-O'Sullivan: "krijgt ook oordeel Kamer" | **`Ook oordeel kamer`** |
| **`Motiebehandeling`** *(L4-307)* | Generiek duplicaat (sz=53) | Blok, Szabó, Van Oosten: verzoek aan indieners om motie aan te houden | **`Aanhouden`** |
| **`Oordeel Kamer`** *(L4-326)* | Generieke doublure van Oordeel Kamer | Van Veldhoven, Jetten, Adema: motie krijgt pas oordeel Kamer na aanpassing/wijziging | **`Als, dan, oordeel kamer`** |
| **`Motiebehandeling`** *(L4-367)* | Generiek duplicaat (sz=44) | Wiersma, Bromet, Van Zanten: "Waarom kan die dan niet gewoon oordeel Kamer krijgen?" | **`Dan oordeel kamer`** |
| **`Motiebehandeling`** *(L4-434)* | Generiek duplicaat (sz=36) | Simons, Dijk, Tony van Dijck: oppositie die klaagt over willekeurig ontreden | **`Ontraden?`** |
| **`Motiebehandeling`** *(L4-504)* | Generiek duplicaat (sz=30) | Bewindspersonen die lijst stuknummers afroepen: "Dan de motie op stuk nr. X" | **`Dan de motie op stuk`** |
| **`Wetgeving`** *(L4-180)* | Hoofdcluster behouden (sz=97) | AMvB's, Raad van State, WAMCA en advocatuur | **`Wetgeving`** |
| **`Wetgeving`** *(L4-344)* | Generiek duplicaat (sz=48) | Bikker, Dijk, Sneller: amendementen in stemming brengen, medeondertekenen | **`Amendement`** |
| **`Wetgeving`** *(L4-355)* | Generiek duplicaat (sz=46) | Bisschop, Mulder, Van Weel: fasering, evaluatie en inwerkingtreding | **`Inwerkingtreding`** |
| **`Wetgeving`** *(L4-363)* | Generiek duplicaat (sz=45) | Van Essen, Rajkowski, Buijsse: onderbouwing en juridische toetsing | **`Onderbouwing`** |
| **`Wetgeving`** *(L4-403)* | Generiek duplicaat (sz=41) | Omtzigt, Ceder, Pierik: vertraging van wetsvoorstellen en initiatiefwetten | **`Vertraging`** |
| **`Wetgeving`** *(L4-472)* | Generiek duplicaat (sz=33) | Van Weel ("De wet is de wet"), Van den Brink ("huidige kader"), Jetten | **`Wet is wet`** |
| **`Uitvoering`** *(L4-167)* | Hoofdcluster behouden (sz=104) | Karremans, Van Weel, Thijssen: beleidsuitvoering departementen en VNG | **`Uitvoering`** |
| **`Uitvoering`** *(L4-196)* | Generiek duplicaat (sz=90) | Sandra Palmen ("In de uitvoeringspraktijk"), Van Hijum, Bontenbal | **`In de praktijk`** |
| **`Uitvoering`** *(L4-427)* | Generiek duplicaat (sz=38) | Hermans ("prioriteringskader"), Van Marum ("capaciteitsprobleem t.o.v. doel"), Sterk | **`Prioritering`** |
| **`Uitvoering`** *(L4-515)* | Generiek duplicaat (sz=30) | Hoogeveen ("quickscan/uitvoerbaarheid per 1 jan"), Rummenie, Tielen | **`Uitvoerbaarheid`** |
| **`Vergaderorde`** *(L4-260)* | Generiek duplicaat (sz=62) | Kamervoorzitters (Kisteman, Van Campen, Paulusma, Bosma): sprekers het woord geven | **`Gaat uw gang`** |
| **`Vergaderorde`** *(L4-290)* | Generiek duplicaat (sz=57) | Bewindspersonen (Paul, Uitermark, Erkens, Van Oosten): antwoord niet paraat/bij zich | **`Niet paraat`** |
| **`Vergaderorde`** *(L4-398)* | Generiek duplicaat (sz=41) | Veldkamp, Blok, Lohman, Dassen: woord of vragen overdragen aan de staatssecretaris | **`Minister of staatssecretaris`** |
| **`Regeldruk`** *(L4-352)* | Hoofdcluster behouden (sz=46) | Maeijer, Müller, Kröger: ATR (Adviescollege toetsing regeldruk), percentages lastenverlichting | **`Regeldruk`** |
| **`Regeldruk`** *(L4-378)* | Generiek duplicaat (sz=43) | Dijk, Brekelmans ("overheid vanzelf uitdijt"), Vijlbrief: taakstelling en omvang overheid | **`Kleine overheid`** |
| **`Regeldruk`** *(L4-516)* | Generiek duplicaat (sz=30) | Six Dijkstra, Aartsen ("simpeler en menselijker"), Eerenberg ("regeling opruimen") | **`Doelmatigheid`** |
| **`Interrupties`** *(L4-468)* | Generiek duplicaat (sz=33) | Voorzitters (Paulusma, Bosma, De Vries, Markuszower): "U heeft een interruptie van..." | **`U heeft een interruptie`** |
| **`Interrupties`** *(L4-499)* | Generiek duplicaat (sz=31) | Kamerleden (Ceder, Kostić, Wijen-Nass, Boswijk, Boomsma): "Hoeveel interrupties heb ik nog?" | **`Hoeveel interrupties heb ik nog?`** |
| **`Interrupties`** *(L4-508)* | Generiek duplicaat (sz=30) | Kamerleden (Timmermans, Van Baarle, Stultiens, Kröger, Leijten): verzet tegen interruptielimiet | **`Meer interrupties`** |
| **`Antisemitisme`** *(L4-30)* | Hoofdcluster behouden (sz=505) | Schoof, Wilders, Teunissen: landelijk debat antisemitisme, Amsterdam, Taskforce | **`Antisemitisme`** |
| **`Antisemitisme`** *(L4-202)* | Generiek duplicaat (sz=85) | Stultiens, Van der Plas, Keijzer, Nanninga: veiligheid en intimidatie van Joodse studenten | **`Joodse studenten`** |
| **`Coalitieakkoord`** *(L4-68)* | Generiek duplicaat (sz=249) | Bontenbal ("onderhandelen met D66, concessies"), informateursverslag, verkiezingsuitslag | **`Formatie`** |
| **`Coalitieakkoord`** *(L4-263)* | Hoofdcluster behouden (sz=62) | Huizenga, Maes, Tijmstra, Van Eijk: uitvoering van afspraken uit het coalitieakkoord | **`Coalitieakkoord`** |
| **`Transparantie`** *(L4-209)* | Generiek duplicaat (sz=82) | Van Dijk (SGP), Hoogeveen, Schoof: samenspel Kamer-kabinet en machtsverhoudingen | **`Machtsverhoudingen`** |
| **`Transparantie`** *(L4-433)* | Generiek duplicaat (sz=37) | Herbert ("inzicht geven"), Hermans, De Vries, Yeşilgöz: informatiepositie en consultatie | **`Informatiepositie`** |
| **`Termijnafspraken`** *(L4-223)* | Generiek duplicaat (sz=77) | Van Hijum, Sterk ("daar bedoel ik het zomerreces mee"), Jansen: deadlines rond het reces | **`Zomerreces`** |
| **`Termijnafspraken`** *(L4-335)* | Generiek duplicaat (sz=49) | Sterk, Hermans ("tabaksbrief/brief apotheek voor de zomer"), Pouw-Verweij | **`Brief voor de zomer`** |
| **`Procesvoering`** *(L4-247)* | Hoofdcluster behouden (sz=67) | Van Dijk (SGP), Jetten, Becking: gefaseerde besluitvorming, routes en no-regret | **`Procesvoering`** |
| **`Procesvoering`** *(L4-441)* | Generiek duplicaat (sz=36) | Tseggai ("wacht al jaar op onderzoek"), Schoof, Maeijer: wachten op externe rapporten | **`Onderzoek afwachten`** |
| **`Bezuinigingen`** *(L4-371)* | Hoofdcluster behouden (sz=44) | De Beer ("begroting rond krijgen"), Van Eijk, Biekman: macro-financiën en begroting | **`Bezuinigingen`** |
| **`Bezuinigingen`** *(L4-255)* | Generiek duplicaat (sz=64) | Oostenbrink ("niet-besteed geld"), Van Hijum ("terugvordering"), De Vries ("subsidies") | **`Terugvordering`** |
| **`Amendementen`** *(L4-329)* | Generiek duplicaat (sz=51) | Hermans, De Vries, Aartsen: resoluut ontraden van amendementen door bewindslieden | **`Amendement ontraden`** |
| **`Amendementen`** *(L4-372)* | Generiek duplicaat (sz=44) | Bruins ("geef graag oordeel Kamer"), Vijlbrief, Becking: verlenen van oordeel Kamer | **`Amendement oordeel Kamer`** |
| **`Moties`** *(L1-17)* | Ouder-herhaling L0 (sz=1348) | Ceder ("Ik heb een motie"), Klos ("aanhouden"), Ergin ("volgende motie"): Kamerleden aan spreekgestoelte | **`Indienen`** |
| **`Moties`** *(L2-35)* | Generiek duplicaat (sz=593) | Bosma ("vijf moties is wel erg veel"), Aartsen, Van Baarle: debat over motielimiet | **`Aantal`** |
| **`Moties`** *(L2-54)* | Generiek duplicaat (sz=420) | Dekker ("dank aan de minister voor beantwoording"), Van Baarle, Ceder: reactie op toezeggingen | **`Dank de minister`** |
| **`Moties`** *(L2-23)* | Generiek duplicaat (sz=928) | Bruins Slot ("motie van Temmink"), Vijlbrief ("van Van den Brink"), Ceder ("sta ik eronder?"): koppeling aan indiener | **`Van`** |
















