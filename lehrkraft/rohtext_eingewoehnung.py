"""Erzeugt den unformatierten Rohtext für das Gruppenprojekt (material/rohtext-eingewoehnung.docx).

    python3 lehrkraft/rohtext_eingewoehnung.py

Der Text ist absichtlich unformatiert: #/##/### markieren Überschriften, die Quellen sind ausgedacht und nur zum Üben.
"""
from pathlib import Path

from docx import Document

ZIEL = Path(__file__).resolve().parent.parent / "material" / "rohtext-eingewoehnung.docx"

TEXT = """# 1 Einleitung
Der Eintritt in die Krippe ist für viele Kinder die erste längere Trennung von ihren Eltern. Wie dieser Übergang gestaltet wird, hat großen Einfluss darauf, ob sich ein Kind in der Einrichtung sicher fühlt. Diese Arbeit stellt dar, worauf es bei der Eingewöhnung ankommt und wie pädagogische Fachkräfte sie in der Praxis begleiten können.
# 2 Grundlagen der Eingewöhnung
## 2.1 Bindung als Voraussetzung
Kleine Kinder können sich nur dann neugierig ihrer Umgebung zuwenden, wenn sie sich sicher fühlen. Diese Sicherheit geben ihnen vertraute Bezugspersonen. In der Krippe muss das Kind deshalb zunächst eine Beziehung zu einer Fachkraft aufbauen, bevor es sich von den Eltern trennen kann. Eine gelungene Eingewöhnung ist damit vor allem ein Beziehungsaufbau.
## 2.2 Eingewöhnungsmodelle
In deutschen Einrichtungen werden vor allem zwei Modelle genutzt. Das Berliner Eingewöhnungsmodell sieht eine mehrtägige Grundphase vor, in der ein Elternteil mit dem Kind in der Einrichtung bleibt. Erst danach folgt ein erster kurzer Trennungsversuch, dessen Verlauf über die weitere Dauer entscheidet. Das Münchener Eingewöhnungsmodell legt größeren Wert darauf, dass das Kind die ganze Gruppe, die Räume und den Tagesablauf kennenlernt, bevor die Trennung beginnt.
# 3 Die Eingewöhnung in der Praxis
## 3.1 Vorbereitung mit den Eltern
Vor dem ersten Tag führt die Bezugsfachkraft ein ausführliches Gespräch mit den Eltern. Dabei geht es um Gewohnheiten des Kindes, Rituale beim Schlafen und Essen und um die Erwartungen der Familie. Die Eltern erfahren, wie die Eingewöhnung abläuft und warum ihre Anwesenheit in den ersten Tagen so wichtig ist.
## 3.2 Die ersten Tage
In den ersten Tagen bleibt das Kind nur kurze Zeit in der Einrichtung. Ein Elternteil ist dabei, verhält sich aber eher zurückhaltend und dient dem Kind als sicherer Hafen. Die Fachkraft nimmt behutsam Kontakt auf, bietet Spielmaterial an und beobachtet, wie das Kind reagiert.
## 3.3 Abschluss der Eingewöhnung
Die Eingewöhnung gilt als abgeschlossen, wenn sich das Kind von der Bezugsfachkraft trösten lässt und den Alltag in der Gruppe mitgestalten kann. Wie lange das dauert, ist sehr unterschiedlich. Ein abschließendes Gespräch mit den Eltern rundet die Eingewöhnung ab.
# 4 Fazit
Eine gelungene Eingewöhnung braucht Zeit, eine verlässliche Bezugsfachkraft und eine enge Zusammenarbeit mit den Eltern. Feste Zeitpläne helfen bei der Orientierung, entscheidend ist aber immer das Verhalten des einzelnen Kindes.
Material für die Gruppe – diesen Teil löscht ihr, sobald ihr ihn verarbeitet habt:
Quelle 1 (ausgedacht, nur zum Üben): Buch von Lena Hoffmann, „Eingewöhnung gestalten. Übergänge von der Familie in die Krippe begleiten“, 3., überarbeitete Auflage 2022, Verlag Frühe Schritte, Hamburg. Auf Seite 34 steht: „Eingewöhnung ist in erster Linie Beziehungsarbeit – und Beziehung lässt sich nicht nach Stundenplan herstellen.“
Quelle 2 (ausgedacht, nur zum Üben): Aufsatz von Hanna Petersen, „Bindung und Eingewöhnung“, erschienen 2023 in „Handbuch Krippenpädagogik. Grundlagen für die Praxis“, herausgegeben von Maren Albers und Tom Brandt, Verlag Frühe Schritte, Hamburg, Seiten 112–130. Auf Seite 118 erklärt Petersen, dass Kinder sich erst dann der Umgebung zuwenden, wenn sie sich bei einer Bezugsperson sicher fühlen.
Quelle 3 (ausgedacht, nur zum Üben): Website des Netzwerks Frühe Kindheit e. V., Seite „Die ersten Tage in der Krippe – so gelingt die Eingewöhnung“, veröffentlicht am 12. März 2024, https://www.netzwerk-fruehe-kindheit.example/eingewoehnung (keine Person als Autor:in genannt). Dort wird empfohlen, das Kind in den ersten Tagen nur ein bis zwei Stunden in der Einrichtung zu lassen.
Zahlen für eine Tabelle (ausgedacht): Dauer der Eingewöhnung in einer Krippe, 20 Kinder:
Dauer	Anzahl der Kinder
bis 1 Woche	3
1 bis 2 Wochen	7
2 bis 3 Wochen	6
mehr als 3 Wochen	4"""

d = Document()
for zeile in TEXT.split("\n"):
    d.add_paragraph(zeile)
d.core_properties.author = ""
d.save(ZIEL)
print("✓", ZIEL)
