// Balklengte voor de pro/contra/onduidelijk-as op de debatkaarten (#112):
// wortelschaal i.p.v. lineair, zodat een debat met 17 argumenten niet
// wegvalt naast één met 687 (ontwerpkeuze uit
// docs/design/debattenlijst/Debattenkaarten.dc.html).
export function scaleWidth(value: number, max: number): string {
	if (max <= 0) return "0%";
	return `${(Math.sqrt(value / max) * 100).toFixed(1)}%`;
}
